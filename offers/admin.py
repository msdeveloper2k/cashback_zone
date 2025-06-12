from django.contrib import admin
from .models import Advertiser, ApiLog, MobileValidationCache, Offer, AdBanner, PendingVerification, TutorialVideo, Referral, UserProfile, ContactInfo, GoogleFormSubmission

# Inline for AdBanner to be displayed in Offer admin
class AdBannerInline(admin.TabularInline):
    model = AdBanner
    extra = 1
    fields = ('title', 'description', 'image')
    readonly_fields = ('title', 'description', 'image')

# Inline for TutorialVideo to be displayed in Offer admin
class TutorialVideoInline(admin.TabularInline):
    model = TutorialVideo
    extra = 1
    fields = ('title', 'description', 'url')
    readonly_fields = ('title', 'description', 'url')

# Inline for ContactInfo to be displayed in Offer admin
class ContactInfoInline(admin.TabularInline):
    model = ContactInfo
    extra = 0
    fields = ('user', 'visitor_identifier', 'referral', 'name', 'email', 'mobile', 'created_at')
    readonly_fields = ('user', 'visitor_identifier', 'referral', 'name', 'email', 'mobile', 'created_at')
    can_delete = False

# Inline for GoogleFormSubmission to be displayed in Offer admin
class GoogleFormSubmissionInline(admin.TabularInline):
    model = GoogleFormSubmission
    extra = 0
    fields = ('user', 'visitor_identifier', 'submitted', 'created_at')
    readonly_fields = ('user', 'visitor_identifier', 'submitted', 'created_at')
    can_delete = False

@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'query_param_prefix', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'base_url')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'advertiser', 'price', 'is_active', 'requires_contact_info', 'created_at', 'updated_at')
    list_filter = ('is_active', 'theme', 'requires_google_form', 'requires_contact_info', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'advertiser__name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [AdBannerInline, TutorialVideoInline, ContactInfoInline, GoogleFormSubmissionInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'advertiser', 'price', 'image', 'logo', 'link')
        }),
        ('Details', {
            'fields': ('description', 'terms', 'theme', 'is_active')
        }),
        ('Requirements', {
            'fields': ('requires_google_form', 'google_form_url', 'requires_contact_info')
        }),
    )

@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'offer', 'image', 'description')
    list_filter = ('offer__name',)
    search_fields = ('title', 'description', 'offer__name')
    ordering = ('offer__name',)

@admin.register(TutorialVideo)
class TutorialVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'offer', 'url', 'description')
    list_filter = ('offer__name',)
    search_fields = ('title', 'description', 'offer__name', 'url')
    ordering = ('offer__name',)

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'offer', 'visitor_identifier', 'working_state', 'click_count', 'created_at', 'updated_at')
    list_filter = ('working_state', 'created_at', 'updated_at')
    search_fields = ('user__username', 'offer__name', 'visitor_identifier')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_level', 'email_verified', 'mobile_verified')
    list_filter = ('email_verified', 'mobile_verified', 'profile_level')
    search_fields = ('user__username', 'user__email')
    ordering = ('user__username',)

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'visitor_identifier', 'offer', 'referral', 'name', 'email', 'mobile', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'mobile', 'user__username', 'offer__name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(GoogleFormSubmission)
class GoogleFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'offer', 'visitor_identifier', 'submitted', 'created_at')
    list_filter = ('submitted', 'created_at')
    search_fields = ('user__username', 'offer__name', 'visitor_identifier')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(PendingVerification)
class PendingVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'mobile_number', 'created_at', 'is_processed')
    list_filter = ('is_processed', 'created_at')
    search_fields = ('user__username', 'mobile_number')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    raw_id_fields = ('user',)

    def mark_as_processed(self, request, queryset):
        queryset.update(is_processed=True)
        self.message_user(request, "Selected verifications have been marked as processed.")
    mark_as_processed.short_description = "Mark as processed"

    actions = [mark_as_processed]

@admin.register(ApiLog)
class ApiLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'api_name', 'level', 'message')
    list_filter = ('api_name', 'level', 'timestamp')
    search_fields = ('message',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)


@admin.register(MobileValidationCache)
class MobileValidationCacheAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'is_valid', 'validated_at')
    list_filter = ('is_valid', 'validated_at')
    search_fields = ('mobile_number',)
    date_hierarchy = 'validated_at'
    ordering = ('-validated_at',)