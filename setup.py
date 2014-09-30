"""
Primarily jacked from Django's setup.py
"""
import os
import sys

from setuptools import setup, find_packages
from distutils.sysconfig import get_python_lib

if "install" in sys.argv:
    lib_paths = [get_python_lib()]
    if lib_paths[0].startswith("/usr/lib/"):
        # We have to try also with an explicit prefix of /usr/local in order to
        # catch Debian's custom user site-packages directory.
        lib_paths.append(get_python_lib(prefix="/usr/local"))
    for lib_path in lib_paths:
        existing_path = os.path.abspath(os.path.join(lib_path, "gitreload"))

EXCLUDE_FROM_PACKAGES = []

version = __import__('gitreload').VERSION

setup(
    name='gitreload',
    version=version,
    url='https://github.com/mitodl/gitreload',
    author='MITx',
    author_email='mitx-devops@mit.edu',
    description=('Github Web hook consumer for reloading '
                 'courses in edx-platform, or generally '
                 'updating local repositories'),
    license='AGPLv3',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    entry_points={'console_scripts': [
        'gitreload = gitreload.web:run_web',
    ]},
    zip_safe=True,
    requires=('flask', 'gunicorn', 'GitPython', ),
    install_requires=['flask', 'gunicorn', 'GitPython==0.3.2.RC1', ],
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Education',
    ],
)
