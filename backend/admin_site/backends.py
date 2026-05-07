from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from .models import AdminUser

class AdminUserBackend(BaseBackend):
    """
    Custom authentication backend for AdminUser model.
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None
        
        try:
            normalized_email = (email or '').strip()
            user = AdminUser.objects.get(email__iexact=normalized_email)
        except AdminUser.DoesNotExist:
            return None
        
        if user.check_password(password) and user.is_active:
            return user
        return None
    
    def get_user(self, user_id):
        try:
            return AdminUser.objects.get(pk=user_id)
        except AdminUser.DoesNotExist:
            return None
