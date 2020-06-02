"""
Python setup file for the gitreload flask app.
"""
# pylint: disable=import-error, invalid-name

import os
import sys
from distutils.sysconfig import get_python_lib

from setuptools import setup, find_packages


if "install" in sys.argv:
    lib_paths = [get_python_lib()]
    if lib_paths[0].startswith("/usr/lib/"):
        # We have to try also with an explicit prefix of /usr/local in order to
        # catch Debian's custom user site-packages directory.
        lib_paths.append(get_python_lib(prefix="/usr/local"))
    for lib_path in lib_paths:
        existing_path = os.path.abspath(os.path.join(lib_path, "gitreload"))

version = __import__('gitreload').VERSION

install_requires = ['flask==1.*,>=1.1.2',
                    'gitpython==3.*,>=3.1.3',
                    'gunicorn==20.*,>=20.0.4']

setup(
    name='gitreload',
    version=version,
    url='https://github.com/mitodl/gitreload',
    author='MIT Office of Digital Learning',
    author_email='mitx-devops@mit.edu',
    description=('Github Web hook consumer for reloading '
                 'courses in edx-platform, or generally '
                 'updating local repositories'),
    license='AGPLv3',
    packages=find_packages(),
    include_package_data=True,
    entry_points={'console_scripts': [
        'gitreload = gitreload.web:run_web',
    ]},
    zip_safe=True,
    install_requires=install_requires,
    data_files=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: GNU Affero '
         'General Public License v3 or later (AGPLv3+)'),
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Education',
    ],
)
