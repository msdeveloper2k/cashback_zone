from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Advertiser(models.Model):
    name = models.CharField(max_length=255, unique=True)
    base_url = models.URLField()
    query_param_prefix = models.CharField(max_length=50, default='aff_sub')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Offer(models.Model):
    advertiser = models.ForeignKey(Advertiser, on_delete=models.CASCADE, related_name='offers', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='offers/', blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    reward = models.CharField(max_length=100, blank=True, null=True)
    theme = models.CharField(max_length=50, choices=[
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('green', 'Green'),
        ('purple', 'Purple'),
    ], default='blue')
    is_active = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    requires_google_form = models.BooleanField(default=False)
    google_form_url = models.URLField(blank=True, null=True)
    requires_contact_info = models.BooleanField(default=False)    

    def __str__(self):
        return self.name

class AdBanner(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='ad_banners')
    image = models.ImageField(upload_to='ad_banners/', null=False, blank=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Ad Banner for {self.offer.name} - {self.title or 'Untitled'}"

class TutorialVideo(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='tutorial_videos')
    url = models.URLField()
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Video for {self.offer.name} - {self.title or 'Untitled'}"

class Referral(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    visitor_identifier = models.CharField(max_length=255, null=True, blank=True)
    working_state = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('clicked', 'Clicked'),
        ('converted', 'Converted'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    click_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Referral {self.id} for Offer {self.offer.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_level = models.IntegerField(default=1)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    mobile_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.username}"

class ContactInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='contact_infos')
    referral = models.ForeignKey(Referral, on_delete=models.SET_NULL, null=True, blank=True)
    visitor_identifier = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact Info for {self.offer.name} by {self.user.username if self.user else 'Anonymous'}"

class GoogleFormSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='google_form_submissions')
    visitor_identifier = models.CharField(max_length=255, null=True, blank=True)
    submitted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user', 'offer'), ('visitor_identifier', 'offer'))

    def __str__(self):
        return f"Google Form Submission for {self.offer.name} by {self.user.username if self.user else 'Anonymous'}"

class ReferralClick(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField()
    session_key = models.CharField(max_length=40, blank=True, null=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('referral', 'ip_address')  # Changed to only use referral and ip_address
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['clicked_at']),
        ]
    
class ApiUsage(models.Model):
    api_name = models.CharField(max_length=50)  # e.g., 'numverify', 'abstract'
    request_count = models.PositiveIntegerField(default=0)
    last_reset = models.DateTimeField(default=timezone.now)

    def reset_if_new_month(self):
        now = timezone.now()
        if now.month != self.last_reset.month or now.year != self.last_reset.year:
            self.request_count = 0
            self.last_reset = now
            self.save()

    def increment(self):
        self.reset_if_new_month()
        self.request_count += 1
        self.save()

    def is_limit_exceeded(self, limit):
        self.reset_if_new_month()
        return self.request_count >= limit

    def __str__(self):
        return f"{self.api_name} Usage: {self.request_count}/{self.last_reset}"
    
# Model to cache mobile validation results
class MobileValidationCache(models.Model):
    mobile_number = models.CharField(max_length=15, unique=True)
    is_valid = models.BooleanField()
    validated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mobile_number} - {'Valid' if self.is_valid else 'Invalid'}"

class PendingVerification(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    mobile_number = models.CharField(max_length=15)  # E.g., +919876543210
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Pending Verification for {self.user.username}: {self.mobile_number}"
    
class ApiLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]

    api_name = models.CharField(max_length=50)
    message = models.TextField()
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - {self.api_name} - {self.level}: {self.message}"