from django.urls import path, include
from offers import views

urlpatterns = [
    path('', views.index, name='index'),
    path('offer/<int:offer_id>/info/', views.offer_info, name='offer_info'),
    path('offer/<int:offer_id>/details/', views.offer_details, name='offer_details'),
    path('offer/<int:offer_id>/details/<int:reffer_id>/', views.offer_details, name='offer_details_with_referral'),
    path('offer/<int:offer_id>/refer/', views.refer, name='refer'),
    path('grab_offer/<int:offer_id>/<int:referral_id>/', views.grab_offer, name='grab_offer'),
    path('grab_offer/<int:offer_id>/', views.grab_offer, name='grab_offer'),
    path('dashboard/', views.user_dashboard, name='dashboard'),
    path('postback/', views.postback, name='postback'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),
    path('accounts/email/', views.CustomEmailView.as_view(), name='account_email'),
    path('accounts/', include('allauth.urls')),
]