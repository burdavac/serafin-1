# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import operator

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import six, timezone
from django.utils.translation import ugettext_lazy as _

from events.signals import log_event
from system.models import Variable, Session, Page, Email, SMS
from tasker.models import Task
from .expressions import Parser


class Engine(object):
    '''A simplified decision engine to traverse the graph for a user'''

    def __init__(self, user_id, context={}, push=False, user=None):
        '''Initialize Engine with a User instance and optional context'''

        if user:
            self.user = user
        else:
            self.user = get_user_model().objects.get(id=user_id)

        # push current session and node to stack if entering subsession
        if push:

            session = self.user.data.get('session')
            node = self.user.data.get('node')

            if session and node is not None:
                if not self.user.data.get('stack'):
                    self.user.data['stack'] = []
                self.user.data['stack'].append((session, node))

        # process context if available
        if context:

            for key, value in context.items():

                if 'expression_' in key:
                    parser = Parser(user_obj=self.user)

                    try:
                        value = parser.parse(value)
                    except:
                        pass

                    parts = key.split('_')[1:]
                    key = ''.join(parts)

                    self.user.data[key] = value

                elif key and value is not None:
                    self.user.data[key] = value

        # save
        if push or context:
            self.user.save()

        self.init_session()

    def init_session(self, session_id=None, node_id=None):

        session_id = session_id or self.user.data.get('session')
        node_id = node_id or self.user.data.get('node')

        self.user.data['session'] = session_id
        self.user.data['node'] = node_id
        self.user.save()

        self.session = Session.objects.get(id=session_id)

        self.nodes = {node['id']: node for node in self.session.data.get('nodes')}
        self.edges = self.session.data.get('edges')

    @staticmethod
    def get_system_var(var_name, user):
        if not var_name:
            return ''

        # now as per timezone settings
        now = timezone.localtime(timezone.now().replace(microsecond=0))

        if var_name == 'current_day':
            return now.isoweekday()

        if var_name == 'current_time':
            return now.time().isoformat()

        if var_name == 'current_date':
            return now.date().isoformat()

        if var_name == 'registered':
            return not user.is_anonymous()

        if var_name == 'enrolled':
            session = Session.objects.get(id=user.data.get('session'))
            return session.program.programuseraccess_set.filter(user=user).exists()

        else:
            try:
                var = Variable.objects.get(name=var_name)
                return var.get_value() or ''
            except:
                return ''

    def traverse(self, edges, source_id):
        '''Select and return first edge where the user passes edge conditions'''

        for edge in edges:
            expression = edge.get('expression')

            if expression:
                parser = Parser(user_obj=self.user)
                passed = parser.parse(expression)
                if passed:
                    return edge
            else:
                return edge

    def get_node_edges(self, source_id):
        return [edge for edge in self.edges if edge.get('source') == source_id]

    def get_normal_edges(self, edges):
        return [edge for edge in edges if edge.get('type') == 'normal']

    def get_special_edges(self, edges):
        return [edge for edge in edges if edge.get('type') == 'special']

    def is_dead_end(self, node_id):
        '''Check if current node is a dead end (end of session)'''

        target_edges = self.get_node_edges(node_id)
        return len(self.get_normal_edges(target_edges)) == 0

    def is_stacked(self):
        '''Check if current session has sessions below in stack'''

        return bool(self.user.data.get('stack'))

    def transition(self, source_id):
        '''Transition from a given node and trigger a new node'''

        edges = self.get_node_edges(source_id)

        special_edges = self.get_special_edges(edges)
        normal_edges = self.get_normal_edges(edges)

        # traverse all special edges
        while special_edges:
            edge = self.traverse(special_edges, source_id)

            if edge:

                target_id = edge.get('target')
                special_edges.remove(edge)

                self.user.data['background_node'] = target_id
                self.user.save()

                self.trigger_node(target_id)

            else:
                break

        # traverse first applicable normal edge
        edge = self.traverse(normal_edges, source_id)

        if edge:

            target_id = edge.get('target')
            node = self.trigger_node(target_id)

            if isinstance(node, Page):
                log_event.send(
                    self,
                    domain='session',
                    actor=self.user,
                    variable='transition',
                    pre_value=self.nodes[self.user.data['node']]['title'],
                    post_value=node.title
                )

                self.user.data['node'] = target_id
                self.user.save()

                node.dead_end = self.is_dead_end(target_id)
                node.stacked = self.is_stacked()

                return node

    def trigger_node(self, node_id):
        '''Trigger action for a given node, return if Page'''

        node = self.nodes.get(node_id)
        node_type = node.get('type')
        ref_id = node.get('ref_id')

        if node_type == 'page':
            page = Page.objects.get(id=ref_id)
            page.update_html(self.user)

            page.dead_end = self.is_dead_end(node_id)
            page.stacked = self.is_stacked()

            return page

        if node_type == 'delay':

            useraccesses = self.session.program.programuseraccess_set.filter(user=self.user)
            for useraccess in useraccesses:
                start_time = self.session.get_start_time(
                    useraccess.start_time,
                    useraccess.time_factor
                )
                delay = node.get('delay')
                kwargs = {
                    delay.get('unit'): float(delay.get('number') * useraccess.time_factor),
                }
                delta = timedelta(**kwargs)

                from system.tasks import transition

                Task.objects.create_task(
                    sender=self.session,
                    domain='delay',
                    time=start_time + delta,
                    task=transition,
                    args=(self.user.id, node_id),
                    action=_('Delayed node execution'),
                    subject=self.user
                )

            return None

        if node_type == 'email':
            email = Email.objects.get(id=ref_id)
            email.send(self.user)

            log_event.send(
                self,
                domain='session',
                actor=self.user,
                variable='email',
                pre_value='',
                post_value=email.title
            )

            return self.transition(node_id)

        if node_type == 'sms':
            sms = SMS.objects.get(id=ref_id)
            sms.send(self.user)

            log_event.send(
                self,
                domain='session',
                actor=self.user,
                variable='sms',
                pre_value='',
                post_value=sms.title
            )

            return self.transition(node_id)

        if node_type == 'session':

            if not self.user.data.get('stack'):
                self.user.data['stack'] = []

            self.user.data['stack'].append(
                (self.session.id, self.user.data.get('node'))
            )

            self.init_session(ref_id, 0)

            return self.transition(0)

        if node_type == 'register':
            self.user, registered = self.user.register()

            if registered:
                log_event.send(
                    self,
                    domain='user',
                    actor=self.user,
                    variable='registered',
                    pre_value='',
                    post_value=''
                )

            return self.transition(node_id)

        if node_type == 'enroll':
            enrolled = self.session.program.enroll(self.user)

            if enrolled:
                log_event.send(
                    self,
                    domain='program',
                    actor=self.user,
                    variable='enrolled',
                    pre_value='',
                    post_value=self.session.program.title
                )

            return self.transition(node_id)

        if node_type == 'start':
            return self.transition(node_id)

    def run(self, next=False, pop=False):
        '''Run the Engine after initializing and return some result'''

        node_id = self.user.data.get('node')

        if node_id == None:
            self.user.data['node'] = 0
            self.user.save()

        # transition to next page
        if next:
            return self.transition(node_id)

        # pop stack data and set previous session
        if pop:
            session_id, node_id = self.user.data.get('stack').pop()
            # pop again if still on the same session
            while self.user.data.get('stack') and session_id == self.user.data.get('session'):
                session_id, node_id = self.user.data.get('stack').pop()
            self.init_session(session_id, node_id)

        return self.trigger_node(node_id)
