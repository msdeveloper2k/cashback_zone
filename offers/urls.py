from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('offer/<int:offer_id>/submit-conversion-proof/', views.submit_conversion_proof, name='submit_conversion_proof'),
    path('send-verification-email/', views.send_verification_email, name='send_verification_email'),
    path('verify-email-code/', views.verify_email_code, name='verify_email_code'),
    path('postback/', views.postback, name='postback'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)