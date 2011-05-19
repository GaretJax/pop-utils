from __future__ import absolute_import

import os

from fabric.api import env

def relative(path):
    return os.path.join(os.path.dirname(env.real_fabfile), path)