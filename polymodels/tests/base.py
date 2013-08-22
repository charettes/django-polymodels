from __future__ import unicode_literals

import re

import django
from django.contrib.contenttypes.models import ContentType
from django.test.testcases import TestCase


class TestCase(TestCase):
    def tearDown(self):
        ContentType.objects.clear_cache()

    # TODO: Remove when support for django 1.3 is dropped
    if django.VERSION < (1, 4):
        def assertRaisesMessage(self, expected_exception, expected_message,
                                callable_obj=None, *args, **kwargs):
            return self.assertRaisesRegexp(expected_exception,
                    re.escape(expected_message), callable_obj, *args, **kwargs)
