from __future__ import unicode_literals
from django.contrib.auth.backends import ModelBackend

from tokens.tokens import token_generator
from users.models import User


class TokenBackend(ModelBackend):
    """
    Authenticate user against id and token
    """

    def authenticate(self, user_id, token):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        if token_generator.check_token(user_id, token):
            return user

    def get_user(self, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None

        return user
