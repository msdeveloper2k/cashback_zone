from django.db import models
from django.contrib.auth.models import User

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
    email_verified = models.BooleanField(default=False)  # New field for email verification
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)  # Store token for verification

    def __str__(self):
        return f"Profile of {self.user.username}"