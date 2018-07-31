from distutils.core import setup

from setuptools import find_packages

setup(
    name = 'waapi-client',
    packages = find_packages(exclude=['waapi/test']),
    install_requires=[
      'autobahn',
      'six'
    ],
    scripts=[],
    version = '0.1.0',
    description = '',
    author = 'Audiokinetic',
    author_email = 'slongchamps@audiokinetic.ca',
    url = 'https://github.com/audiokinetic/waapi-client-python',
    download_url = 'https://github.com/audiokinetic/waapi-client-python/releases',
    keywords = ['waapi', 'wwise', 'audiokinetic'],
    classifiers = [
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Development Status :: 3 - Alpha'
    ],
)
