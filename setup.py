#!/usr/bin/env python
from setuptools import setup, find_packages

from polymodels import __version__


github_url = 'https://github.com/charettes/django-polymodels'
long_desc = open('README.rst').read()

setup(
    name='django-polymodels',
    version='.'.join(str(v) for v in __version__),
    description='Polymorphic models implementation for django',
    long_description=long_desc,
    url=github_url,
    author='Simon Charette',
    author_email='charette.s@gmail.com',
    install_requires=(
        'django>=1.3,<=1.5',
    ),
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
