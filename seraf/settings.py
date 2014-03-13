"""
Django settings for seraf project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'llzkwh=$&0x2*1u^)1&24%ix+_z$io4!gtxo6cxkg=lxqruaz+'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['seraf.inonit.no']

SITE_ID = 1


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'suit',
    'django.contrib.admin',

    'south',
    'django_extensions',
    'rest_framework',
    'filer',
    'mptt',
    'easy_thumbnails',
    'mail_templated',
    'plumbing',

    'users',
    'vault',
    'sms',
    'tasks',
    'events',
    'content',
    'system',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


# Auth backends

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'users.backends.TokenBackend',
)

ROOT_URLCONF = 'seraf.urls'

WSGI_APPLICATION = 'seraf.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'seraf.db'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'nb'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'conf/locale'),
)

TIME_ZONE = 'Europe/Oslo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_HTTPS = True


# E-mail settings

ADMINS = (
    ('Eirik', 'eirik.krogstad@inonit.no'),
)
SERVER_EMAIL = 'SERAF <post@inonit.no>'
DEFAULT_FROM_EMAIL = 'SERAF <post@inonit.no>'
EMAIL_SUBJECT_PREFIX = '[SERAF] '
EMAIL_HOST_USER = 'AKIAJYR7AW6SXUYTVI2Q'
EMAIL_HOST_PASSWORD = 'AuzX2+v7uGKwnYOupxZLGBsOh+b3RCdKtekyBHPLSxkY'
EMAIL_HOST = 'email-smtp.eu-west-1.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'staticfiles'),
)


# User model and vault separation

AUTH_USER_MODEL = 'users.User'

VAULT_SERVER_API_URL = 'http://127.0.0.1:8000/api/vault/'

VAULT_MIRROR_USER = 'mirror_user/'
VAULT_DELETE_MIRROR = 'delete_mirror/'
VAULT_SEND_EMAIL_URL = 'send_email/'
VAULT_SEND_SMS_URL = 'send_sms/'
VAULT_FETCH_SMS_URL = 'fetch_sms/'


# Token

TOKEN_TIMEOUT_DAYS = 1


# Twilio

TWILIO_ACCOUNT_SID = 'xxxxx'
TWILIO_AUTH_TOKEN = 'xxxxx'


# Huey

HUEY = {
    'backend': 'huey.backends.redis_backend',
    'name': 'seraf',
    'connection': {
        'host': 'localhost',
        'port': 6379,
    },

    # Options to pass into the consumer when running `manage.py run_huey`
    'consumer_options': {
        'workers': 4,
    },
}


# REST Framework

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        'rest_framework.permissions.AllowAny',
    ]
}


# Admin interface

SUIT_CONFIG = {
    'ADMIN_NAME': 'SERAF admin',
    'HEADER_DATE_FORMAT': 'l j. F Y',

    'SEARCH_URL': '/admin/system/page/',

    'MENU': [
        {
            'app': 'users',
            'label': 'Brukere',
            'icon': 'icon-user',
            'models':
                [
                    'user',
                    'auth.groups',
                ]
        },
        {
            'app': 'system',
            'label': 'Program',
            'icon': 'icon-cog',
            'models':
                [
                    'program',
                    'part',
                    'page'
                ]
        },
        {
            'app': 'events',
            'label': 'Hendelser',
            'icon': 'icon-bullhorn',
            'models':
                [
                    'event',
                    'tasks.task',
                ]
        },
        {
            'app': 'filer',
            'label': 'Media',
            'icon': 'icon-picture'
        },
    ]
}

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose'
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'users.views': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

try:
    from local_settings import *
except ImportError:
    pass
