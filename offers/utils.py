import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

def send_verification_email(user, request):
    # Generate a unique token
    token = str(uuid.uuid4())
    
    # Save the token to the user's profile
    user_profile = user.userprofile
    user_profile.email_verification_token = token
    user_profile.email_verified = False
    user_profile.save()

    # Create the verification URL
    verification_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'token': token})
    )

    # Email subject and message
    subject = 'Verify Your Email Address'
    message = (
        f'Hi {user.username},\n\n'
        f'Please verify your email address by clicking the link below:\n\n'
        f'{verification_url}\n\n'
        f'If you did not register for this account, please ignore this email.\n\n'
        f'Thanks,\nYour Team'
    )

    # Send the email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

    return True