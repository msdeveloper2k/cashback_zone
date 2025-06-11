from django.contrib import admin
from .models import Offer, AdBanner, TutorialVideo, Referral, UserProfile, Advertiser

# Inline for TutorialVideo
class TutorialVideoInline(admin.TabularInline):
    model = TutorialVideo
    extra = 1
    fields = ('title', 'description', 'url')

# Inline for AdBanner
class AdBannerInline(admin.TabularInline):
    model = AdBanner
    extra = 1
    fields = ('title', 'description', 'image')

@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'query_param_prefix', 'created_at', 'updated_at')
    search_fields = ('name', 'base_url')
    list_filter = ('created_at',)

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'advertiser', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'theme', 'advertiser')
    search_fields = ('name', 'description')
    fields = (
        'advertiser', 'name', 'description', 'price', 'theme', 'is_active', 'terms', 'link', 'logo', 'image',
        'requires_google_form', 'google_form_url', 'requires_contact_info'
    )
    inlines = [TutorialVideoInline, AdBannerInline]

@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    list_display = ('offer', 'title', 'image')
    list_filter = ('offer',)
    search_fields = ('title', 'description')

@admin.register(TutorialVideo)
class TutorialVideoAdmin(admin.ModelAdmin):
    list_display = ('offer', 'title', 'url')
    list_filter = ('offer',)
    search_fields = ('title', 'description', 'url')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('id', 'offer', 'user', 'working_state', 'click_count', 'created_at')
    list_filter = ('working_state', 'offer')
    search_fields = ('user__username', 'offer__name')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_level')
    search_fields = ('user__username',)