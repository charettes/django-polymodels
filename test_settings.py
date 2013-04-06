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

try:
    import django_coverage
except ImportError:
    pass
else:
    INSTALLED_APPS.append('django_coverage')
    COVERAGE_MODULE_EXCLUDES = [
        'polymodels.__init__',
        'polymodels.utils',
        'polymodels.tests',
    ]