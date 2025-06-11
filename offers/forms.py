from django.contrib.auth.models import User
from offers.models import UserProfile

class CustomSignupForm:
    def __init__(self, *args, **kwargs):
        from allauth.account.forms import SignupForm
        self.__class__.__bases__ = (SignupForm,)
        super().__init__(*args, **kwargs)

    def save(self, request):
        # Save the user using the parent class's save method
        user = super().save(request)
        
        # Create or get the UserProfile and send verification email
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        user_profile.email_verified = False
        user_profile.save()
        
        # Lazy import to avoid circular import
        from offers.utils import send_verification_email
        send_verification_email(user, request)
        
        return user