from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context
from django.template.loader import get_template
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt

from serafin.utils import JSONResponse
from system.engine import Engine
from tokens.tokens import token_generator
from vault.decorators import json_response
from vault.models import VaultUser
from twilio.twiml import Response
import json
import requests


@csrf_exempt
@json_response
def mirror_user(request, *args, **kwargs):
    '''Store user sensitive information to vault'''

    vault_user, created = VaultUser.objects.get_or_create(id=kwargs['user_id'])

    data = kwargs.get('data')
    email = data.get('email')
    phone = data.get('phone')

    if email and phone:
        vault_user.email = email
        vault_user.phone = phone

    vault_user.save()


@csrf_exempt
@json_response
def delete_mirror(request, *args, **kwargs):
    '''Remove user associated sensitive information from vault'''

    vault_user = VaultUser.objects.get(id=kwargs['user_id'])

    if vault_user:
        vault_user.delete()


@csrf_exempt
@json_response
def send_email(request, *args, **kwargs):
    '''Send email to vault user'''

    vault_user = VaultUser.objects.get(id=kwargs['user_id'])

    data = kwargs.get('data')
    subject = data.get('subject')
    message = data.get('message')
    html_message = data.get('html_message')

    if vault_user:
        vault_user.send_email(subject, message, html_message)


@csrf_exempt
@json_response
def send_sms(request, *args, **kwargs):
    '''Send sms to vault user'''

    vault_user = VaultUser.objects.get(id=kwargs['user_id'])

    data = kwargs.get('data')
    message = data.get('message')

    if vault_user and message:
        vault_user.send_sms(message=message)


@csrf_exempt
def receive_sms(request):
    '''Receive sms message from user, process through main API and respond'''

    response = Response()
    if request.method == 'POST':

        sender = request.POST.get('From')
        body = request.POST.get('Body')
        url = settings.USERS_RECEIVE_SMS_URL

        try:
            vault_user = VaultUser.objects.get(phone=sender)
            token = token_generator.make_token(vault_user.id)
            data = {
                'user_id': vault_user.id,
                'token': token,
                'message': body,
            }

            result = requests.post(url, data=json.dumps(data))
            result.raise_for_status()
        except VaultUser.ObjectDoesNotExist:
            response.message(_('Sorry, there was an error processing your SMS.') + ' (number mismatch)')
        except requests.exceptions.HTTPError:
            response.message(_('Sorry, there was an error processing your SMS.') + ' (%s)' % result.status_code)
        except:
            response.message(_('Sorry, there was an error processing your SMS.') + ' (unknown)')
    else:
        response.message(_('No data received.'))

    return HttpResponse(response, content_type='text/xml')


@csrf_exempt
def password_reset(request):
    '''Send password reset email'''

    data = json.loads(request.body)

    vault_user = VaultUser.objects.get(email__iexact=data.get('email'))

    protocol = data.get('protocol')
    domain = data.get('domain')
    path = data.get('path')
    site_name = data.get('site_name')

    if vault_user and protocol and domain and path and site_name:

        link = '%(protocol)s://%(domain)s%(path)s%(uid)s/%(token)s' % {
            'protocol': protocol,
            'domain': domain,
            'path': path,
            'uid': urlsafe_base64_encode(force_bytes(vault_user.id)),
            'token': token_generator.make_token(vault_user.id),
        }

        subject_template = get_template('registration/password_reset_subject.txt')
        content_template = get_template('registration/password_reset_email.html')

        context = {
            'site_name': site_name,
            'link': link,
            'user': vault_user,
        }

        subject = subject_template.render(Context({'site_name': site_name}))
        subject = ''.join(subject.splitlines())
        content = content_template.render(Context(context))

        if subject and content:
            vault_user.send_email(subject, content)

        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'bad data'})
