import os
from setuptools import setup, find_packages


NAME = 'pop-utils'

VERSION = '0.1'

DESCRIPTION = """
Collection of utilities to optimize the deployment and management of a POP-C++
or POP-Java based setup with a special focus on cloud deployments and Amazon
Web Services.
"""

URL = 'https://github.com/GaretJax/pop-utils'

LICENSE = 'MIT'

AUTHOR = 'Jonathan Stoppani', 'jonathan.stoppani@gmail.com'

KEYWORDS = 'pop cloud utils aws'

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: Education',
    'Intended Audience :: Information Technology',
    'Intended Audience :: Science/Research',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX',
    'Topic :: System :: Distributed Computing',
    'Topic :: Utilities',
]


def read(fname):
    """
    Utility function to read the README file.
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_files(*bases):
    """
    Utility function to list all files in a data directory.
    """
    for base in bases:
        base = os.path.join(os.path.dirname(__file__), *base.split('.'))
        
        rem = len(os.path.dirname(base)) + 1
        
        for root, dirs, files in os.walk(base):
            for name in files:
                yield os.path.join(root, name)[rem:]


def requirements(fname):
    """
    Utility function to create a list of requirements from the output of the
    pip freeze command saved in a text file.
    """
    packages = read(fname).split('\n')
    packages = (p.strip() for p in packages)
    packages = (p for p in packages if p and not p.startswith('#'))
    return list(packages)


setup(
    name=NAME,
    version=VERSION,
    description=' '.join(DESCRIPTION.strip().splitlines()),
    long_description=read('README.md'),
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    author=AUTHOR[0],
    author_email=AUTHOR[1],
    url=URL,
    license=LICENSE,
    packages=find_packages(),
    package_data = {
        'poputils': get_files('poputils.schemata')
    },
    install_requires=requirements('requirements.txt'),
    entry_points=read('entry-points.ini'),
)
