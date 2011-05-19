"""
Common fabric utilities used for different tasks such as manager setup, child
management, AMI creation and so on.
"""


from fabric.api import put, get, sudo, run
from cStringIO import StringIO


__all__ = ['use_vpc_sources', 'update_hosts']


def use_vpc_sources():
    """
    Updates the APT sources for instances deployed as part of a VPC.
    VPC instances cannot connect to other AWS instances running outside of the
    cloud using private IP addressing anf as the URL of the internal AWS mirror
    resolves to a private IP address, it can't be used.
    """

    SOURCES = """
    deb http://archive.ubuntu.com/ubuntu/ lucid main universe
    deb-src http://archive.ubuntu.com/ubuntu/ lucid main universe
    deb http://archive.ubuntu.com/ubuntu/ lucid-updates main universe
    deb-src http://archive.ubuntu.com/ubuntu/ lucid-updates main universe
    deb http://security.ubuntu.com/ubuntu lucid-security main universe
    deb-src http://security.ubuntu.com/ubuntu lucid-security main universe
    """

    put(StringIO(SOURCES), '/etc/apt/sources.list', use_sudo=True, mode=0644)
    sudo('chown root:root /etc/apt/sources.list')
    sudo('apt-get -y update')


def update_hosts():
    """
    Updates the /etc/hosts file to include a loopback entry for the currently
    defined hostname. This prevents the sudo command to print warnings about
    unresolved hosts for the local machine.
    """

    hosts = StringIO()
    hostname = run('hostname')
    get('/etc/hosts', hosts)

    hosts = StringIO(hosts.getvalue().replace(
        '127.0.0.1 localhost',
        '127.0.0.1 localhost\n127.0.0.1 {0}'.format(hostname)
    ))
    put(hosts, '/etc/hosts', use_sudo=True, mode=644)
    sudo('chown root:root /etc/hosts')

