from django import VERSION as DJANGO_VERSION
from django.contrib.contenttypes.models import ContentType
from django.test.testcases import TestCase

from polymodels.models import BasePolymorphicModel


class TestCase(TestCase):
    DJANGO_GTE_42 = (4, 2) <= DJANGO_VERSION

    def assertQuerysetEqual(self, qs, values, transform=None, ordered=True, msg=None):
        if self.DJANGO_GTE_42:
            super().assertQuerySetEqual(
                qs, values, transform=transform or repr, ordered=ordered, msg=msg
            )
        else:
            super().assertQuerysetEqual(
                qs, values, transform=transform or repr, ordered=ordered, msg=msg
            )

    def tearDown(self):
        ContentType.objects.clear_cache()
        BasePolymorphicModel.subclass_accessors.clear()
