# setup.py

from setuptools import setup, find_packages

setup(
    name='ipat_data_watchdog',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'watchdog',
        'tifffile',
        'xmltodict',
        'kadi_apy',
    ],
    entry_points={
        'console_scripts': [
            'device_watchdog=main:main',
        ],
    },
    author='James Fitz',
    author_email='james.fitz@tu-braunschweig.de',
    description='A device watchdog application.',
    url='https://github.com/yourusername/device_watchdog_app',  # Update with your repo URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
