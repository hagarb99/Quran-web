from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class PhoneOrEmailBackend(ModelBackend):
    """
    Authenticate using username, email, or phone number.
    Ensures suspended users cannot log in.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('phone') or kwargs.get('email')
        if not username or not password:
            return None
        
        username = str(username).strip()
        try:
            user = User.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(phone=username)
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(phone=username)
            ).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            if user.is_suspended:
                return None
            return user
        return None

