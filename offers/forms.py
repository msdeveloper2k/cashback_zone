from allauth.account.forms import SignupForm
from django import forms
from offers.models import UserProfile, PendingVerification, ContactInfo
from offers.utils import send_email_verification_code, validate_mobile_number, send_verification_email
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
import re
import logging
import random

logger = logging.getLogger(__name__)

class CustomSignupForm(SignupForm):
    mobile_number = forms.CharField(max_length=15, required=True, label="Mobile Number")
    email_verification_code = forms.CharField(max_length=6, required=False, label="Email Verification Code")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_mobile_number(self):
        mobile = self.cleaned_data['mobile_number']
        if not re.match(r'^\+\d{10,15}$', mobile):
            raise ValidationError("Mobile number must start with a '+' followed by 10-15 digits (e.g., +919876543210).")
        return mobile

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        mobile_number = cleaned_data.get('mobile_number')
        email_code = cleaned_data.get('email_verification_code')

        if email and email_code:
            expected_code = self.request.session.get('email_verification_code')
            if email_code != expected_code:
                raise ValidationError("Invalid email verification code.")
            self.request.session['email_verified'] = True
        elif email and not self.request.session.get('email_verified'):
            code = str(random.randint(100000, 999999))
            self.request.session['email_verification_code'] = code
            send_email_verification_code(self.request.user, email, code)
            raise ValidationError("Please enter the email verification code sent to your email.")

        if mobile_number:
            is_valid, message = validate_mobile_number(self.request.user, mobile_number)
            if is_valid:
                self.request.session['mobile_verified'] = True
            else:
                if "pending" in message:
                    if not PendingVerification.objects.filter(user=self.request.user, is_processed=False).exists():
                        PendingVerification.objects.create(user=self.request.user, mobile_number=mobile_number)
                        try:
                            send_mail(
                                subject='Mobile Number Verification Pending',
                                message=f'Hi,\n\nWe couldn’t verify your mobile number {mobile_number} right now due to API issues. You’ll be notified when verification is available.\n\nThanks,\nYour Team',
                                from_email=self.request.settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[email],
                                fail_silently=False,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send verification pending email to {email}: {str(e)}")
                    raise ValidationError("Mobile verification is pending due to API issues. Please wait or contact support.")
                else:
                    raise ValidationError("Invalid mobile number format.")

        return cleaned_data

    def save(self, request):
        user = super().save(request)
        return user

    def signup(self, request, user):
        mobile_number = self.cleaned_data.get('mobile_number')
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        user_profile.mobile_verified = request.session.get('mobile_verified', False)
        user_profile.email_verified = request.session.get('email_verified', False)
        user_profile.save()

        if not user_profile.mobile_verified:
            PendingVerification.objects.filter(mobile_number=mobile_number, user__isnull=True).update(user=user)

        request.session.pop('email_verification_code', None)
        request.session.pop('email_verified', None)
        request.session.pop('mobile_verified', None)

        try:
            send_verification_email(user, request)
        except Exception as e:
            logger.error(f"Failed to send email verification to {user.email}: {str(e)}")

class UpdateMobileForm(forms.Form):
    mobile_number = forms.CharField(max_length=15, required=True, label="New Mobile Number")

    def __init__(self, *args, user=None, request=None, **kwargs):
        self.user = user
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_mobile_number(self):
        mobile = self.cleaned_data['mobile_number']
        if not re.match(r'^\+\d{10,15}$', mobile):
            raise ValidationError("Mobile number must start with a '+' followed by 10-15 digits (e.g., +919876543210).")
        return mobile

    def clean(self):
        cleaned_data = super().clean()
        mobile_number = cleaned_data.get('mobile_number')

        if mobile_number:
            is_valid, message = validate_mobile_number(self.user, mobile_number)
            if is_valid:
                self.request.session['mobile_verified'] = True
            else:
                if "pending" in message:
                    if not PendingVerification.objects.filter(user=self.user, is_processed=False).exists():
                        PendingVerification.objects.create(user=self.user, mobile_number=mobile_number)
                        try:
                            send_mail(
                                subject='Mobile Number Verification Pending',
                                message=f'Hi {self.user.username},\n\nWe couldn’t verify your mobile number {mobile_number} right now due to API issues. You’ll be notified when verification is available.\n\nThanks,\nYour Team',
                                from_email=self.request.settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[self.user.email],
                                fail_silently=False,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send verification pending email to {self.user.email}: {str(e)}")
                    raise ValidationError("Mobile verification is pending due to API issues. Please wait or contact support.")
                else:
                    raise ValidationError("Invalid mobile number format.")

        return cleaned_data

    def save(self, request):
        mobile_number = self.cleaned_data.get('mobile_number')
        user_profile = self.user.userprofile

        user_profile.mobile_verified = request.session.get('mobile_verified', False)
        user_profile.save()

        request.session.pop('mobile_verified', None)

class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ['name', 'email', 'mobile']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'mobile': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg'}),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        if not re.match(r'^\+\d{10,15}$', mobile):
            raise ValidationError("Mobile number must start with a '+' followed by 10-15 digits (e.g., +919876543210).")
        return mobile