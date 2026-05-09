from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken
    SIMPLEJWT_AVAILABLE = True
except Exception:
    JWTAuthentication = None
    InvalidToken = None
    SIMPLEJWT_AVAILABLE = False
from .models import AdminUser

if SIMPLEJWT_AVAILABLE:
    class AdminJWTAuthentication(JWTAuthentication):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.user_id_claim = "user_id"

        def get_user(self, validated_token):
            try:
                user_id = validated_token[self.user_id_claim]
                return AdminUser.objects.get(id=user_id)
            except AdminUser.DoesNotExist:
                raise InvalidToken("User not found")
            except KeyError:
                raise InvalidToken("Token contains no recognizable user identification")
else:
    class AdminJWTAuthentication(BaseAuthentication):
        def authenticate(self, request):
            raise AuthenticationFailed("JWT authentication is unavailable on this server.")

        def authenticate_header(self, request):
            return "Bearer"
