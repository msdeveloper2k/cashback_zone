from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Offer, Referral, UserProfile
from django.utils.dateparse import parse_datetime
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from .utils import send_verification_email
from allauth.account.models import EmailAddress
from allauth.account.views import EmailView

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
        return redirect('offer_details', offer_id=offer_id)

def offer_details(request, offer_id, reffer_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    referral_message = None

    profile_info = None
    profile_level = None
    offer_referral = None
    referral_url = None
    email_not_verified = False

    if request.user.is_authenticated:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not user_profile.email_verified:
            email_not_verified = True
            messages.warning(request, "Please verify your email address to access all features.")

        referrals = Referral.objects.filter(user=request.user)
        user_profile.profile_level = max(1, len(referrals) // 5 + 1)
        user_profile.save()

        profile_info = {
            'username': request.user.username,
            'email': request.user.email,
            'joined': request.user.date_joined,
        }
        profile_level = user_profile.profile_level
        offer_referral = Referral.objects.filter(user=request.user, offer=offer).first()
        if not offer_referral and user_profile.email_verified:
            offer_referral = Referral.objects.create(
                user=request.user,
                offer=offer,
                working_state='pending'
            )
        if offer_referral:
            referral_url = request.build_absolute_uri(
                reverse('offer_details_with_referral', kwargs={'reffer_id': offer_referral.id, 'offer_id': offer.id})
            )

    if reffer_id:
        try:
            referral = Referral.objects.get(id=reffer_id)
            referral.working_state = 'clicked'
            referral.click_count += 1
            referral.save()
            print(f"Postback triggered: referral_id={reffer_id}, state=clicked, clicks={referral.click_count}, client_ip={request.META.get('REMOTE_ADDR')}")
        except Referral.DoesNotExist:
            print(f"Referral with id {reffer_id} not found, client_ip={request.META.get('REMOTE_ADDR')}")

    if request.method == 'POST':
        if request.user.is_authenticated:
            if not user_profile.email_verified:
                messages.error(request, "You must verify your email before referring an offer.")
            else:
                existing_referral = Referral.objects.filter(user=request.user, offer=offer).first()
                if existing_referral:
                    referral_message = f"You have already referred this offer! Referral ID: {existing_referral.id}"
                else:
                    referral = Referral.objects.create(
                        user=request.user,
                        offer=offer,
                        working_state='pending'
                    )
                    referral_message = f'Referral submitted successfully! Referral ID: {referral.id}'
        else:
            if not request.session.session_key:
                request.session.create()
            visitor_id = request.session.session_key
            existing_referral = Referral.objects.filter(visitor_identifier=visitor_id, offer=offer).first()
            if existing_referral:
                referral_message = f"You have already referred this offer! Referral ID: {existing_referral.id}"
            else:
                referral = Referral.objects.create(
                    visitor_identifier=visitor_id,
                    offer=offer,
                    working_state='pending'
                )
                referral_message = f'Referral submitted successfully! Referral ID: {referral.id}'

    context = {
        'offer': offer,
        'referral_message': referral_message,
        'profile_info': profile_info,
        'profile_level': profile_level,
        'offer_referral': offer_referral,
        'referral_url': referral_url,
        'email_not_verified': email_not_verified,
    }
    return render(request, 'offer_details.html', context)

@csrf_exempt
def postback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            referral_id = data.get('referral_id')
            state = data.get('state')

            if not referral_id or not state:
                return JsonResponse({'status': 'error', 'message': 'Missing referral_id or state'}, status=400)

            referral = get_object_or_404(Referral, id=referral_id)
            if state in ['clicked', 'converted', 'failed']:
                referral.working_state = state
                referral.save()
                return JsonResponse({'status': 'success', 'message': f'Referral state updated to {state}'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid state'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return HttpResponse(status=405)

@login_required
def user_dashboard(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    referrals = Referral.objects.filter(user=request.user)
    user_profile.profile_level = max(1, len(referrals) // 5 + 1)
    user_profile.save()

    profile_info = {
        'username': request.user.username,
        'email': request.user.email,
        'joined': request.user.date_joined,
    }

    filter_offer = request.GET.get('offer', '')
    filter_referral_id = request.GET.get('referral_id', '')
    filter_date_start = request.GET.get('date_start', '')
    filter_date_end = request.GET.get('date_end', '')

    filtered_referrals = referrals
    if filter_offer:
        filtered_referrals = filtered_referrals.filter(offer__name__icontains=filter_offer)
    if filter_referral_id:
        filtered_referrals = filtered_referrals.filter(id=filter_referral_id)
    if filter_date_start:
        start_date = parse_datetime(filter_date_start)
        if start_date:
            filtered_referrals = filtered_referrals.filter(created_at__gte=start_date)
    if filter_date_end:
        end_date = parse_datetime(filter_date_end)
        if end_date:
            filtered_referrals = filtered_referrals.filter(created_at__lte=end_date)

    context = {
        'profile_info': profile_info,
        'referrals': filtered_referrals,
        'profile_level': user_profile.profile_level,
        'filter_offer': filter_offer,
        'filter_referral_id': filter_referral_id,
        'filter_date_start': filter_date_start,
        'filter_date_end': filter_date_end,
    }
    return render(request, 'dashboard.html', context)

def grab_offer(request, offer_id, referral_id=None):
    offer = get_object_or_404(Offer, id=offer_id)
    redirect_url = offer.link

    if referral_id:
        try:
            referral = Referral.objects.get(id=referral_id)
            if request.method == 'POST' and offer.requires_contact_info:
                name = request.POST.get('name')
                email = request.POST.get('email')
                mobile = request.POST.get('mobile')
                print(f"Contact info submitted: name={name}, email={email}, mobile={mobile}, offer_id={offer_id}, referral_id={referral_id}")
            referral.working_state = 'converted'
            referral.click_count += 1
            referral.save()
            print(f"Offer grabbed: referral_id={referral_id}, state=converted, clicks={referral.click_count}, client_ip={request.META.get('REMOTE_ADDR')}")

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
                while param_name in query_params:
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
        except Referral.DoesNotExist:
            print(f"Referral with id {referral_id} not found, client_ip={request.META.get('REMOTE_ADDR')}")
    else:
        print(f"Offer grabbed without referral: offer_id={offer_id}, client_ip={request.META.get('REMOTE_ADDR')}")

    return redirect(redirect_url)

def verify_email(request, token):
    try:
        user_profile = UserProfile.objects.get(email_verification_token=token)
        user_profile.email_verified = True
        user_profile.email_verification_token = None
        user_profile.save()
        messages.success(request, "Your email has been verified successfully!")
    except UserProfile.DoesNotExist:
        messages.error(request, "Invalid or expired verification link.")
    
    return redirect('index')

@login_required
def resend_verification_email(request):
    user = request.user
    user_profile = user.userprofile
    if user_profile.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        send_verification_email(user, request)
        messages.success(request, "A new verification email has been sent to your email address.")
    return redirect('offer_details', offer_id=request.GET.get('offer_id', 1))

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