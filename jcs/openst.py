import openstack

class OpenstClient:
    def __init__(self, os_cloud):
        self._os_cloud = os_cloud
        self._conn = openstack.connect(cloud=os_cloud)

    def _os_instance_get_floating_ip(self, instance, network_fixed,
                                     network_public):
        floating_ip = None
        for addr in instance['addresses'].get(network_fixed, []):
            if addr['version'] != 4:
                continue
            if addr['OS-EXT-IPS:type'] == network_public:
                floating_ip = addr['addr']
                return floating_ip
        for addr in instance['addresses'].get(network_public, []):
            if addr['version'] != 4:
                continue
            floating_ip = addr['addr']
            return floating_ip
        return floating_ip

    def os_instance_create(self, instance_name, instance_type, image_name, key_name,
                           network_fixed, network_public, security_groups):
        instance = self._conn.get_server(instance_name)
        if instance:
            raise Exception('OS instance "{}" ({}) already available'.format(
                instance_name, instance['id']))

        image = self._conn.get_image(image_name)
        if not image:
            raise Exception('OS image "{}" not found'.format(image_name))

        instance_type = self._conn.get_flavor(instance_type)
        if not instance_type:
            raise Exception('OS instance type (flavor) "{}" not found'.format(instance_type))

        network_fixed = self._conn.get_network(network_fixed)

        # create instance
        instance = self._conn.create_server(
            instance_name, image=image, flavor=instance_type, key_name=key_name,
            network=network_public, security_groups=security_groups,
            wait=True, auto_ip=True)

        # add floating ip
        try:
            # this might fail (eg. on OVH)
            self._conn.add_auto_ip(instance)
            # update instance data (to be able to get the floating ip)
            instance = self._conn.get_server(instance)
        except:
            pass
        print('OS instance {} ({}) created'.format(instance['name'], instance['id']))

        # handle floating/public IP
        floating_ip = self._os_instance_get_floating_ip(instance, network_fixed,
                                                        network_public)
        if not floating_ip:
            raise Exception('OS public (floating) IP not found for {}'.format(instance['name']))
        print('OS instance {} has {}'.format(instance['name'], floating_ip))
        return floating_ip

    def os_instance_delete(self, instance_name):
        instance = self._conn.get_server(instance_name)
        if instance:
            print('OS instance "{}" ({}) deleting...'.format(instance_name, instance['id']))
            self._conn.delete_server(instance_name, wait=True, delete_ips=True)
            print('OS instance "{}" ({}) deleted'.format(instance_name, instance['id']))
        else:
            print('OS instance "{}" not available for deleting '.format(instance_name))
