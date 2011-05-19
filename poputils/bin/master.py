#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A utility to create new POP-C++/POP-Java EBS-backed machine image to be
deployed on the cloud.
"""

import argparse
import os
import sys
import stat
import random
import string
import threading
import socket
import time

from lxml import etree

from boto import ec2, iam

from fabric.api import settings, sudo, put, lcd, hide, open_shell, show
from fabric.contrib.console import confirm

from poputils import conf
from poputils.fabfiles import common as fab
from poputils.utils import shell


VERSION = '0.1b'

DESCRIPTION = """
Creates a new POP-C++/POP-Java EBS-Backed machine image to deploy POP
applications onto it.
"""

DEFAULT_REGION = 'us-east-1'
"""
Default region on which the AMI shall be created if no region is provided in
the XML file. Possible values are:

 * eu-west-1
 * us-east-1
 * ap-northeast-1
 * us-west-1
 * ap-southeast-1

"""

TYPES = {
    'x86_64': 'm1.large',
    'i386': 'c1.medium',
}

# Login user for the POP application manager; has for the KEY_FILENAME setting,
# this has also to eventually be refactored in order for the user to be able
# to specify it.
USER = 'ubuntu'


def random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def remote_machine(user, address, key_filename, debug):

    display = show('everything') if debug else hide('everything')

    return settings(
        display,
        host_string='{0}@{1}'.format(user, address),
        key_filename=key_filename,
        disable_known_hosts=True,
    )


def upload_files(base, files, dest):
    base = os.path.realpath(base)

    sudo('mkdir -p {0}'.format(dest))

    with lcd(base):
        for f in files:
            real = os.path.join(base, f)

            if len(os.path.commonprefix((real, base))) < len(base):
                raise ValueError("Insecure path detected: {0}".format(f))

            remote = os.path.dirname(f)

            if remote:
                directory = os.path.join(dest, remote)
                sudo('mkdir -p {0}'.format(directory))

            print "  └ Uploading '{0}'".format(f),
            shell.wait(Upload(real, os.path.join(dest, f)), 'uploaded', interval=.8)



class Upload(threading.Thread):
    def __init__(self, src, dst):
        super(Upload, self).__init__()
        self.src = src
        self.dst = dst
        self.state = 'uploading'
        self.start()

    def run(self):
        try:
            put(self.src, self.dst, use_sudo=True)
        except:
            self.state = 'failed'
        else:
            self.state = 'uploaded'

    def update(self):
        return self


class Manifest(threading.Thread):
    def __init__(self, manifest, debug):
        super(Manifest, self).__init__()
        self.manifest = manifest
        self.debug = debug
        self.state = 'applying'
        self.start()

    def run(self):
        try:
            cmd = 'puppet {0}'.format(os.path.join('/var/manifests', self.manifest))

            if self.debug:
                cmd += ' --verbose --debug'
            sudo(cmd)
        except SystemExit as e:
            if e.code:
                print "Remote command failed"
                self.state = 'failed'
                raise
        self.state = 'applied'

    def update(self):
        return self


class ConnectionAttempt(threading.Thread):
    def __init__(self, host, port):
        super(ConnectionAttempt, self).__init__()
        self.host = host
        self.port = port
        self.state = 'connecting'
        self.start()

    def run(self):
        while True:
            try:
                socket.create_connection((self.host, self.port), 10)
            except socket.error:
                # Either timed out or the connection was refused
                time.sleep(.5)
            else:
                break

        self.state = 'connected'

    def update(self):
        return self


def master(args):
    """
    Main entry point for the master utility.
    """

    start = time.time()

    with shell.Step(1):
        print "Cloud setup validation:"

        # Load master configuration
        print "* Parsing the master XML definition file"
        config = etree.parse(args.setup)

        # Validate the configuration file
        print "* Validating the master XML definition against the XML schema"
        conf.schema('master-image').assertValid(config)

        master = config.getroot().attrib
        manifests = config.xpath('/master/apply/@manifest')
        uploads = config.xpath('/master/upload/@asset')

    # Instantiate connections
    with shell.Step(2):
        print "Instantiation of the cloud manager connection:"
        print "* Choosing region"
        try:
            region = master['region']
        except KeyError:
            region = DEFAULT_REGION
        print "  └ Selected region '{0}'".format(region)

        print "* Connecting to the EC2 manager"
        c = ec2.connect_to_region(
            aws_access_key_id=args.access_key_id,
            aws_secret_access_key=args.secret_key,
            region_name=region,
        )

    with shell.Step(3):
        print "Virtual setup initialization:"

        print "* Checking for duplicate image names"
        try:
            image = c.get_all_images(filters={'name': master['name']})[0]
        except IndexError:
            print "  └ Name '{0}' not used yet".format(master['name'])
        else:
            print "  └ Name '{0}' already used".format(master['name'])
            print "  └ Checking for different user"

            iam_c = iam.IAMConnection(
                aws_access_key_id=args.access_key_id,
                aws_secret_access_key=args.secret_key,
            )

            uid = iam_c.get_user()['GetUserResponse']['GetUserResult']['User']['UserId']

            if image.ownerId == uid:
                if not args.force:
                    raise ValueError("The name '{0}' is already taken by the " \
                                     "image '{1}'.".format(master['name'], image.id))
                else:
                    print "  └ Same user but --force flag set, deregistering image"
                    image.deregister()
                    print
                    print shell.hilite("Note that only the AMI was deregistered, " \
                        "the relative snapshot was left in place. Remove it " \
                        "manually if desired.", shell.MAGENTA)
                    print

        print "* Creating temporary security group"
        group = c.create_security_group(
            'pop-' + random_string(16),
            'Temporary security group for POP master image creation'
        )
        print "  └ New security group named '{0.name}'".format(group)
        print "  └ Authorizing external SSH access"
        group.authorize('tcp', 22, 22, "0.0.0.0/0")
        #group.authorize('tcp', 80, 80, "0.0.0.0/0")

        print "* Creating key pair"
        key = c.create_key_pair('pop-' + random_string(16))
        print "  └ New key pair named '{0.name}'".format(key)

        key_filename = 'pop-master-pk-' + random_string(8) + '.pem'
        with open(key_filename, 'w') as fh:
            fh.write(key.material)
        os.chmod(key_filename, stat.S_IRUSR | stat.S_IWUSR)
        print "  └ Private key written to '{0}'".format(key_filename)

        print "* Getting base image"
        image = c.get_image(master['base'])

        print "* Launching new instance"
        res = image.run(
            key_name=key.name,
            security_groups=[group],
            instance_type=TYPES[image.architecture],
        )
        print "  └ New reservation with ID '{0}'".format(res.id)
        instance = res.instances[0]

        print "* Waiting for machine to boot",
        instance = shell.wait(instance, 'running', interval=.5)
        address = instance.dns_name
        print shell.nowrap("  └ Public address is '{0}'".format(address))

        print "* Waiting for instance to come online",
        shell.wait(ConnectionAttempt(address, 22), 'connected', interval=.8)

        print
        print "Instance online; you can manually connect using this command:\n"

        print shell.nowrap(shell.hilite(
            "ssh -i {0} {1}@{2}".format(key_filename, USER, address),
            shell.MAGENTA
        ))

        if args.clean:
            print
            print "Note that the machine will be available only until the master " \
                  "image creation process successfully completes. If an error " \
                  "happens before completion, the availability of the instance " \
                  "will depend on the stage at which the error happened."
            print "If you want to access the machine after the image creation " \
                  "process completes, use the --no-clean flag."
            print
        else:
            print
            print "The --no-clean flag is set, the instance will remain " \
                  "available after the image creation process completes."
            print "Remember to terminate it manually once done with it."
            print

    with shell.Step(4):
        print "Instance customization:"

        with remote_machine(USER, address, key_filename, args.debug):
            print "* Configuring sources for VPC deployment"
            fab.use_vpc_sources()

            print "* Installing puppet"
            sudo('apt-get -y install puppet')
            sudo('update-rc.d -f puppet remove')

            base = os.path.dirname(os.path.realpath(args.setup.name))

            upload_files(base, uploads, '/var/uploads')
            upload_files(base, manifests, '/var/manifests')

            print "* Applying manifests"
            for manifest in manifests:
                print "  └ Applying '{0}'".format(manifest),
                shell.wait(
                    Manifest(os.path.join('/var/manifests', manifest), args.debug),
                    'applied',
                    interval=.8
                )

            if args.manual:
                print
                print "Base setup done, manual setup requested."
                op = confirm('Open an SSH connection now?', default=True)

                if op:
                    stdout = sys.stdout
                    while hasattr(sys.stdout, 'stdout'):
                        sys.stdout = sys.stdout.stdout
                    print
                    print "-" * shell.size()[0]
                    open_shell()
                    print "-" * shell.size()[0]
                    sys.stdout = stdout
                    print
                    sys.stdout.write("Connection closed, press the return key once done.")
                    sys.stdout.flush()
                    raw_input()
                    print
                else:
                    print "Please manually setup the imahe and press the return" \
                          " key once done."
                    raw_input()
                    print

            print "* Cleaning up"
            sudo('rm -rf /var/manifests /var/uploads')

    with shell.Step(5):
        print "Image creation:"

        print "* Creating image from running instance"
        ami = c.create_image(instance.id, master['name'], master['description'])

        while True:
            try:
                image = c.get_image(ami)
                print "  └ New AMI created with ID '{0}'".format(ami)
                break
            except:
                print "  └ AMI not found, trying again".format(ami)
                pass

        print "* Waiting for image creation to complete",
        shell.wait(image, 'available', interval=.5)

        if 'public' in master:
            print "* Making image public"
            image.set_launch_permissions(group_names=['all'])

    with shell.Step(6):
        print "Resources cleanup:"

        if args.clean:
            print "* Terminating instance"
            instance.terminate()

            print "* Deleting key pair"
            c.delete_key_pair(key.name)
            os.remove(key_filename)

            print "* Deleting security group"
            group.delete()
        else:
            print "* The --no-clean flag is set, skipping cleanup"
            raise shell.Step.Skipped()

    duration = int(time.time() - start)
    duration = '{0:.0f}m {1:.0f}s'.format(duration // 60, duration % 60)

    with shell.Wrapper(72):
        print
        print "Master image creation completed in {0}; you can launch new " \
              "instances of the just created image by specifying the " \
              "following AMI ID:\n".format(duration)

        print shell.hilite("    {0}".format(ami), shell.MAGENTA)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-a', '--access-key-id')
    parser.add_argument('-s', '--secret-key')
    parser.add_argument('-f', '--force',
        dest='force',
        default=False,
        action='store_true',
        help="force the creation of a new image, deregistering any exising " \
             "image with the same name"
    )
    parser.add_argument('-c', '--no-clean',
        dest='clean',
        default=True,
        action='store_false',
        help="skip final cleanup phase, leaving the virtualization resources " \
             "in place and the instance running for further manual access"
    )
    parser.add_argument('-m', '--manual',
        dest='manual',
        default=False,
        action='store_true',
        help="perform basic setup and then wait for the user to configure " \
             "the machine manually before continuing"
    )
    parser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s ' + VERSION
    )
    parser.add_argument('setup',
        metavar='configuration-file',
        type=argparse.FileType('r')
    )

    return shell.main(parser, master)


