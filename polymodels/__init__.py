from __future__ import unicode_literals

from django.utils.version import get_version

VERSION = (1, 4, 0, 'alpha', 0)

__version__ = get_version(VERSION)

default_app_config = 'polymodels.apps.PolymodelsConfig'
