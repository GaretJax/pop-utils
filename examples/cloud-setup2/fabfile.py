"""
Fabfile for POP Cloud Deployments
---------------------------------

Autogenerated by pop-cloud-setup on 2011-05-19 17:00:11.821734

Run 'fab --list' from the command line (and in the same directory as this file)
to obtain a list of operations you can execute on your remote cloud setup.

You can then run 'fab -d COMMAND' to obtain more information about a given
command.

For even more information, either run 'fab --help' and/or consult the pop-utils
user manual.
"""



### External dependencies, do not alter the following lines ###################
from fabric.api import env
from poputils.utils.fabric import relative
from poputils.fabfiles.manager import *
run = run_application
del run_application
### End of dependencies import ################################################



### Configuration section #####################################################
# Alter the following lines if you need to adapt this fabfile to your setup   #

env.hosts = ['184.72.108.79']

env.key_filename = relative('key.pem')

env.user = 'ubuntu'

env.cloud_setup = 'cloud.i.xml'

del relative
### Configuration section end #################################################



### Custom workflow commands ##################################################
# Add custom or new commands below by composing existing ones or creating     #
# whole new workflows                                                         #

def runall(sources='sources'):
    """
    Executes the init, upload_sources, compile, link and run commands; in this
    order.
    
    The default value for the sources parameter of the upload_sources command
    is 'sources'.
    """
    init()
    upload_sources(sources)
    compile()
    run()
