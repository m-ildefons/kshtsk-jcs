import urllib3
urllib3.disable_warnings()
import time

from jenkinsapi.jenkins import Jenkins
from jenkinsapi.utils.crumb_requester import CrumbRequester


class JenkinsClient:
    def __init__(self, url, username, password):
        self._url=url
        self._username=username
        self._password=password
        self._ssl_verify=False
        self._client=self._client_init()

    def _client_init(self):
        crumb_requester = CrumbRequester(
            baseurl=self._url,
            username=self._username,
            password=self._password,
            ssl_verify=self._ssl_verify
        )
        server = Jenkins(self._url, self._username, self._password,
                         requester=crumb_requester, ssl_verify=self._ssl_verify)
        print('Connected to jenkins server {}'.format(server.version))
        return server

    def offline_node(self, node_name, message=''):
        node = self._client.get_nodes()[node_name]
        node.set_offline(message)
        print('Jenkins node "{}" offline'.format(node_name))

    def delete_node(self, node_name):
        print('Jenkins node "{}" deleting...'.format(node_name))
        self._client.delete_node(node_name)
        print('Jenkins node "{}" deleted'.format(node_name))

    def create_node(self, node_hostname, node_name, node_desc, credential_desc,
                    node_labels, force=True):
        # does node already exist?
        if node_name in self._client.nodes.keys() and force:
            self.offline_node(node_name, 'Node will be deleted soon')
            self.delete_node(node_name)

        node_dict = {
            'num_executors': 1,
            'node_description': node_desc,
            'remote_fs': '/tmp',
            'labels': node_labels,
            'exclusive': True,
            'host': node_hostname,
            'port': 22,
            'credential_description': credential_desc,
            'jvm_options': '-Xmx2000M',
            'java_path': '/usr/bin/java',
            'prefix_start_slave_cmd': '',
            'suffix_start_slave_cmd': '',
            'max_num_retries': 0,
            'retry_wait_time': 0,
            'retention': 'Always',
            'ondemand_delay': 1,
            'ondemand_idle_delay': 5
        }
        print('Jenkins node "{}" creating ...'.format(node_name))
        node = self._client.nodes.create_node(node_name, node_dict)
        print('Jenkins node "{}" created'.format(node_name))
        for retry in range(60):
            node = self._client.get_nodes()[node_name]
            if node.is_online():
                print('Jenkins node is online now'.format(node.is_online()))
                return node
            else:
                print('Jenkins node is not online. Waiting...')
                time.sleep(5)

        raise Exception('Jenkins node "{}" ({}) still not online. abort'.format(node_name, node_hostname))
