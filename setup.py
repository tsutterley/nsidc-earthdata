from setuptools import setup, find_packages

# package description and keywords
description = ('ftp-like program for searching NSIDC databases and '
    'retrieving NASA Operation IceBridge data')
keywords = 'NSIDC Earthdata Operation IceBridge download'
# get long_description from README.rst
with open("README.rst", "r") as fh:
    long_description = fh.read()
long_description_content_type = "text/x-rst"

# get version
with open('version.txt') as fh:
    version = fh.read()

setup(
    name='nsidc-earthdata',
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type=long_description_content_type,
    url='https://github.com/tsutterley/nsidc-earthdata',
    author='Tyler Sutterley',
    author_email='tsutterl@uw.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='NSIDC Earthdata Operation IceBridge download',
    packages=find_packages(),
    install_requires=['lxml','future'],
    scripts=['nsidc_earthdata.py']
)
