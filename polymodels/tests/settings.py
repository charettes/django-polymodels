from __future__ import unicode_literals

from django.conf.global_settings import TEST_RUNNER


SECRET_KEY = 'not-anymore'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'polymodels',
]

if not TEST_RUNNER.endswith('DiscoverRunner'):
    TEST_RUNNER = str('discover_runner.DiscoverRunner')

SILENCED_SYSTEM_CHECKS = ['1_7.W001']
