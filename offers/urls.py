from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    path('offer/<int:offer_id>/', views.offer_detail, name='offer_detail'),
    path('offer/<int:offer_id>/details/<int:referral_id>/', views.offer_detail, name='offer_detail_with_referral'),
    path('offer/<int:offer_id>/info/', views.offer_info, name='offer_info'),
    path('offer/<int:offer_id>/confirm-google-form/', views.confirm_google_form_submission, name='confirm_google_form_submission'),
    path('offer/<int:offer_id>/refer/', views.refer, name='refer'),
    path('grab-offer/<int:offer_id>/', views.grab_offer, name='grab_offer'),
    path('grab-offer/<int:offer_id>/<int:referral_id>/', views.grab_offer, name='grab_offer'),
    path('retry-mobile-verification/', views.retry_mobile_verification, name='retry_mobile_verification'),
    path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('postback/', views.postback, name='postback'),
]