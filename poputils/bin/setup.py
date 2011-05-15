#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A utility to setup a VPC cloud in order to run a POP application.
"""

import argparse
import os
import stat
import random
import string
import threading
import socket
import time
import re

from lxml import etree

from poputils import conf, xml
from poputils.utils import cidr, shell
from poputils import boto

VERSION = '0.1b'

DESCRIPTION = """
Sets up a virtual private cloud on Amazon Web Services in order to run POP
applications using the pop-deploy command.
"""


# Default location of the auto-generated private key; this has to eventually be
# refactored into a more configurable settings variable.
KEY_FILENAME = 'key.pem'


# Login user for the POP application manager; has for the KEY_FILENAME setting,
# this has also to eventually be refactored in order for the user to be able
# to specify it.
USER = 'ubuntu'


KNOWN_HOSTS = os.path.expanduser('~/.ssh/known_hosts')


DEFAULT_MACHINE_TYPE = 'm1.large'


class ConnectionAttempt(threading.Thread):
    def __init__(self, address):
        super(ConnectionAttempt, self).__init__(args=[address,])
        self.address = address
        self.start()

    def run(self):
        self.state = 'connecting'

        while True:
            try:
                socket.create_connection((self.address.public_ip, 22), 10)
            except socket.error:
                # Either timed out or the connection was refused
                time.sleep(.5)
            else:
                break

        self.state = 'connected'

    def update(self):
        return self


def setup(args):
    """
    Main entry point for the setup utility.
    """

    start = time.time()

    with shell.Step(1):
        print "Cloud setup validation:"

        # Load cloud configuration
        print "* Parsing the cloud XML definition file"
        config = etree.parse(args.setup)

        # Validate the configuration file
        print "* Validating the cloud XML definition against the XML schema"
        conf.schema('cloud-setup').assertValid(config)

        cloud = config.getroot().attrib

        # Raise an error if an unmanaged cloud is requested
        try:
            print "* Checking for supported setup type"
            cloud['manager']
        except KeyError:
            raise NotImplementedError("Unmanaged clouds are not yet supported")

    # Instantiate connections
    with shell.Step(2):
        print "Instantiation of the cloud manager connections"
        print "* Connecting to the VPC manager"
        c = boto.VPCConnection(args.access_key_id, args.secret_key)

    with shell.Step(3):
        print "Creation and setup of the virtual private cloud"
        # Get max vpc size (16) using the cloud subnet IP range
        print "* Getting or creating the VPC"
        vpc, created = c.get_or_create(str(cidr.CIDR(cloud['cidr'], 16)))
        if created:
            print "  └ New VPC created with ID '{0}'".format(vpc.id)
            print "* Waiting for VPC creation to complete",
            vpc = shell.wait(vpc, 'available', interval=0)
        else:
            print "  └ Using existing VPC with ID '{0}'".format(vpc.id)
            print "* Checking for valid CIDR block of the existing VPC"
            subnet_cidr = cidr.CIDR(cloud['cidr'])
            vpc_cidr = cidr.CIDR(vpc.cidr_block)
            if subnet_cidr.base not in vpc_cidr:
                raise ValueError("The requested subnet CIDR block base " \
                                 "address ({0}) falls outside the VPC CIDR " \
                                 "block ({1!s}).\nAcceptable values are in " \
                                 "the range {1.base} - {1.last}.".format(
                                 subnet_cidr.base, vpc_cidr))

            if subnet_cidr.size > vpc_cidr.size:
                raise ValueError("The requested subnet CIDR size (/{0.block}," \
                                 " {0.size} IPs) is too big for the " \
                                 "existing VPC CIDR size (/{1.block}, {1.size} " \
                                 "IPs).".format(subnet_cidr, vpc_cidr))

    with shell.Step(4):
        print "Subnet, gateway, addressing and routing setup"

        print "* Getting or creating subnet"
        subnet, created = vpc.get_or_create_subnet(str(subnet_cidr))
        if created:
            print "  └ New subnet created with ID '{0}'".format(subnet.id)
        else:
            print "  └ Using existing subnet with ID '{0}'".format(subnet.id)

        print "* Getting or creating internet gateway"
        gateway, created = vpc.get_or_create_gateway()
        if created:
            print "  └ New gateway created with ID '{0}'".format(gateway.id)
        else:
            print "  └ Using existing gateway with ID '{0}'".format(gateway.id)

        print "* Getting public IP address"
        address, created = c.get_or_create_address()
        if created:
            print "  └ New address created with IP '{0.public_ip}'".format(address)
        else:
            print "  └ Using existing address with IP '{0.public_ip}'".format(address)

        print "* Setting up routing"
        print "  └ Getting route table"
        route_table = c.get_all_route_tables()[0]
        print "  └ Associating route table with subnet"
        route_table.associate(subnet)
        print "  └ Creating route to internet gateway"
        route_table.route('0.0.0.0/0', gateway=gateway)

    with shell.Step(5):
        print "Security resources setup"

        print "* Creating temporary security group"
        name = 'pop-' + ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        group = vpc.create_security_group(name, 'Temporary security group for a POP application')
        print "  └ New security group created with ID '{0.id}'".format(group)

        print "* Authorizing all internal traffic"
        group.authorize(-1, 0, 65535, src_group=group)

        print "* Authorizing external SSH access"
        group.authorize('tcp', 22, 22, "0.0.0.0/0")

        print "* Creating key pair"
        name = 'pop-' + ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        key = c.create_key_pair(name)
        print "  └ New key pair created with name '{0.name}'".format(key)

    with shell.Step(6):
        print "Virtual machines boot process"

        print "* Getting needed images"
        images = c.get_all_images(config.xpath('//setup/machine/@image'))
        images = dict([(image.id, image) for image in images])

        print "* Reserving instances"
        reservations = {}
        for machine in config.xpath('//setup/machine'):
            machine = machine.attrib
            image = images[machine['image']]
            res = image.run(
                key_name=key.name,
                security_groups=[group.id,],
                instance_type=machine.get('type', DEFAULT_MACHINE_TYPE),
                subnet_id=subnet.id,
                private_ip_address=machine['ip'],
            )

            print "  └ New reservation (ID: {0}, IP: {1})".format(res.id, machine['ip'])
            reservations[machine['ip']] = machine, res.instances[0]

        print "* Waiting for machines to boot"
        for ip, (machine, instance) in reservations.iteritems():
            print "  └ Waiting for machine @ {0} to boot".format(ip),
            shell.wait(instance, 'running', interval=.5)

        print "* Associating public IP address to POP application manager"
        address.associate(reservations[cloud['manager']][1])

        print "* Waiting for manager to come online",
        shell.wait(ConnectionAttempt(address), 'connected', interval=.8)

    with shell.Step(7):
        print "Local environment setup"

        print "* Saving private key to disk"
        with open(KEY_FILENAME, 'w') as fh:
            fh.write(key.material)
        os.chmod(KEY_FILENAME, stat.S_IRUSR | stat.S_IWUSR)
        print "  └ Private key written to '{0}'".format(KEY_FILENAME)

        print "* Generating local fabfile"
        #raise NotImplementedError()

        print "* Saving cloud setup to XML file"
        cloud.update({
            'vpc': vpc.id,
            'subnet': subnet.id,
            'gateway': gateway.id,
            'security-group': group.id,
            'key-pair': key.name,
            'public-address': address.public_ip,
            'key-filename': KEY_FILENAME,
        })
        for machine, instance in reservations.itervalues():
            machine['instance-id'] = instance.id
            machine['launch-time'] = instance.launch_time

        with open('cloud.i.xml', 'w') as fh:
            fh.write(xml.format_document(config))

        print "* Removing old public key from known hosts (if present)"

        try:
            with open(KNOWN_HOSTS, 'r') as fh:
                known_hosts = fh.read()
        except:
            print "  └ Could not read {0}".format(KNOWN_HOSTS)
        else:
            known_hosts, count = re.subn(
                '\n{0} .*'.format(re.escape(address.public_ip)),
                '',
                known_hosts
            )
            if count:
                try:
                    with open(KNOWN_HOSTS, 'w') as fh:
                        fh.write(known_hosts)
                except:
                    print "  └ Could not write changes back to {0}".format(KNOWN_HOSTS)
                else:
                    print "  └ Public key for IP {0} removed".format(address.public_ip)
            else:
                print "  └ No public key matching IP {0} found".format(address.public_ip)

    duration = int(time.time() - start)
    duration = '{0:.0f}m {1:.0f}s'.format(duration // 60, duration % 60)

    with shell.Wrapper(72):
        print
        print "Cloud setup completed in {0}; you can manually connect to the " \
              "manager using the following command:\n".format(duration)

    print shell.hilite(
        "    ssh -i {0} {1}@{2}".format(KEY_FILENAME, USER, address.public_ip),
        shell.MAGENTA
    )

    with shell.Wrapper(72):
        print
        print "Alternatively, you can use the commands already provided by " \
              "the generated fabfile. To rapidly obtain some help about them," \
              " execute the following command in the directory where the " \
              "fabfile is located (make sure you have a recent fabric " \
              "installation):\n"
        print shell.hilite("    fab --list", shell.MAGENTA)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + VERSION)
    parser.add_argument('-I', '--access-key-id')
    parser.add_argument('-S', '--secret-key')
    parser.add_argument('setup', metavar='configuration-file',
                        type=argparse.FileType('r'))

    return shell.main(parser, setup)


