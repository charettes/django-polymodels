from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.test.testcases import TestCase

from polymodels.models import BasePolymorphicModel


class TestCase(TestCase):
    def tearDown(self):
        ContentType.objects.clear_cache()
        BasePolymorphicModel.subclass_accessors.clear()
