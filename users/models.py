from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.conf import settings
import requests
import json


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

    objects = UserManager()

    USERNAME_FIELD = 'id'

    @property
    def username(self):
        return _('User %i' % self.id)

    def get_short_name(self):
        return self.username

    def get_username(self):
        return self.username

    def update_token(self):
        '''Update User authentication token for the Vault'''
        pass

    def vault_post(func):
        '''Decorator for posting to the Vault'''
        def _vault_post(*args, **kwargs):

            url, user_id, token = func(*args, **kwargs)

            if url and user_id and token:
                data = {
                    'user_id': user_id,
                    'token': token,
                }
                data.update(kwargs)

                response = requests.post(url, data=json.dumps(data))
                response.raise_for_status()

                response_json = response.json()
                if 'status' in response_json and response_json['status'] == 'ok':
                    return True

            return False

    @vault_post
    def send_email(self, subject=None, message=None, html_message=None):
        '''Send an e-mail to the User through the Vault'''
        self.update_token()
        url = settings.VAULT_SEND_EMAIL_URL

        return url, self.id, self.token

    @vault_post
    def send_sms(self, message=None):
        '''Send an sms to the User through the Vault'''
        self.update_token()
        url = settings.VAULT_SEND_SMS_URL

        return url, self.id, self.token

    def __unicode__(self):
        return unicode(self.username)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')


class UserField(models.Model):
    '''A simple modelling of User key: value relationships'''

    user = models.ForeignKey(User, verbose_name=_('user'))
    key = models.CharField(_('key name'), max_length=64)
    value = models.CharField(_('value'), max_length=64, blank=True)

    is_required = models.BooleanField(_('required field'), default=False)

    def __unicode__(self):
        return '%s: %s' % (self.key, self.value)

    class Meta:
        verbose_name = _('userfield')
        verbose_name_plural = _('userfields')