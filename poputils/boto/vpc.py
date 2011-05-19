import base64

from poputils.boto import error, ec2

import boto.vpc
import boto.ec2.ec2object
import boto.ec2.securitygroup
import boto.ec2.address
import boto.ec2.instance


class Address(boto.ec2.address.Address):

    def endElement(self, name, value, connection):
           if name == 'allocationId':
               self.id = value
           else:
               boto.ec2.address.Address.endElement(self, name, value, connection)
               
    def associate(self, instance):
        return self.connection.associate_address(instance.id, self.id)
    
    def disassociate(self):
        self.connection.disassociate_address(self.association_id)
    
    def release(self):
        self.connection.release_address(self.id)
    

class InternetGateway(boto.ec2.ec2object.EC2Object):
    def __init__(self, connection=None):
        boto.ec2.ec2object.EC2Object.__init__(self, connection)
        self.id = None

    def __repr__(self):
        return 'InternetGateway:%s' % self.id

    def endElement(self, name, value, connection):
        if name == 'internetGatewayId':
            self.id = value
        elif name in set(['tagSet', 'attachmentSet', 'internetGateway']):
            pass
        else:
            setattr(self, name, value)

class VPC(boto.vpc.VPC):
    def __call__(self, connection=None):
        self.connection = connection
        return self
    
    def create_security_group(self, name, description):
        return self.connection.create_security_group(name, description, self.id)
    
    def get_or_create_gateway(self):
        try:
            gateway = self.connection.get_all_internet_gateways()[0]
            created = False
        except IndexError:
            gateway = self.connection.create_internet_gateway()
            created = True

        try:
            self.connection.attach_internet_gateway(gateway.id, self.id)
        except boto.exception.EC2ResponseError as e:
            e = error.AWSException(e)
            if e.code != 'Resource.AlreadyAssociated':
                raise

        return gateway, created
    
    def get_or_create_subnet(self, cidr):
        for subnet in self.connection.get_all_subnets():
            if subnet.cidr_block == cidr:
                return subnet, False
        else:
            subnet = self.connection.create_subnet(self.id, cidr)
            return subnet, True
    
    def update(self):
        params = {}
        self.connection.build_list_params(params, [self.id], 'VpcId')
        return self.connection.get_list('DescribeVpcs', params, [('item', self)])[0]


class RouteTable(boto.ec2.ec2object.EC2Object):
    def __init__(self, connection=None):
        boto.ec2.ec2object.EC2Object.__init__(self, connection)
        self.id = None

    def __repr__(self):
        return 'RouteTable:%s' % self.id

    def endElement(self, name, value, connection):
        if name == 'routeTableId':
            self.id = value
        else:
            setattr(self, name, value)
    
    def route(self, cidr, instance=None, gateway=None):
        instance = instance.id if instance else None
        gateway = gateway.id if gateway else None
        return self.connection.create_route(self.id, cidr, instance, gateway)
        
    def associate(self, subnet):
        return self.connection.associate_route_table(self.id, subnet.id)


class Route(boto.ec2.ec2object.EC2Object):
    def __init__(self, connection=None):
        boto.ec2.ec2object.EC2Object.__init__(self, connection)
        self.id = None

    def __repr__(self):
        return 'RouteTableAssociation:%s' % self.id
    
    def endElement(self, name, value, connection):
        if name == 'associationId':
            self.id = value
        else:
            setattr(self, name, value)



class SecurityGroup(boto.ec2.securitygroup.SecurityGroup):
    def endElement(self, name, value, connection):
        if name == 'groupId':
            self.id = value
        else:
            boto.ec2.securitygroup.SecurityGroup.endElement(self, name, value, connection)
    def delete(self):
        return self.connection.delete_security_group(self.id)
    def authorize(self, ip_protocol=None, from_port=None, to_port=None,
                  cidr_ip=None, src_group=None):
        if src_group:
            cidr_ip = None
            src_group_id = src_group.id
            src_group_owner_id = src_group.owner_id
        else:
            src_group_id = None
            src_group_owner_id = None
        status = self.connection.authorize_security_group(self.id,
                                                          src_group_id,
                                                          src_group_owner_id,
                                                          ip_protocol,
                                                          from_port,
                                                          to_port,
                                                          cidr_ip)
        if status:
            self.add_rule(ip_protocol, from_port, to_port, src_group_id,
                          src_group_owner_id, cidr_ip)
        return status


class VPCConnection(boto.vpc.VPCConnection, ec2.EC2Connection):
    
    #
    # Security groups
    #
    def delete_security_group(self, group_id):
        """
        Delete a security group from your account.

        :type key_name: string
        :param key_name: The name of the keypair to delete
        """
        params = {'GroupId':group_id}
        return self.get_status('DeleteSecurityGroup', params, verb='POST')
    
    def get_all_security_groups(self, groupnames=None, filters=None):
        params = {}
        if groupnames:
            self.build_list_params(params, groupnames, 'GroupName')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeSecurityGroups', params,
                             [('item', SecurityGroup)], verb='POST')

    def create_security_group(self, name, description, vpc_id):
        params = {'GroupName':name, 'GroupDescription':description, 'VpcId': vpc_id}
        group = self.get_object('CreateSecurityGroup', params, SecurityGroup, verb='POST')
        group.name = name
        group.description = description
        return group
    
    def _authorize_deprecated(self, group_id, src_security_group_id=None,
                              src_security_group_owner_id=None):
        params = {'GroupId':group_id}
        if src_security_group_id:
            params['SourceSecurityGroupId'] = src_security_group_id
        if src_security_group_owner_id:
            params['SourceSecurityGroupOwnerId'] = src_security_group_owner_id
        return self.get_status('AuthorizeSecurityGroupIngress', params, verb='POST')
    
    def authorize_security_group(self, group_id, src_security_group_id=None,
                                 src_security_group_owner_id=None,
                                 ip_protocol=None, from_port=None, to_port=None,
                                 cidr_ip=None):
        if src_security_group_id:
            if from_port is None and to_port is None and ip_protocol is None:
                return self._authorize_deprecated(group_id,
                                                  src_security_group_id,
                                                  src_security_group_owner_id)
        params = {'GroupId':group_id}
        if src_security_group_id:
            params['IpPermissions.1.Groups.1.GroupId'] = src_security_group_id
        if src_security_group_owner_id:
            params['IpPermissions.1.Groups.1.UserId'] = src_security_group_owner_id
        if ip_protocol:
            params['IpPermissions.1.IpProtocol'] = ip_protocol
        if from_port:
            params['IpPermissions.1.FromPort'] = from_port
        if to_port:
            params['IpPermissions.1.ToPort'] = to_port
        if cidr_ip:
            params['IpPermissions.1.IpRanges.1.CidrIp'] = cidr_ip
        return self.get_status('AuthorizeSecurityGroupIngress', params, verb='POST')
    
    #
    # Elastic IP
    #
    def get_or_create_address(self):
        for address in self.get_all_addresses(filters={'domain': 'vpc'}):
            if address.instance_id is None:
                return address, False
        else:
            return self.allocate_address(), True
    
    def allocate_address(self):
        return self.get_object('AllocateAddress', {'Domain': 'vpc'}, Address, verb='POST')
    
    def release_address(self, allocation_id):
        return self.get_status('ReleaseAddress', {'AllocationId': allocation_id}, verb='POST')
    
    def associate_address(self, instance_id, allocation_id):
        params = {'InstanceId' : instance_id, 'AllocationId' : allocation_id}
        return self.get_status('AssociateAddress', params, verb='POST')
    
    def disassociate_address(self, association_id):
        params = {'AssociationId' : association_id}
        return self.get_status('DisassociateAddress', params, verb='POST')
    
    def get_all_addresses(self, addresses=None, filters=None):
        """
        Get all EIP's associated with the current credentials.

        :type addresses: list
        :param addresses: Optional list of addresses.  If this list is present,
                           only the Addresses associated with these addresses
                           will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list of :class:`boto.ec2.address.Address`
        :return: The requested Address objects
        """
        params = {}
        if addresses:
            self.build_list_params(params, addresses, 'PublicIp')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeAddresses', params, [('item', Address)], verb='POST')

    
    #
    # Route tables
    #
    
    def associate_route_table(self, route_table_id, subnet_id):
        params = {
            'RouteTableId': route_table_id,
            'SubnetId': subnet_id,
        }
        return self.get_object('AssociateRouteTable', params, Route, verb='POST')

    def delete_route_table(self, route_table_id):
        params = {
            'RouteTableId': route_table_id,
        }
        return self.get_status('CreateRoute', params, verb='POST')

    def create_route(self, route_table_id, cidr, instance_id=None, gateway_id=None):
        assert bool(instance_id) != bool(gateway_id)

        params = {
            'RouteTableId': route_table_id,
            'DestinationCidrBlock': cidr
        }

        if instance_id:
            params['InstanceId'] = instance_id
        else:
            params['GatewayId'] = gateway_id

        return self.get_status('CreateRoute', params, verb='POST')
    
    def get_all_route_tables(self):
        return self.get_list('DescribeRouteTables', {}, [('item', RouteTable)], verb='POST')
    
    #
    # Internet gateway
    #
    
    def get_all_internet_gateways(self):
        return self.get_list('DescribeInternetGateways', {}, [('item', InternetGateway)], verb='POST')
    
    def create_internet_gateway(self):
        return self.get_object('CreateInternetGateway', {}, InternetGateway, verb='POST')

    def delete_internet_gateway(self, gateway_id):
        params = {'InternetGatewayId': gateway_id}
        return self.get_status('DeleteInternetGateway', params)
    
    def attach_internet_gateway(self, gateway_id, vpc_id):
        params = {
            'InternetGatewayId': gateway_id,
            'VpcId': vpc_id,
        }
        return self.get_status('AttachInternetGateway', params, verb='POST')
    
    #
    # VPCs
    #
    
    def get_or_create(self, cidr):
        try:
            return self.get_all_vpcs()[0], False
        except IndexError:
            return self.create_vpc(cidr), True
            
    def get_all_vpcs(self, vpc_ids=None, filters=None):
        """
        Retrieve information about your VPCs.  You can filter results to
        return information only about those VPCs that match your search
        parameters.  Otherwise, all VPCs associated with your account
        are returned.

        :type vpc_ids: list
        :param vpc_ids: A list of strings with the desired VPC ID's

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
                        Possible filter keys are:

                        - *state*, the state of the VPC (pending or available)
                        - *cidrBlock*, CIDR block of the VPC
                        - *dhcpOptionsId*, the ID of a set of DHCP options

        :rtype: list
        :return: A list of :class:`boto.vpc.vpc.VPC`
        """
        params = {}
        if vpc_ids:
            self.build_list_params(params, vpc_ids, 'VpcId')
        if filters:
            i = 1
            for filter in filters:
                params[('Filter.%d.Key' % i)] = filter[0]
                params[('Filter.%d.Value.1')] = filter[1]
                i += 1
        return self.get_list('DescribeVpcs', params, [('item', VPC)])

    def create_vpc(self, cidr_block):
        """
        Create a new Virtual Private Cloud.

        :type cidr_block: str
        :param cidr_block: A valid CIDR block

        :rtype: The newly created VPC
        :return: A :class:`boto.vpc.vpc.VPC` object
        """
        params = {'CidrBlock' : cidr_block}
        return self.get_object('CreateVpc', params, VPC)
    
    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small', placement=None,
                      kernel_id=None, ramdisk_id=None,
                      monitoring_enabled=False, subnet_id=None,
                      block_device_map=None,
                      disable_api_termination=False,
                      instance_initiated_shutdown_behavior=None,
                      private_ip_address=None,
                      placement_group=None, client_token=None):
        params = {'ImageId':image_id,
                  'MinCount':min_count,
                  'MaxCount': max_count}
        if key_name:
            params['KeyName'] = key_name
        if security_groups:
            l = []
            for group in security_groups:
                if isinstance(group, SecurityGroup):
                    l.append(group.id)
                else:
                    l.append(group)
            self.build_list_params(params, l, 'SecurityGroupId')
        if user_data:
            params['UserData'] = base64.b64encode(user_data)
        if addressing_type:
            params['AddressingType'] = addressing_type
        if instance_type:
            params['InstanceType'] = instance_type
        if placement:
            params['Placement.AvailabilityZone'] = placement
        if placement_group:
            params['Placement.GroupName'] = placement_group
        if kernel_id:
            params['KernelId'] = kernel_id
        if ramdisk_id:
            params['RamdiskId'] = ramdisk_id
        if monitoring_enabled:
            params['Monitoring.Enabled'] = 'true'
        if subnet_id:
            params['SubnetId'] = subnet_id
        if private_ip_address:
            params['PrivateIpAddress'] = private_ip_address
        if block_device_map:
            block_device_map.build_list_params(params)
        if disable_api_termination:
            params['DisableApiTermination'] = 'true'
        if instance_initiated_shutdown_behavior:
            val = instance_initiated_shutdown_behavior
            params['InstanceInitiatedShutdownBehavior'] = val
        if client_token:
            params['ClientToken'] = client_token
        return self.get_object('RunInstances', params, boto.ec2.instance.Reservation, verb='POST')
    