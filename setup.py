#!/usr/bin/env python
from setuptools import find_packages, setup

from polymodels import __version__

github_url = "https://github.com/charettes/django-polymodels"
long_desc = open("README.rst").read()

setup(
    name="django-polymodels",
    version=__version__,
    description="Polymorphic models implementation for django",
    long_description=long_desc,
    long_description_content_type="text/x-rst",
    url=github_url,
    author="Simon Charette",
    author_email="charette.s@gmail.com",
    install_requires=("Django>=4.2",),
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    license="MIT License",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Django :: 5.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
