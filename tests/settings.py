from __future__ import unicode_literals

SECRET_KEY = 'not-anymore'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'polymodels',
    'tests',
]

SILENCED_SYSTEM_CHECKS = ['1_7.W001']
