
import tarfile
import os

from fabric.api import (put, run, require, env, sudo, cd, open_shell,
                        settings, hide, prompt)

from poputils.fabfiles import common


__all__ = ['init', 'upload_sources', 'compile', 'run_application', 'attach', 'shell']


def init(resetenv=False, link=True):
    """
    Setups the remote node to be able to manage the cloud.
    """

    if resetenv:
        reset()

    common.update_hosts()
    upload_key()
    upload_setup()
    upload_fabfile()

    if link:
        setup_topology()


def shell():
    open_shell()

def upload_key():
    """
    Uploads the private key which fabric uses to connect to the remote host
    to the remote host and sets it has default private key for both the
    current user and the root.
    The permissions are also set to ``rw-------`` for both copies.
    """

    require('key_filename', used_for='uploading to the PAM')
    put(env.key_filename, '.ssh/id_rsa', mode=0600)
    put(env.key_filename, '/root/.ssh/id_rsa', mode=0600, use_sudo=True)
    sudo('chown root:root /root/.ssh/id_rsa')


def upload_setup():
    """
    Uploads the cloud setup XML definition file to the remote host.
    """
    require('cloud_setup', used_for='uploading to the PAM')
    put(env.cloud_setup, 'cloud.xml', mode=0600)


def upload_fabfile():
    fabfile = os.path.join(os.path.dirname(common.__file__), 'remote.py')
    put(fabfile, 'fabfile.py', mode=0600)


def setup_topology():
    run('fab link')


def upload_sources(path):
    """
    Uploads the sources contained in the specified directory to the PAM.
    """

    def tarball(path):
        """
        Returns a filelike object containing the tarball of the all the files
        under the basename of ``path`` contained in a single ``sources``
        directory.
        """
        from StringIO import StringIO

        fh = StringIO()

        oldcwd = os.getcwd()

        srcpath = os.path.realpath(path)
        os.chdir(os.path.dirname(srcpath))

        tar = tarfile.open(fileobj=fh, mode='w|gz')
        tar.add(os.path.basename(srcpath), 'sources')
        tar.close()

        os.chdir(oldcwd)

        fh.seek(0)

        return fh

    run('rm -rf sources')
    put(tarball(path), 'sources.tar.gz')
    run('tar xzf sources.tar.gz')


def compile():
    """
    Compiles the remote application on all the needed hosts, retrieves the
    results and publishes them (also updates the remote obj.map file).
    """
    workflow = [
        'compile_application',
        'find_compilers',
        'compile_objects',
        'collect_objects',
    ]
    run('fab ' + ' '.join(workflow))


def _get_sessions():
    with settings(hide('everything'), warn_only=True):
        sessions = run('screen -ls poprun')
        sessions = sessions.strip().split('\n')[1:-1]
        sessions = [s.strip().split('\t') for s in sessions]
        sessions = [(int(s[0].split('.')[0]), s[1][1:-1]) for s in sessions]

    return dict(sessions)

def _chose_session(sessions):
    for s, date in sessions.iteritems():
        print "   * {0} (started {1})".format(s, date)
    print

    def validate(x):
        if x == '':
            return False

        try:
            if int(x) in sessions:
                return int(x)
            else:
                raise ValueError()
        except:
            raise ValueError("Enter the number corresponding to the session")

    return prompt('Enter a session number:', validate=validate)


def run_application(attached=True):
    """
    Runs the remote application execution session.
    """

    sessions = _get_sessions()

    if sessions:
        if len(sessions) == 1:
            print "There is 1 other pop application running."
        else:
            print "There are {0} other pop applications running."

        print "If you want to start another one press enter;"
        print "If you want to resume a session enter one of the following"
        print "session numbers:"
        print

        session = _chose_session(sessions)

        if session:
            attach(session)
            return

    run('screen -d -m -S poprun fab run', pty=False)

    session = (set(_get_sessions().keys()) - set(sessions.keys())).pop()

    if attached:
        attach(session)


def attach(session=None):
    """
    Attaches to a running remote application session.
    """
    name = '{0}.poprun'.format(session) if session else 'poprun'

    with settings(hide('running', 'warnings'), warn_only=True):
        err = run('screen -q -d -r ' + name).return_code
        if err == 10:
            print "No application sessions running"
        elif err == 12:
            print "Multiple sessions running, chose to which one you want to attach:"
            print

            session = _chose_session(_get_sessions())

            if session:
                attach(session)
                return


def reset():
    upload_fabfile()
    upload_setup()

    run('fab jobmgr:stop')
    run('fab jobmgr:kill')
    run('fab jobmgr:start')

    sudo('rm -f /var/www/objs')
    run('rm -rf sources* fabfile.py* cloud.xml objs')

