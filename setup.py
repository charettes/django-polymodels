#!/usr/bin/env python
from setuptools import find_packages, setup

from polymodels import __version__

github_url = 'https://github.com/charettes/django-polymodels'
long_desc = open('README.rst').read()

setup(
    name='django-polymodels',
    version=__version__,
    description='Polymorphic models implementation for django',
    long_description=long_desc,
    url=github_url,
    author='Simon Charette',
    author_email='charette.s@gmail.com',
    install_requires=(
        'Django>=2.2',
    ),
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    license='MIT License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
