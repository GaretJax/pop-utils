#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A utility to destroy an already setup POP cloud based on a cloud description
XML file.
"""

import argparse
import os
import time

from lxml import etree

from poputils import conf
from poputils import boto
from poputils.utils import shell


VERSION = '0.1b'

DESCRIPTION = """
Destroys an existing POP cloud setup and frees all associated resources.
"""


def destroy(args):
    """
    Main entry point for the master utility.
    """

    start = time.time()

    with shell.Step(1):
        print "Cloud setup validation:"

        if args.clean:
            raise shell.Step.Skipped('Not need to parse a configuration file')

        # Load master configuration
        print "* Parsing the master XML definition file"
        config = etree.parse(args.setup)

        assets = config.getroot().attrib
        machines = config.xpath('/cloud/setup/machine/@instance-id')

        # Validate the configuration file
        print "* Validating the master XML definition against the XML schema"
        conf.schema('cloud-instance').assertValid(config)
        #raise shell.Step.Skipped("Cloud XML instance definition schema not yet implemented")

    # Instantiate connections
    with shell.Step(2):
        print "Instantiation of the cloud manager connection:"
        print "* Connecting to the VPC manager"
        c = boto.VPCConnection(args.access_key_id, args.secret_key)

    if args.clean:
        with shell.Step(3):
            print "Deleting all security groups"

            grpcnt = 0
            for group in c.get_all_security_groups():
                if group.name.startswith('pop-'):
                    print "* Deleting", group.name
                    group.delete()
                    grpcnt += 1
                else:
                    print "* Skipping", group.name

        with shell.Step(4):
            print "Deleting all key pairs:"

            kpcnt = 0
            for key in c.get_all_key_pairs():
                if key.name.startswith('pop-'):
                    print "* Deleting", key.name
                    key.delete()
                    kpcnt += 1
                else:
                    print "* Skipping", key.name

        duration = int(time.time() - start)
        duration = '{0:.0f}m {1:.0f}s'.format(duration // 60, duration % 60)

        with shell.Wrapper(72):
            print
            print "Destroyed {0} groups and {1} key pairs in {2}.\n".format(
                grpcnt, kpcnt, duration)

        return

    with shell.Step(3):
        print "Stopping all instances:"

        terminating = []

        for instance in machines:
            print "* Terminating instance with ID {0}".format(instance)
            try:
                instance = c.terminate_instances(instance)[0]
            except boto.ResponseError as e:
                if boto.AWSException(e).code == 'InvalidInstanceID.NotFound':
                    print "  └", shell.hilite("Instance not found", shell.YELLOW)
                else:
                    raise
            else:
                if instance.state == 'terminated':
                    print "  └ Instance already terminated"
                else:
                    terminating.append(instance)

        if terminating:
            print "* Waiting for {0} instances to terminate".format(len(terminating))
            for instance in terminating:
                print "  └ Waiting for instance with ID {0} to terminate".format(instance.id),
                shell.wait(instance, 'terminated', interval=.5, valid=('shutting-down',))

    with shell.Step(4):
        print "Destroying security assets"

        print "* Destroying security group"
        try:
            time.sleep(8) # Let some time to AWS to disassociate the machines
            c.delete_security_group(assets['security-group'])
        except boto.ResponseError as e:
            if boto.AWSException(e).code == 'InvalidGroup.NotFound':
                print "  └ Group already deleted"
            else:
                raise

        print "* Destroying key pair"
        c.delete_key_pair(assets['key-pair'])

        if os.path.exists(assets['key-filename']):
            print "  └ Deleting local private key '{0}'".format(assets['key-filename'])
            try:
                os.remove(assets['key-filename'])
                print "  └ Local private key deleted"
            except:
                print "  └ Unable to delete local private key"

    with shell.Step(5):
        print "Freeing unused resources"

        print "* Releasing elastic IP address"
        try:
            address = c.get_all_addresses([assets['public-address']])[0]
        except boto.ResponseError as e:
            if boto.AWSException(e).code == 'InvalidAddress.NotFound':
                print "  └ Address already released"
            else:
                raise
        else:
            address.release()

        print "* Deleting subnet"
        try:
            c.delete_subnet(assets['subnet'])
        except boto.ResponseError as e:
            if boto.AWSException(e).code == 'InvalidSubnetID.NotFound':
                print "  └ Subnet already deleted"
            else:
                raise

        print
        print shell.hilite("The internet gateway and the VPC will not be " \
                           "deleted as they could still be needed by other " \
                           "applications and don't generate additional " \
                           "costs.", shell.MAGENTA)
        print

    duration = int(time.time() - start)
    duration = '{0:.0f}m {1:.0f}s'.format(duration // 60, duration % 60)

    with shell.Wrapper(72):
        print
        print "Cloud destroyed in {0}; all resources were correctly torn down.\n".format(duration)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--configuration-file',
        dest='setup',
        type=argparse.FileType('r'),
    )
    group.add_argument('-C', '--clean-all',
        dest='clean',
        default=False,
        action='store_true',
        help="cleans all security groups and key pairs whose name starts with"\
             " 'pop-'",
    )
    
    parser.add_argument('-a', '--access-key-id')
    parser.add_argument('-s', '--secret-key')
    parser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s ' + VERSION
    )

    return shell.main(parser, destroy)

