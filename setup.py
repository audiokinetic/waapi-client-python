import os
from distutils.core import setup

from setuptools import find_packages

# Dump the README.md file
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')) as f:
    long_description = f.read()

setup(
    name='waapi-client',
    packages=find_packages(exclude=['waapi.test']),
    test_suite='waapi.test',
    install_requires=[
      'autobahn',
      'six'
    ],
    license='Apache License 2.0',
    platforms=['any'],
    scripts=[],
    version='0.1b5',
    description='Wwise Authoring API client.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Audiokinetic',
    author_email='sales@audiokinetic.com',
    maintainer='Samuel Longchamps',
    maintainer_email='slongchamps@audiokinetic.ca',
    url='https://github.com/audiokinetic/waapi-client-python',
    download_url='https://github.com/audiokinetic/waapi-client-python/releases',
    keywords=['waapi', 'wwise', 'audiokinetic'],
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 4 - Beta'
    ],
)
