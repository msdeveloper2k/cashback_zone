import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-!#1$p310*!wxsubr!%mak=#^g%0+$v@*mbrwcwdd1s=zn-_&sn'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'localhost:8000',
    '127.0.0.1',
    '192.168.1.17',
]

INSTALLED_APPS = [    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',    
    'tailwind',           
    'django_browser_reload',
    'offers',
    'theme',    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]    

TAILWIND_APP_NAME = 'theme'

# Remove CRISPY_* settings if not using django-crispy-forms
# If using crispy-forms, uncomment the following and add 'crispy_forms' and 'crispy_tailwind' to INSTALLED_APPS
# CRISPY_ALLOWED_TEMPLATE_TYPES = 'tailwind'
# CRISPY_TEMPLATE_TYPE = 'tailwind'

ROOT_URLCONF = 'cashback_zone.urls'


TEMPLATES = [
       {
           'BACKEND': 'django.template.backends.django.DjangoTemplates',
           'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'offers' / 'templates',
            BASE_DIR / 'theme' / 'templates',
            # Removed 'dashboard/templates' since there's no dashboard app
            ],
           'APP_DIRS': True,
           'OPTIONS': {
               'context_processors': [
                   'django.template.context_processors.debug',
                   'django.template.context_processors.request',
                   'django.contrib.auth.context_processors.auth',
                   'django.contrib.messages.context_processors.messages',
               ],
           },
       },
   ]


# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'coolcents2k25@gmail.com'
EMAIL_HOST_PASSWORD = 'uqnb tkkp sobe xwqc'
DEFAULT_FROM_EMAIL = 'coolcents2k25@gmail.com'


# Other settings (ensure these are present for email and session functionality)
DEFAULT_FROM_EMAIL = 'coolcents2k25@gmail.com'  # Replace with your email
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
TIME_ZONE = 'Asia/Kolkata'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'  # You're handling email verification manually
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SIGNUP_REDIRECT_URL = '/'  # Changed to redirect to homepage after signup
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

NUMVERIFY_API_KEY = 'a530364b433775e47da0ea0c160adfc7' # https://numverify.com/documentation#test-credentials
ABSTRACT_API_KEY = 'ac32223c63ff43d697d3596aca424045'  # https://app.abstractapi.com/api/phone-validation/tester


# Free tier limits
NUMVERIFY_FREE_LIMIT = 250  # 250 requests/month
ABSTRACT_FREE_LIMIT = 250  # 250 requests/month

# Google OAuth settings (replace with your actual credentials)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'your-google-client-id',  # Replace with actual Google Client ID
            'secret': 'your-google-client-secret',  # Replace with actual Google Client Secret
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'click_logs.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Static files settings
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files settings
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Removed duplicate definition

# Remove LOCALE_PATHS if not using internationalization
# LOCALE_PATHS = [BASE_DIR / 'locale']

# Tailwind settings for Windows
NPM_BIN_PATH = "C:/Program Files/nodejs/npm.cmd"