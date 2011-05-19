import os

from lxml import etree

from fabric.api import (put, sudo, require, env, \
                        abort, settings, run, hide, \
                        roles, runs_once, cd, get, \
                        local, lcd, prompt)

def workers():
    """
    Uploads the cloud setup XML definition file to the remote host.
    """
    require('cloud_config', used_for='finding the workers addresses')
    return env.cloud_config.xpath('/cloud/setup/machine[@ip!=/cloud/@manager]/@ip')

def manager():
    """
    Uploads the cloud setup XML definition file to the remote host.
    """
    require('cloud_config', used_for='finding the manager address')
    return env.cloud_config.xpath('/cloud/@manager')

env.cloud_config = etree.parse('cloud.xml')

env.roledefs = {
    'workers': workers(),
    'manager': manager(),
}


@roles('workers')
def proxy(cmd):
    with settings(warn_only=True):
        run(cmd)


@roles('workers', 'manager')
def jobmgr(cmd):
    assert cmd in set(('start', 'stop', 'kill', 'restart'))
    sudo('SXXpopc {0}'.format(cmd), pty=True)


@runs_once
def run():
    with lcd('sources'):
        local('make run')
    
    try:
        print "-" * int(run('echo $COLUMNS'))
    except:
        print "-" * 80
    print
    prompt("POP application exited, press enter to continue... ")


@runs_once
def link():
    require('cloud_config', used_for='retrieving the topology configuration')
    try:
        preset = env.cloud_config.xpath('/cloud/topology/@preset')[0]
        print
    except IndexError:
        print "No presets defined"
    else:
        if preset == 'complete':
            ips = env.cloud_config.xpath('/cloud/setup/machine/@ip')
            ips = ['socket://{0}:2711'.format(ip) for ip in ips]
            ips = ' '.join(ips)
            local('pop-link {0}'.format(ips))
        else:
            abort("Topology preset '{0}' not yet supported.".format(preset))

    # Setting up additional links
    for link in env.cloud_config.xpath('/cloud/topology/link'):
        print
        local('pop-link socket://{0}:2711 socket://{1}:2711'.format(*link.attrib.values()))


def find_compilers():
    # Get all platforms
    compiler_hosts = {}

    for h in env.roledefs['workers'] + env.roledefs['manager']:
        with settings(
            hide('everything'),
            host_string='{0}@{1}'.format(env.user, h),
        ):
            platform = run('echo $(uname -m)-$(uname -s)')
            compiler_hosts[platform] = h

    print "The following machines were selected for compilation:"
    for compiler in compiler_hosts.iteritems():
        print " * Platform: {0}; Compilation on: {1}".format(*compiler)

    env.roledefs['compilers'] = compiler_hosts.values()
    env.objs = []


@roles('manager')
def compile_application():
    with lcd('sources'):
        local('make application')


@roles('compilers')
def compile_objects():
    put('sources.tar.gz', 'sources.tar.gz')
    run('tar xzf sources.tar.gz')

    with cd('sources'):
        run('make objects')
        for obj in run('cat obj.map').splitlines():
            env.objs.append((env.host,) + tuple(obj.split(' ', 2)))

    run('rm sources.tar.gz')


@runs_once
def collect_objects():
    def unique_objects():
        objs = {}
        for host, name, platform, path in env.objs:
            objs[name, platform] = host, path
        return objs

    def publish():
        print "Publishing objects"
        with hide('everything'):
            local('mv objs/obj.map sources/obj.map')
            home = local('echo $HOME', capture=True)
            local('sudo ln -s {0}/objs /var/www/objs'.format(home))

    def retrieve(objs, url):
        with open('objs/obj.map', 'w') as fh:
            for (name, platform), (host, path) in objs.iteritems():
                print "Retrieving '{0}.obj' from {1} for 'platform {2}'".format(
                    name, host, platform)

                with settings(
                    hide('everything'),
                    host_string='{0}@{1}'.format(env.user, host)
                ):
                    local('mkdir -p objs/{0}'.format(platform))
                    lpath = 'objs/{0}/{1}'.format(platform, os.path.basename(path))
                    get(path, lpath)
                    ourl = url.format(platform=platform, obj=os.path.basename(path))

                    fh.write(' '.join((name, platform, ourl)) + "\n")
                    run('rm -rf sources')

    url = 'http://{0}/objs/{{platform}}/{{obj}}'.format(env.roledefs['manager'][0])

    with hide('everything'):
        local('rm -rf objs ; mkdir objs')

    retrieve(unique_objects(), url)

    publish()
















