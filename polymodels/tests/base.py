from __future__ import unicode_literals
import re

import django
from django.test.testcases import TestCase


# TODO: Remove when support for django 1.3 is dropped
if django.VERSION < (1, 4):
    class TestCase(TestCase):
        def assertRaisesMessage(self, expected_exception, expected_message,
                                callable_obj=None, *args, **kwargs):
            return self.assertRaisesRegexp(expected_exception,
                    re.escape(expected_message), callable_obj, *args, **kwargs)
