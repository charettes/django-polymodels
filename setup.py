#!/usr/bin/env python
from setuptools import setup, find_packages

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
        'Django>=1.8',
    ),
    packages=find_packages(exclude=['tests', 'tests.*']),
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
