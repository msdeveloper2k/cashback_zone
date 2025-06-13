from datetime import datetime, timedelta, timezone
from email import utils
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import AdBanner, ApiLog, ApiUsage, Offer, Referral, ReferralClick, TutorialVideo, UserProfile, PendingVerification, ContactInfo, GoogleFormSubmission, ConversionProof
from django.utils.dateparse import parse_datetime
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from allauth.account.models import EmailAddress
from allauth.account.views import EmailView
from .forms import ContactInfoForm, CustomSignupForm, UpdateMobileForm
from django.db import IntegrityError
import random
from django_ratelimit.decorators import ratelimit
import logging
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from allauth.account.views import SignupView
from django.core.mail import send_mail
import string
import time

# CAPTCHA options (simple image-based CAPTCHA with descriptions)
CAPTCHA_OPTIONS = [
    {'description': 'Select the image of a tree', 'correct': 'tree.jpg', 'images': ['tree.jpg', 'car.jpg', 'dog.jpg']},
    {'description': 'Select the image of a car', 'correct': 'car.jpg', 'images': ['tree.jpg', 'car.jpg', 'dog.jpg']},
    {'description': 'Select the image of a dog', 'correct': 'dog.jpg', 'images': ['tree.jpg', 'car.jpg', 'dog.jpg']},
]

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def index(request):
    offers = Offer.objects.filter(is_active='active')
    return render(request, 'index.html', {'offers': offers})

def offer_info(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    referral = None
    
    if request.user.is_authenticated:
        referral = Referral.objects.filter(user=request.user, offer=offer).first()
        if not referral:
            referral = Referral.objects.create(
                user=request.user,
                offer=offer,
                working_state='pending'
            )
    else:
        if not request.session.session_key:
            request.session.create()
        visitor_id = request.session.session_key
        referral = Referral.objects.filter(visitor_identifier=visitor_id, offer=offer).first()
        if not referral:
            referral = Referral.objects.create(
                visitor_identifier=visitor_id,
                offer=offer,
                working_state='pending'
            )
    
    context = {
        'offer': offer,
        'referral': referral,
    }
    return render(request, 'offer_info.html', context)

def refer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    if not request.user.is_authenticated:
        request.session['referral_offer_id'] = offer_id
        return redirect('account_signup')
    
    if request.method == 'POST':
        existing_referral = Referral.objects.filter(user=request.user, offer=offer).first()
        if existing_referral:
            message = f"You have already referred this offer! Referral ID: {existing_referral.id}"
        else:
            referral = Referral.objects.create(
                user=request.user,
                offer=offer,
                working_state='pending'
            )
            message = f'Referral submitted successfully! Referral ID: {referral.id}'
        return render(request, 'refer_message.html', {'message': message})
    else:
        return redirect('offer_detail', offer_id=offer_id)

def confirm_google_form_submission(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    
    if request.method == 'POST':
        if request.user.is_authenticated:
            submission, created = GoogleFormSubmission.objects.get_or_create(
                user=request.user,
                offer=offer,
                defaults={'submitted': True}
            )
            if not created:
                submission.submitted = True
                submission.save()
        else:
            if not request.session.session_key:
                request.session.create()
            visitor_id = request.session.session_key
            submission, created = GoogleFormSubmission.objects.get_or_create(
                visitor_identifier=visitor_id,
                offer=offer,
                defaults={'submitted': True}
            )
            if not created:
                submission.submitted = True
                submission.save()
        
        messages.success(request, "Google Form submission confirmed!")
        return redirect('offer_detail', offer_id=offer.id)
    
    return redirect('offer_detail', offer_id=offer.id)

# Submit Conversion Proof View
def submit_conversion_proof(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to submit conversion proof.")
            return redirect('account_login')
        
        # Handle multiple image uploads
        proof_images = request.FILES.getlist('proof_images')
        if not proof_images:
            messages.error(request, "Please upload at least one proof image.")
            return redirect('offer_detail', offer_id=offer.id)
        
        # Save each image as a separate ConversionProof entry
        for image in proof_images:
            ConversionProof.objects.create(
                user=request.user,
                offer=offer,
                image=image,
                status='pending'
            )
        
        messages.success(request, "Conversion proof submitted successfully! It will be reviewed soon.")
        return redirect('offer_detail', offer_id=offer.id)
    
    return redirect('offer_detail', offer_id=offer.id)

# Offer Detail View
def offer_detail(request, offer_id, referral_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    referral_url = None
    offer_referral = None
    email_not_verified = False
    contact_info_submitted = False
    google_form_completed = False
    proof_submitted = False
    proof_status = None
    email_verified = False
    mobile_verified = False
    tutorial_videos = TutorialVideo.objects.filter(offer=offer)
    ad_banners = AdBanner.objects.filter(offer=offer)
    captcha = None
    referral_message = None

    # Handle referral if referral_id is provided
    if referral_id:
        try:
            referral = get_object_or_404(Referral, id=referral_id, offer=offer)
            # Check for unique click
            ip_address = get_client_ip(request)
            session_key = request.session.session_key or request.session.create()
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            click_exists = ReferralClick.objects.filter(
                referral=referral,
                ip_address=ip_address,
                clicked_at__gte=time_threshold
            ).exists()

            if not click_exists:
                referral.click_count += 1
                referral.save()
                ReferralClick.objects.create(
                    referral=referral,
                    ip_address=ip_address,
                    session_key=session_key
                )
                logger.info(f"Unique click recorded: referral_id={referral_id}, clicks={referral.click_count}, client_ip={ip_address}")
            else:
                logger.info(f"Non-unique click ignored: referral_id={referral_id}, client_ip={ip_address}")

            offer_referral = referral
            referral_url = request.build_absolute_uri(
                reverse('offer_detail_with_referral', kwargs={'offer_id': offer.id, 'referral_id': referral.id})
            )
            messages.info(request, f"You were referred by {referral.user.username if referral.user else 'an anonymous user'}.")
        except Referral.DoesNotExist:
            messages.error(request, "Invalid referral link.")

    if request.user.is_authenticated:
        # Check email verification
        if not request.user.userprofile.email_verified:
            email_not_verified = True
        else:
            # Get or create referral if no referral_id is provided
            if not referral_id:
                offer_referral, created = Referral.objects.get_or_create(user=request.user, offer=offer)
                referral_url = request.build_absolute_uri(
                    reverse('offer_detail_with_referral', kwargs={'offer_id': offer.id, 'referral_id': offer_referral.id})
                )
                if created:
                    referral_message = "Referral created successfully! Share your referral link to earn rewards."

        # Check verification status
        email_verified = request.user.userprofile.email_verified
        mobile_verified = request.user.userprofile.mobile_verified

        # Check if contact info is submitted
        contact_info_submitted = ContactInfo.objects.filter(user=request.user, offer=offer).exists()

        # Check if Google Form is completed
        google_form_completed = GoogleFormSubmission.objects.filter(user=request.user, offer=offer).exists()

        # Check if conversion proof is submitted
        proof_submitted = ConversionProof.objects.filter(user=request.user, offer=offer).exists()
        if proof_submitted:
            latest_proof = ConversionProof.objects.filter(user=request.user, offer=offer).latest('submitted_at')
            proof_status = latest_proof.status

        # Profile info for user section
        profile_info = {
            'username': request.user.username,
            'email': request.user.email,
            'joined': request.user.date_joined,
        }
        profile_level = request.user.userprofile.profile_level

    else:
        if not request.session.session_key:
            request.session.create()
        visitor_id = request.session.session_key
        google_form_completed = GoogleFormSubmission.objects.filter(visitor_identifier=visitor_id, offer=offer).exists()

    # Generate CAPTCHA if required
    if offer.requires_contact_info and not contact_info_submitted:
        captcha_id = request.session.get('captcha_id')
        if not captcha_id:
            captcha_id = random.randint(0, len(CAPTCHA_OPTIONS) - 1)
            request.session['captcha_id'] = captcha_id
            request.session['captcha_correct'] = CAPTCHA_OPTIONS[captcha_id]['correct']
        captcha = CAPTCHA_OPTIONS[captcha_id]

    if request.method == 'POST' and request.user.is_authenticated:
        form = ContactInfoForm(request.POST)
        if form.is_valid():
            # Verify CAPTCHA
            if captcha:
                selected_image = request.POST.get('captcha_image')
                correct_image = request.session.get('captcha_correct')
                if selected_image != correct_image:
                    messages.error(request, "CAPTCHA verification failed. Please try again.")
                    return render(request, 'offer_detail.html', {
                        'offer': offer,
                        'offer_referral': offer_referral,
                        'referral_url': referral_url,
                        'email_not_verified': email_not_verified,
                        'contact_info_submitted': contact_info_submitted,
                        'google_form_completed': google_form_completed,
                        'proof_submitted': proof_submitted,
                        'proof_status': proof_status,
                        'email_verified': email_verified,
                        'mobile_verified': mobile_verified,
                        'tutorial_videos': tutorial_videos,
                        'ad_banners': ad_banners,
                        'captcha': captcha,
                        'referral_message': referral_message,
                        'profile_info': profile_info if request.user.is_authenticated else None,
                        'profile_level': profile_level if request.user.is_authenticated else None,
                        'contact_form': form,
                    })

            # Clear CAPTCHA session data
            request.session.pop('captcha_id', None)
            request.session.pop('captcha_correct', None)

            contact_info = form.save(commit=False)
            contact_info.user = request.user
            contact_info.offer = offer
            if offer_referral:
                contact_info.referral = offer_referral
            contact_info.save()
            messages.success(request, "Contact info submitted successfully!")
            return redirect('offer_info', offer_id=offer.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Fetch mobile from ContactInfo instead of UserProfile
        mobile = '+911234567890'  # Default mobile number
        if request.user.is_authenticated and request.user.userprofile.mobile_verified:
            contact_info = request.user.contactinfo_set.first()
            mobile = contact_info.mobile if contact_info else '+911234567890'

        form = ContactInfoForm(initial={
            'email': request.user.email if request.user.is_authenticated else '',
            'mobile': mobile
        })

    return render(request, 'offer_detail.html', {
        'offer': offer,
        'offer_referral': offer_referral,
        'referral_url': referral_url,
        'email_not_verified': email_not_verified,
        'contact_info_submitted': contact_info_submitted,
        'google_form_completed': google_form_completed,
        'proof_submitted': proof_submitted,
        'proof_status': proof_status,
        'email_verified': email_verified,
        'mobile_verified': mobile_verified,
        'tutorial_videos': tutorial_videos,
        'ad_banners': ad_banners,
        'captcha': captcha,
        'referral_message': referral_message,
        'profile_info': profile_info if request.user.is_authenticated else None,
        'profile_level': profile_level if request.user.is_authenticated else None,
        'contact_form': form,
    })

@csrf_exempt
def postback(request):
    # Ensure this is a POST request from an advertiser
    if request.method != 'POST':
        logger.warning(f"Invalid postback request: method={request.method}, client_ip={request.META.get('REMOTE_ADDR')}")
        return HttpResponse("Invalid request method", status=400)

    # Validate the request (e.g., check for an API key or specific parameters)
    api_key = request.POST.get('api_key')  # Example: Require an API key
    if not api_key or api_key != 'your_secret_api_key':  # Replace with your actual validation
        logger.warning(f"Invalid postback request: missing or incorrect API key, client_ip={request.META.get('REMOTE_ADDR')}")
        return HttpResponse("Unauthorized", status=401)

    referral_id = request.GET.get('referral_id') or request.POST.get('referral_id')
    if not referral_id:
        logger.warning(f"Postback missing referral_id, client_ip={request.META.get('REMOTE_ADDR')}")
        return HttpResponse("Missing referral_id", status=400)

    try:
        referral = get_object_or_404(Referral, id=referral_id)
        referral.click_count += 1
        referral.working_state = 'clicked'
        referral.save()
        logger.info(f"Postback triggered: referral_id={referral_id}, state=clicked, clicks={referral.click_count}, client_ip={request.META.get('REMOTE_ADDR')}")
        return HttpResponse("Postback processed", status=200)
    except Exception as e:
        logger.error(f"Postback error: {str(e)}, referral_id={referral_id}, client_ip={request.META.get('REMOTE_ADDR')}")
        return HttpResponse("Error processing postback", status=500)

@login_required
def user_dashboard(request):
    user = request.user

    try:
        user_profile, created = UserProfile.objects.get_or_create(user=user)
    except Exception as e:
        logger.error(f"Error creating/retrieving UserProfile for user {user.username}: {str(e)}")
        messages.error(request, "An error occurred while loading your profile. Please try again later.")
        return render(request, 'dashboard.html', {})

    if request.method == 'POST':
        mobile_form = UpdateMobileForm(request.POST, user=user, request=request)
        if mobile_form.is_valid():
            mobile_form.save(request)
            if user_profile.mobile_verified:
                messages.success(request, "Mobile number updated and verified successfully!")
            else:
                messages.info(request, "Mobile number updated, but verification is pending due to API issues. You'll be notified when verification is available.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        mobile_form = UpdateMobileForm(user=user, request=request)

    profile_info = {
        'username': user.username,
        'email': user.email,
        'joined': user.date_joined,
    }

    try:
        referrals = Referral.objects.filter(user=user).select_related('offer')
    except Exception as e:
        logger.error(f"Error fetching referrals for user {user.username}: {str(e)}")
        referrals = []
        messages.error(request, "An error occurred while fetching your referrals.")

    referral_urls = {}
    for referral in referrals:
        try:
            offer = referral.offer
            kwargs = {'offer_id': offer.id}
            if referral.id:
                kwargs['referral_id'] = referral.id
            referral_urls[offer.id] = request.build_absolute_uri(reverse('offer_detail_with_referral', kwargs=kwargs))
        except Exception as e:
            logger.error(f"Error generating referral URL for referral {referral.id}: {str(e)}")
            continue

    try:
        contact_infos = ContactInfo.objects.filter(user=user).select_related('offer', 'referral')
    except Exception as e:
        logger.error(f"Error fetching contact infos for user {user.username}: {str(e)}")
        contact_infos = []
        messages.error(request, "An error occurred while fetching your contact info submissions.")

    try:
        total_referrals = len(referrals)
        clicked_referrals = sum(1 for r in referrals if r.working_state == 'clicked')
        converted_referrals = sum(1 for r in referrals if r.working_state == 'converted')
    except Exception as e:
        logger.error(f"Error calculating referral statistics for user {user.username}: {str(e)}")
        total_referrals = clicked_referrals = converted_referrals = 0

    try:
        pending_verification = PendingVerification.objects.filter(user=user, is_processed=False).exists()
    except Exception as e:
        logger.error(f"Error checking pending verification for user {user.username}: {str(e)}")
        pending_verification = False

    # Admin-specific data
    api_status = {}
    api_config = {}
    api_logs = []
    if user.is_staff:
        # API Status
        try:
            numverify_usage = ApiUsage.objects.get(api_name='numverify')
            abstract_usage = ApiUsage.objects.get(api_name='abstract')
            api_status = {
                'numverify': {
                    'status': 'active' if not numverify_usage.is_limit_exceeded(100) else 'inactive',
                    'request_count': numverify_usage.request_count,
                    'limit': 100,
                },
                'abstract': {
                    'status': 'active' if not abstract_usage.is_limit_exceeded(100) else 'inactive',
                    'request_count': abstract_usage.request_count,
                    'limit': 100,
                },
            }
        except Exception as e:
            logger.error(f"Error fetching API status for admin {user.username}: {str(e)}")
            api_status = {
                'numverify': {'status': 'unknown', 'request_count': 0, 'limit': 100},
                'abstract': {'status': 'unknown', 'request_count': 0, 'limit': 100},
            }

        # API Configuration
        api_config = {
            'numverify_key': settings.NUMVERIFY_API_KEY,
            'abstract_key': settings.ABSTRACT_API_KEY,
            'request_limit': 100,
        }

        # API Logs (last 10 entries)
        try:
            api_logs = ApiLog.objects.all().order_by('-timestamp')[:10]
        except Exception as e:
            logger.error(f"Error fetching API logs for admin {user.username}: {str(e)}")

    context = {
        'profile_info': profile_info,
        'profile_level': user_profile.profile_level,
        'user': user,
        'email_not_verified': not user_profile.email_verified,
        'mobile_form': mobile_form,
        'pending_verification': pending_verification,
        'contact_infos': contact_infos,
        'total_referrals': total_referrals,
        'clicked_referrals': clicked_referrals,
        'converted_referrals': converted_referrals,
        'referrals': referrals,
        'referral_urls': referral_urls,
        'api_status': api_status,
        'api_config': api_config,
        'api_logs': api_logs,
    }

    return render(request, 'dashboard.html', context)

@ratelimit(key='ip', rate='100/5m', method='GET', block=True)
@ratelimit(key='ip', rate='100/5m', method='POST', block=True)
def grab_offer(request, offer_id, referral_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    redirect_url = offer.link

    # Initialize referral
    if referral_id:
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            referral = None
            logger.warning(f"Referral with id {referral_id} not found, client_ip={get_client_ip(request)}")
    else:
        referral = None

    # Get client IP and session key for click tracking
    ip_address = get_client_ip(request)
    session_key = request.session.session_key or request.session.create()

    # Check if this IP has clicked this referral within the last 24 hours
    click_exists = False
    if referral:
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        click_exists = ReferralClick.objects.filter(
            referral=referral,
            ip_address=ip_address,
            clicked_at__gte=time_threshold
        ).exists()

    if offer.requires_contact_info:
        if request.method == 'POST':
            # Validate CAPTCHA
            selected_image = request.POST.get('captcha_image')
            correct_image = request.session.get('captcha_correct')
            if selected_image != correct_image:
                messages.error(request, 'CAPTCHA verification failed. Please try again.')
                return redirect('offer_detail', offer_id=offer.id)

            # Clear CAPTCHA session data
            request.session.pop('captcha_id', None)
            request.session.pop('captcha_correct', None)

            name = request.POST.get('name')
            email = request.POST.get('email')
            mobile = request.POST.get('mobile')
            
            # Attempt to save the contact info, handle duplicates
            try:
                contact_info = ContactInfo.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    offer=offer,
                    referral=referral,
                    name=name,
                    email=email,
                    mobile=mobile,
                    visitor_identifier=request.session.session_key if not request.user.is_authenticated else None
                )
                
                # For authenticated users, check verification status
                if request.user.is_authenticated:
                    user_profile = request.user.userprofile
                    if not (user_profile.email_verified or user_profile.mobile_verified):
                        # Trigger email verification if email is not verified
                        if not user_profile.email_verified:
                            send_verification_email(request.user, request)
                            messages.info(request, 'A verification email has been sent to your email address.')
                        # Trigger mobile verification if mobile is not verified and not pending
                        if not user_profile.mobile_verified and not PendingVerification.objects.filter(user=request.user, is_processed=False).exists():
                            mobile_form = UpdateMobileForm({'mobile_number': mobile}, user=request.user)
                            if mobile_form.is_valid():
                                mobile_form.save(request)
                                messages.info(request, 'A mobile verification request has been initiated.')
                            else:
                                messages.error(request, 'Invalid mobile number format. Please update your mobile number on the dashboard.')

                messages.success(request, 'Offer grabbed successfully! Your contact info has been saved.')
                
                # Increment click_count only for unique clicks within 24 hours
                if referral and not click_exists:
                    referral.click_count += 1
                    referral.working_state = 'clicked'
                    referral.save()
                    ReferralClick.objects.create(
                        referral=referral,
                        ip_address=ip_address,
                        session_key=session_key
                    )
                    logger.info(f"Offer grabbed: referral_id={referral_id}, state=clicked, clicks={referral.click_count}, client_ip={ip_address}")
                
                redirect_url = offer.link if offer.link else reverse('offer_detail', kwargs={'offer_id': offer.id})
            except IntegrityError as e:
                if 'email' in str(e).lower():
                    messages.error(request, 'This email is already in use. Please use a different email.')
                elif 'mobile' in str(e).lower():
                    messages.error(request, 'This mobile number is already in use. Please use a different mobile number.')
                else:
                    messages.error(request, 'An error occurred while saving your contact info. Please try again.')
                return redirect('offer_detail', offer_id=offer.id)
        else:
            # Redirect to offer detail page to show the form
            if referral_id:
                return redirect('offer_detail_with_referral', offer_id=offer_id, referral_id=referral_id)
            return redirect('offer_detail', offer_id=offer_id)
    else:
        if request.method == 'POST':
            # Validate CAPTCHA for "Grab Now" action
            selected_image = request.POST.get('captcha_image')
            correct_image = request.session.get('captcha_correct')
            if selected_image != correct_image:
                messages.error(request, 'CAPTCHA verification failed. Please try again.')
                return redirect('offer_detail', offer_id=offer.id)

            # Clear CAPTCHA session data
            request.session.pop('captcha_id', None)
            request.session.pop('captcha_correct', None)

            # Increment click_count only for unique clicks within 24 hours
            if referral and not click_exists:
                referral.click_count += 1
                referral.working_state = 'clicked'
                referral.save()
                ReferralClick.objects.create(
                    referral=referral,
                    ip_address=ip_address,
                    session_key=session_key
                )
                logger.info(f"Offer grabbed: referral_id={referral_id}, state=clicked, clicks={referral.click_count}, client_ip={ip_address}")
            else:
                logger.info(f"Offer grabbed without referral or already clicked: offer_id={offer_id}, client_ip={ip_address}")
        else:
            # Do not increment click_count on GET requests (page loads)
            logger.info(f"GET request to grab_offer: offer_id={offer_id}, referral_id={referral_id}, client_ip={ip_address}")
            if referral_id:
                return redirect('offer_detail_with_referral', offer_id=offer_id, referral_id=referral_id)
            return redirect('offer_detail', offer_id=offer_id)

    # Modify redirect URL with referral parameters
    if referral and offer.link:
        if offer.advertiser:
            parsed_url = urlparse(offer.link)
            query_params = parse_qs(parsed_url.query)

            prefix = offer.advertiser.query_param_prefix
            i = 1
            param_name = f"{prefix}{i}"
            while param_name in query_params:
                i += 1
                param_name = f"{prefix}{i}"
            
            query_params[param_name] = [str(referral_id)]
            new_query = urlencode(query_params, doseq=True)

            redirect_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
        else:
            parsed_url = urlparse(offer.link)
            query_params = parse_qs(parsed_url.query)

            i = 1
            param_name = 'aff_sub1'
            if param_name in query_params:
                i += 1
                param_name = f'aff_sub{i}'
            
            query_params[param_name] = [str(referral_id)]
            new_query = urlencode(query_params, doseq=True)

            redirect_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))

    return redirect(redirect_url)

# Email Verification View
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user_profile = user.userprofile
        user_profile.email_verified = True
        user_profile.save()
        messages.success(request, "Your email has been verified successfully!")
        logger.info(f"Email verified for user {user.username}")
    else:
        messages.error(request, "The verification link is invalid or has expired.")
        logger.warning(f"Invalid email verification attempt for uid {uidb64}")

    return redirect('dashboard')

@login_required
def resend_verification_email(request):
    from .utils import send_verification_email
    user = request.user
    user_profile = user.userprofile    
    if user_profile.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        try:
            send_verification_email(user, request)
            messages.success(request, "A new verification email has been sent.")
        except Exception as e:
            print(f"Error sending verification email: {str(e)}")
            logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
            messages.error(request, "Failed to send verification email. Please try again later.")
    return redirect('dashboard')

def send_verification_email(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            return JsonResponse({"status": "error", "message": "Email is required."}, status=400)

        # Generate a random 6-digit code
        verification_code = ''.join(random.choices(string.digits, k=6))

        # Initialize the verification_codes dictionary in the session if it doesn't exist
        if 'verification_codes' not in request.session:
            request.session['verification_codes'] = {}

        # Store the code in the session, keyed by email
        request.session['verification_codes'][email] = {
            'code': verification_code,
            'timestamp': int(time.time()),  # Store the timestamp for expiration
        }
        request.session.modified = True  # Ensure the session is saved

        logger.info(f"Sending verification code {verification_code} to {email}")

        try:
            # Send the email
            send_mail(
                subject="Email Verification Code",
                message=f"Your verification code is: {verification_code}",
                from_email="noreply@yourdomain.com",
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Successfully sent verification code to {email}")
            return JsonResponse({"status": "success", "message": "Verification code sent to your email."})
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return JsonResponse({"status": "error", "message": f"Failed to send email: {str(e)}"}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

def verify_email_code(request):
    if request.method == "POST":
        code = request.POST.get("code")
        email = request.POST.get("email")
        is_signup = request.POST.get("is_signup") == "true"  # Check if this is the signup flow

        if not email or not code:
            return JsonResponse({"status": "error", "message": "Email and code are required."}, status=400)

        # Retrieve the verification codes dictionary from the session
        verification_codes = request.session.get('verification_codes', {})
        stored_data = verification_codes.get(email)

        if not stored_data:
            logger.warning(f"No verification code found for email {email}")
            return JsonResponse({"status": "error", "message": "No verification code found for this email."}, status=400)

        stored_code = stored_data['code']
        timestamp = stored_data['timestamp']
        current_time = int(time.time())

        logger.info(f"Verifying code {code} for {email}, stored code: {stored_code}")

        # Check if the code has expired (e.g., 10 minutes = 600 seconds)
        if current_time - timestamp > 600:
            del verification_codes[email]
            request.session['verification_codes'] = verification_codes
            request.session.modified = True
            logger.warning(f"Verification code expired for {email}")
            return JsonResponse({"status": "error", "message": "Verification code has expired."}, status=400)

        if code == stored_code:
            # Remove the code from the session
            del verification_codes[email]
            request.session['verification_codes'] = verification_codes
            request.session.modified = True

            if is_signup:
                # For signup, just confirm the code is valid; user creation happens later
                logger.info(f"Email {email} verification successful for signup")
                return JsonResponse({"status": "success", "message": "Email verified successfully!"})
            else:
                # For other flows (e.g., offer_detail.html), update the user's email_verified status
                try:
                    user = User.objects.get(email=email)
                    user.userprofile.email_verified = True
                    user.userprofile.save()
                    logger.info(f"Email {email} verified successfully for existing user")
                    return JsonResponse({"status": "success", "message": "Email verified successfully!"})
                except User.DoesNotExist:
                    logger.error(f"User with email {email} does not exist")
                    return JsonResponse({"status": "error", "message": "User with this email does not exist."}, status=400)
        logger.warning(f"Invalid code {code} for {email}, expected {stored_code}")
        return JsonResponse({"status": "error", "message": "Invalid verification code."}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)

class CustomEmailView(EmailView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if 'email' in request.POST and request.POST.get('action') == 'add_email':
            email = request.POST['email']
            email_address = EmailAddress.objects.filter(user=request.user, email=email).first()
            if email_address:
                email_address.verified = False
                email_address.save()
                user_profile = request.user.userprofile
                user_profile.email_verified = False
                user_profile.save()
                send_verification_email(request.user, request)
                messages.info(request, "A verification email has been sent to your new email address.")
        return response

class CustomSignupView(SignupView):
    form_class = CustomSignupForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
@login_required
def retry_mobile_verification(request):
    user = request.user
    try:
        pending = PendingVerification.objects.filter(user=user, is_processed=False).first()
        if not pending:
            messages.info(request, "No pending verifications found.")
            return redirect('dashboard')

        # Attempt to verify the mobile number
        from offers.utils import validate_mobile_number
        is_valid, message = validate_mobile_number(user, pending.mobile_number)
        if is_valid:
            user.userprofile.mobile_verified = True
            user.userprofile.save()
            pending.is_processed = True
            pending.save()
            messages.success(request, "Mobile number verified successfully!")
        else:
            messages.error(request, f"Verification failed: {message}")
    except Exception as e:
        logger.error(f"Error retrying mobile verification for user {user.username}: {str(e)}")
        messages.error(request, "An error occurred while retrying verification. Please try again later.")
    return redirect('dashboard')