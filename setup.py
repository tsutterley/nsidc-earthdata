from setuptools import setup, find_packages
setup(
    name='nsidc-earthdata',
    version='1.0.1.0',
    description='ftp-like program for searching NSIDC databases and retrieving NASA Operation IceBridge data',
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
    keywords='NSIDC Earthdata IceBridge download',
    packages=find_packages(),
    install_requires=['lxml','future'],
)
