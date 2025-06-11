from django import template

register = template.Library()

@register.filter
def add_aff_sub1(url, referral_id):
    """
    Append aff_sub1 query parameter to a URL.
    If the URL already has query parameters, use '&', otherwise use '?'.
    """
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}aff_sub1={referral_id}"