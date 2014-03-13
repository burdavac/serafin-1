from __future__ import unicode_literals
import json

from django.test import TestCase
from django.test.client import RequestFactory
from mock import Mock

from token_auth.json_status import STATUS_OK, STATUS_INVALID_TOKEN, STATUS_USER_DOES_NOT_EXIST

from token_auth.tokens import token_generator
from vault.decorators import json_response
from vault.models import VaultUser


class TestJsonResponse(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        VaultUser.objects.create(id=1, email='test@seraf.no', phone='1234567890')

    def test_okay(self):
        user_id = 1
        token = token_generator.make_token(user_id)

        func = Mock()
        decorated_func = json_response(func)
        request = self.factory.post(
            '/',
            {
                'user_id': user_id,
                'token': token
            }
        )
        response = decorated_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content).get('status'), STATUS_OK)

    def test_invalid_token(self):
        user_id = 1
        token = 'invalidtoken'

        func = Mock()
        decorated_func = json_response(func)
        request = self.factory.post(
            '/',
            {
                'user_id': user_id,
                'token': token
            }
        )
        response = decorated_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content).get('status'), STATUS_INVALID_TOKEN)

    def test_missing_user(self):
        user_id = 2
        token = token_generator.make_token(user_id)

        func = Mock()
        decorated_func = json_response(func)
        request = self.factory.post(
            '/',
            {
                'user_id': user_id,
                'token': token
            }
        )
        response = decorated_func(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content).get('status'), STATUS_USER_DOES_NOT_EXIST)