from __future__ import unicode_literals

from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout_then_login as django_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
import datetime
import logging

logger = logging.getLogger('users.views')

@login_required()
def profile(request):
    logger.debug('Loding user page')
    template_name="profile.html"

    context = {
               'title': 'Welcome to your profile',
               }
    return render_to_response(
                              template_name,
                              context
                              )

def login(request, template_name="login.html"):
    """ Manual login to seraf """
    logger.debug('Loding login page')
    return django_login(request, **{"template_name" : template_name})

def logout(request, template_name="login.html"):
    '''Manual Logout of seraf'''
    logger.debug('User logging out')
    return django_logout(request)

