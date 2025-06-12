import logging
import requests
import random
from django.core.mail import send_mail
from django.conf import settings
from .models import ApiUsage, ApiLog, MobileValidationCache, PendingVerification

logger = logging.getLogger(__name__)

def send_email_verification_code(user, email, code):
    username = user.username if user else "User"
    try:
        send_mail(
            subject='Verify Your Email Address',
            message=f'Hi {username},\n\nYour email verification code is: {code}\n\nEnter this code to verify your email.\n\nThanks,\nYour Team',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Email verification code sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email verification code to {email}: {str(e)}")
        return False

def validate_mobile_number(user, mobile_number):
    username = user.username if user else "anonymous"

    # Check cache first
    try:
        cached = MobileValidationCache.objects.get(mobile_number=mobile_number)
        message = f"Mobile number {mobile_number} validation retrieved from cache for user {username}: {'Valid' if cached.is_valid else 'Invalid'}"
        logger.info(message)
        ApiLog.objects.create(api_name='cache', message=message, level='INFO')
        return cached.is_valid, "Valid mobile number" if cached.is_valid else "Invalid mobile number"
    except MobileValidationCache.DoesNotExist:
        pass

    try:
        api_usage, created = ApiUsage.objects.get_or_create(api_name='numverify')
        if api_usage.is_limit_exceeded(limit=100):
            message = f"NumVerify API limit exceeded for user {username}"
            logger.warning(message)
            ApiLog.objects.create(api_name='numverify', message=message, level='WARNING')
            return validate_with_abstract_api(user, mobile_number)

        url = f"https://apilayer.net/api/validate?access_key={settings.NUMVERIFY_API_KEY}&number={mobile_number}&country_code=&format=1"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        if not data.get('success', False):
            error_message = data.get('error', {}).get('info', 'Unknown error')
            message = f"NumVerify API error for user {username}: {error_message}"
            logger.warning(message)
            ApiLog.objects.create(api_name='numverify', message=message, level='WARNING')
            return validate_with_abstract_api(user, mobile_number)

        is_valid = data.get('valid', False)
        message = f"Mobile number {mobile_number} {'is valid' if is_valid else 'invalid'} for user {username} (NumVerify)"
        logger.info(message)
        ApiLog.objects.create(api_name='numverify', message=message, level='INFO')

        # Cache the result
        MobileValidationCache.objects.create(mobile_number=mobile_number, is_valid=is_valid)

        return is_valid, "Valid mobile number" if is_valid else "Invalid mobile number"

    except (requests.RequestException, Exception) as e:
        message = f"Error validating mobile number {mobile_number} with NumVerify for user {username}: {str(e)}"
        logger.error(message)
        ApiLog.objects.create(api_name='numverify', message=message, level='ERROR')
        return validate_with_abstract_api(user, mobile_number)

def validate_with_abstract_api(user, mobile_number):
    username = user.username if user else "anonymous"

    try:
        cached = MobileValidationCache.objects.get(mobile_number=mobile_number)
        message = f"Mobile number {mobile_number} validation retrieved from cache for user {username}: {'Valid' if cached.is_valid else 'Invalid'}"
        logger.info(message)
        ApiLog.objects.create(api_name='cache', message=message, level='INFO')
        return cached.is_valid, "Valid mobile number" if cached.is_valid else "Invalid mobile number"
    except MobileValidationCache.DoesNotExist:
        pass

    try:
        api_usage, created = ApiUsage.objects.get_or_create(api_name='abstract')
        if api_usage.is_limit_exceeded(limit=100):
            message = f"Abstract API limit exceeded for user {username}"
            logger.warning(message)
            ApiLog.objects.create(api_name='abstract', message=message, level='WARNING')
            return False, "Verification pending due to API limits"

        url = f"https://phonevalidation.abstractapi.com/v1/?api_key={settings.ABSTRACT_API_KEY}&phone={mobile_number}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        is_valid = data.get('valid', False)
        message = f"Mobile number {mobile_number} {'is valid' if is_valid else 'invalid'} for user {username} (Abstract API)"
        logger.info(message)
        ApiLog.objects.create(api_name='abstract', message=message, level='INFO')

        # Cache the result
        MobileValidationCache.objects.create(mobile_number=mobile_number, is_valid=is_valid)

        return is_valid, "Valid mobile number" if is_valid else "Invalid mobile number"

    except (requests.RequestException, Exception) as e:
        message = f"Error validating mobile number {mobile_number} with Abstract API for user {username}: {str(e)}"
        logger.error(message)
        ApiLog.objects.create(api_name='abstract', message=message, level='ERROR')
        return False, "Verification pending due to API failure"

def send_verification_email(user, request):
    try:
        from django.core.mail import EmailMessage
        from django.urls import reverse
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )

        email = EmailMessage(
            subject='Verify Your Email Address',
            body=f'Hi {user.username},\n\nPlease click the link below to verify your email address:\n{verification_url}\n\nThanks,\nYour Team',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.send(fail_silently=False)
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")

def process_pending_verifications():
    # Check if free tier is available
    numverify_usage, _ = ApiUsage.objects.get_or_create(api_name='numverify')
    abstract_usage, _ = ApiUsage.objects.get_or_create(api_name='abstract')

    if numverify_usage.is_limit_exceeded(settings.NUMVERIFY_FREE_LIMIT) and \
       abstract_usage.is_limit_exceeded(settings.ABSTRACT_FREE_LIMIT):
        return  # Still no free tier available

    # Process pending verifications
    pending_verifications = PendingVerification.objects.filter(is_processed=False)
    for pv in pending_verifications:
        is_valid, message = validate_mobile_number(pv.user, pv.mobile_number)
        if is_valid:
            # Update user profile (assuming UserProfile has a mobile_verified field)
            user_profile = pv.user.userprofile
            user_profile.mobile_verified = True
            user_profile.save()

            # Notify user via email
            send_mail(
                subject='Mobile Number Verification Available',
                message=f'Hi {pv.user.username},\n\nYour mobile number {pv.mobile_number} has been verified successfully!\n\nThanks,\nYour Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pv.user.email],
                fail_silently=False,
            )
            pv.is_processed = True
            pv.save()
        else:
            print(f"Failed to verify {pv.mobile_number}: {message}")