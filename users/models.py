from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import get_template
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin, AnonymousUser
from django.conf import settings
from jsonfield import JSONField
from collections import OrderedDict

from tokens.tokens import token_generator
from users.decorators import vault_post


class UserManager(BaseUserManager):
    '''Custom User model Manager'''

    def create_user(self, id, password):
        user = self.model()
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, id, password):
        user = self.create_user(id=id, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user


class User(AbstractBaseUser, PermissionsMixin):
    '''Custom User, identified by ID and password'''

    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=True)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True, editable=False)

    token = models.CharField(_('token'), max_length=64, blank=True, editable=False)

    data = JSONField(load_kwargs={'object_pairs_hook': OrderedDict}, default={})

    objects = UserManager()

    USERNAME_FIELD = 'id'

    @property
    def username(self):
        return _('User %i' % self.id)

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return self.get_short_name()

    def get_username(self):
        return self.username

    def is_member(self, group_name):
        '''Check if user is part of a given group by name'''
        return self.groups.filter(name=group_name).exists()

    @vault_post
    def _mirror_user(self, email=None, phone=None):
        '''Get confirmation of or create a corresponding User in the Vault'''
        path = settings.VAULT_MIRROR_USER_PATH
        return path, self.id, token_generator.make_token(self.id)

    @vault_post
    def _delete_mirror(self):
        '''Deletes VaultUser corresponding to User in Vault'''
        path = settings.VAULT_DELETE_MIRROR_PATH
        return path, self.id, token_generator.make_token(self.id)

    @vault_post
    def send_email(self, subject=None, message=None, html_message=None):
        '''Sends an e-mail to the User through the Vault'''
        path = settings.VAULT_SEND_EMAIL_PATH
        return path, self.id, token_generator.make_token(self.id)

    @vault_post
    def send_sms(self, message=None):
        '''Sends an SMS to the User through the Vault'''
        path = settings.VAULT_SEND_SMS_PATH
        return path, self.id, token_generator.make_token(self.id)

    def generate_login_link(self):
        '''Generates a login link URL'''

        current_site = Site.objects.get_current()

        link = '%(protocol)s://%(domain)s%(link)s' % {
            'link': reverse(
                'login_via_email',
                kwargs={
                    'user_id': self.id,
                    'token': token_generator.make_token(self.id),
                }
            ),
            'protocol': 'https' if settings.USE_HTTPS else 'http',
            'domain': current_site.domain,
        }

        return link

    def send_login_link(self):
        '''Sends user login link via email templates'''

        subject = unicode(_("Today's login link"))

        html_template = get_template('email/login_link.html')
        text_template = get_template('email/login_link.txt')

        current_site = Site.objects.get_current()

        manual_login = '%s://%s%s' % (
            'https' if settings.USE_HTTPS else 'http',
            current_site.domain,
            reverse('login'),
        )

        context = {
            'link': self.generate_login_link(),
            'manual_login': manual_login,
            'site_name': current_site.name,
        }

        text_content = text_template.render(Context(context))
        html_content = html_template.render(Context(context))

        self.send_email(
            subject=subject,
            message=text_content,
            html_message=html_content
        )

    def register(self):
        return self, False

    def __unicode__(self):
        return u'%s' % self.id

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')


class StatefulAnonymousUser(AnonymousUser):

    def __init__(self, session):
        self.session = session
        self.data = session.get('user_data', {})

    def is_authenticated(self):
        return True

    def save(self):
        self.session['user_data'] = self.data

    def register(self):
        password = self.data['password']
        del self.data['password']

        user = User.objects.create_user(None, password)

        try:
            del self.data['email']
            del self.data['phone']
        except:
            pass

        User.objects.filter(id=user.id).update(data=self.data)
        user.data = self.data

        return user, True
