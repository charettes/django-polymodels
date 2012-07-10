#!/usr/bin/env python
import argparse
import os
import sys

from django.conf import settings


def main(verbosity, failfast, test_labels):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'runtests'
    defaults = dict(
        SECRET_KEY='secret',
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=(
            'django.contrib.contenttypes',
            'polymodels',
        )
    )
    settings.configure(**defaults)
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=verbosity, interactive=False, failfast=failfast)
    failures = test_runner.run_tests(test_labels)
    sys.exit(failures)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--failfast', action='store_true', default=False,
                        dest='failfast')
    parser.add_argument('--verbosity', default=1)
    parser.add_argument('test_labels', nargs='*', default=['polymodels'])
    args = parser.parse_args()
    main(args.verbosity, args.failfast, args.test_labels)
