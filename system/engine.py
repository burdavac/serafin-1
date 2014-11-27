from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth import get_user_model
from django.core.signals import request_finished
from django.utils import timezone

from datetime import date, timedelta
from events.signals import log_event
from huey.djhuey import db_task
from system.models import Variable, Session, Page, Email, SMS
from tasker.models import Task


class Engine(object):
    '''A simplified decision engine to traverse the graph for a user'''

    def __init__(self, user_id, context={}):
        '''Initialize Engine with a User instance and optional context'''

        self.user = get_user_model().objects.get(id=user_id)

        # process context if available, save to user data
        if context:
            for key, value in context.items():
                if key and value is not None:
                    self.user.data[key] = value

            self.user.save()

        session_id = self.user.data.get('current_session')
        self.session = Session.objects.get(id=session_id)

        self.nodes = {node['id']: node for node in self.session.data.get('nodes')}
        self.edges = self.session.data.get('edges')

    @staticmethod
    def get_system_var(var_name):
        if not var_name:
            return ''

        if var_name == 'current_day':
            return date.isoweekday(date.today())
        else:
            try:
                var = Variable.objects.get(name=var_name)
                return var.get_value() or ''
            except:
                return ''

    @classmethod
    def check_conditions(cls, conditions, user, return_value):
        '''Return a value if all conditions in a list of conditions pass (or no conditions)'''

        passing = []
        for condition in conditions:
            var_name = condition.get('var_name')
            operator = condition.get('operator')
            value_b = condition.get('value')

            # variable comparison:
            # if value_b is actually another var_name, assign users value to it
            value_b = user.data.get(value_b, value_b)
            value_a = user.data.get(var_name)

            # if either value is still not assigned, try system vars
            if not value_a:
                value_a = cls.get_system_var(var_name)

            if not value_b:
                value_b = cls.get_system_var(value_b)

            try:
                # try converting to float for numeric comparisons
                value_a_float = float(value_a)
                value_b_float = float(value_b)

                # only set to float if both pass conversion
                value_a = value_a_float
                value_b = value_b_float
            except:
                pass

            if isinstance(value_a, list):
                value_a = ', '.join(value_a)

            if isinstance(value_b, list):
                value_b = ', '.join(value_b)

            if var_name == 'group':
                value_a = ', '.join(
                    [group.__unicode__() for group in user.groups.all()]
                )

            if operator == 'eq':
                passing.append(value_a == value_b)

            if operator == 'ne':
                passing.append(value_a != value_b)

            if operator == 'lt':
                passing.append(value_a < value_b)

            if operator == 'le':
                passing.append(value_a <= value_b)

            if operator == 'gt':
                passing.append(value_a > value_b)

            if operator == 'ge':
                passing.append(value_a >= value_b)

            if operator == 'in':
                passing.append(unicode(value_b).lower() in unicode(value_a).lower())

        if all(passing):
            return return_value

    def traverse(self, edges, source_id):
        '''Select and return first edge where the user passes edge conditions'''

        for edge in edges:
            conditions = edge.get('conditions')

            return_edge = self.check_conditions(conditions, self.user, edge)
            if return_edge:
                return return_edge

    def get_node_edges(self, source_id):
        return [edge for edge in self.edges if edge.get('source') == source_id]

    def get_normal_edges(self, edges):
        return [edge for edge in edges if edge.get('type') == 'normal']

    def get_special_edges(self, edges):
        return [edge for edge in edges if edge.get('type') == 'special']

    def is_dead_end(self, node_id):
        target_edges = self.get_node_edges(node_id)
        return len(self.get_normal_edges(target_edges)) == 0

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

                self.user.data['current_background'] = target_id
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
                    pre_value=self.nodes[self.user.data['current_page']]['title'],
                    post_value=node.title
                )

                self.user.data['current_page'] = target_id
                self.user.save()

                node.dead_end = self.is_dead_end(target_id)

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

        if node_type == 'start':
            return self.transition(node_id)

    def run(self, next=None):
        '''Run the Engine after initializing and return some result'''

        node_id = self.user.data.get('current_page')

        if node_id == None:
            self.user.data['current_page'] = 0
            self.user.save()

        if next:
            return self.transition(node_id)

        return self.trigger_node(node_id)
