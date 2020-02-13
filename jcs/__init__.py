#!/usr/bin/python3

import argparse
import os
import random
import string
import sys


def _parser():
    parser = argparse.ArgumentParser(
        description='CLI to generate Jenkins slave nodes on clouds',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # global jenkins vars
    group_jenkins = parser.add_argument_group('jenkins')
    group_jenkins.add_argument('--jenkins-url',
                                default=os.getenv('JENKINS_URL'),
                                help='The url to the Jenkins server '
                                '(can be set as env var "JENKINS_URL")')
    group_jenkins.add_argument('--jenkins-username',
                               default=os.getenv('JENKINS_USERNAME'),
                               help='The username for the Jenkins server '
                               '(can be set as env var "JENKINS_USERNAME")')
    group_jenkins.add_argument('--jenkins-password',
                               default=os.getenv('JENKINS_PASSWORD'),
                               help='The password for the Jenkins server '
                               '(can be set as env var "JENKINS_PASSWORD")')

    # global AWS vars
    group_aws = parser.add_argument_group('aws')
    group_aws.add_argument('--aws-access-key-id',
                           default=os.getenv('AWS_ACCESS_KEY_ID'),
                           help='The access key for your AWS account '
                           '(can be set as env var "AWS_ACCESS_KEY_ID")')
    group_aws.add_argument('--aws-secret-access-key',
                           default=os.getenv('AWS_SECRET_ACCESS_KEY'),
                           help='The secret key for your AWS account '
                           '(can be set as env var "AWS_SECRET_ACCESS_KEY")')
    group_aws.add_argument('--aws-region-name',
                           default='eu-central-1', help='The AWS region ')

    ### subparsers
    subparsers = parser.add_subparsers(title='commands')

    ### all-in-one - create node as jenkins slave
    parser_create = subparsers.add_parser(
        'create', help='Create a new Jenkins slave')
    parser_create.add_argument('--cloud', default='ec2', choices=['ec2'],
                               help='On which cloud')
    parser_create.add_argument(
        '--arch', default='x86_64', choices=['x86_64', 'aarch64'],
        help='Architecture')
    parser_create.add_argument(
        '--instance-type', default='t2.micro', help='Instance type or Flavor')
    parser_create.add_argument(
        '--key-name', default='storage-automation', help='The keypair name')
    parser_create.add_argument(
        '--jenkins-credential', default='storage-automation-for-root-user',
        help='The Jenkins credential description(!) that can be used to access '
        'the instance')
    parser_create.add_argument('image_url', metavar='image-url',
                               help='The image url to use (a URL from OBS/IBS')
    parser_create.add_argument('jenkins_name', metavar='jenkins-name',
                               help='The name of the new jenkins slave')
    parser_create.set_defaults(func=_do_create)

    ### all-in-one - delete node as jenkins slave
    parser_delete = subparsers.add_parser(
        'delete', help='Delete a new Jenkins slave')
    parser_delete.add_argument('--cloud', default='ec2', choices=['ec2'],
                               help='On which cloud')
    parser_delete.add_argument('jenkins_name', metavar='jenkins-name',
                               help='The name of the new jenkins slave')
    parser_delete.set_defaults(func=_do_delete)

    # jenkins add node
    parser_jenkins_node_add = subparsers.add_parser('jenkins-node-add',
                                                    help='Jenkins add node')
    parser_jenkins_node_add.add_argument('hostname', help='node hostname/IP')
    parser_jenkins_node_add.add_argument('name', help='node name')
    parser_jenkins_node_add.add_argument('desc', help='node description')
    parser_jenkins_node_add.add_argument('credential',
                                         help='credential description')
    parser_jenkins_node_add.add_argument('labels',
                                         help='node labels (space separated)')
    parser_jenkins_node_add.set_defaults(func=_do_jenkins_node_add)

    # jenkins delete node
    parser_jenkins_node_delete = subparsers.add_parser(
        'jenkins-node-delete', help='Jenkins delete node')
    parser_jenkins_node_delete.add_argument('name', help='node name')
    parser_jenkins_node_delete.set_defaults(func=_do_jenkins_node_delete)

    # OpenBuildService image download
    parser_obs_image_download = subparsers.add_parser(
        'obs-image-download', help='Download a image from the OpenBuildService')
    parser_obs_image_download.add_argument('url', help='Image URL')
    parser_obs_image_download.set_defaults(func=_do_obs_image_download)

    # aws image create
    parser_aws_ec2_image_create = subparsers.add_parser(
        'ec2-image-create', help='Create a new EC2 AMI image (requires ec2imgutils)')
    parser_aws_ec2_image_create.add_argument('filepath', help='Image file path')
    parser_aws_ec2_image_create.add_argument('--image-arch', default='x86_64',
                                             help='Image architecture')
    parser_aws_ec2_image_create.set_defaults(func=_do_aws_ec2_image_create)

    # aws instance create
    parser_aws_ec2_instance_create = subparsers.add_parser(
        'ec2-instance-create', help='Create a new instance')
    parser_aws_ec2_instance_create.add_argument('name', help='Instance name')
    parser_aws_ec2_instance_create.add_argument(
        'instance_type', metavar='instance-type', help='EC2 instance type')
    parser_aws_ec2_instance_create.add_argument(
        'image_name', metavar='image-name', help='Image name')
    parser_aws_ec2_instance_create.add_argument(
        'key_name', metavar='key-name', help='Keypair name')
    parser_aws_ec2_instance_create.set_defaults(func=_do_aws_ec2_instance_create)

    # aws instance delete
    parser_aws_ec2_instance_delete = subparsers.add_parser(
        'ec2-instance-delete', help='Delete a instance')
    parser_aws_ec2_instance_delete.add_argument('id',
                                                help='Instance Id')
    parser_aws_ec2_instance_delete.set_defaults(func=_do_aws_ec2_instance_delete)

    return parser


def _do_create(args):
    from . import obs
    from . import jen
    # download image
    img = obs.OBSImage(args.image_url)
    image_path = img.download()
    # AWS/EC2
    if args.cloud == 'ec2':
        from . import aws
        # create ec2 ami
        aws_client = aws.AWSClient(
            args.aws_access_key_id, args.aws_secret_access_key, args.aws_region_name)
        ec2_image = aws_client.ec2_image_create(image_path, args.arch)
        instance_name = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
        instance_ip = aws_client.ec2_instance_create(
            'jcs-{}'.format(instance_name),
            args.instance_type, ec2_image['image_name'], args.key_name,
            tags={'jcs-jenkins-name': args.jenkins_name,
                  'jcs-jenkins-url': args.jenkins_url})

    # Jenkins
    jen_client = jen.JenkinsClient(args.jenkins_url, args.jenkins_username,
                                   args.jenkins_password)
    jen_client.create_node(
        instance_ip, args.jenkins_name, 'Running on AWS ({}, {}, {})'.format(
            instance_ip, instance_name, args.aws_region_name), args.jenkins_credential, '')


def _do_delete(args):
    from . import jen
    # Jenkins
    jen_client = jen.JenkinsClient(args.jenkins_url, args.jenkins_username,
                                   args.jenkins_password)
    jen_client.delete_node(args.jenkins_name)
    if args.cloud == 'ec2':
        from . import aws
        aws_client = aws.AWSClient(
            args.aws_access_key_id, args.aws_secret_access_key, args.aws_region_name)
        tags={'jcs-jenkins-name': args.jenkins_name,
              'jcs-jenkins-url': args.jenkins_url}
        aws_client.ec2_instance_delete_by_tags(tags)


def _do_aws_ec2_instance_create(args):
    from . import aws
    client = aws.AWSClient(args.aws_access_key_id, args.aws_secret_access_key,
                           args.aws_region_name)
    client.ec2_instance_create(args.name, args.instance_type, args.image_name,
                               args.key_name)


def _do_aws_ec2_instance_delete(args):
    from . import aws
    client = aws.AWSClient(args.aws_access_key_id, args.aws_secret_access_key,
                           args.aws_region_name)
    client.ec2_instance_delete(args.id)


def _do_aws_ec2_image_create(args):
    from . import aws
    client = aws.AWSClient(args.aws_access_key_id, args.aws_secret_access_key,
                           args.aws_region_name)
    image = client.ec2_image_create(args.filepath,args.image_arch)
    print('Name: {}, Id: {}'.format(image['image_name'], image['image_id']))


def _do_obs_image_download(args):
    from . import obs
    img = obs.OBSImage(args.url)
    img.download()


def _do_jenkins_node_add(args):
    from . import jen
    if not args.jenkins_url:
        raise Exception('No jenkins server url provided.')
    client = jen.JenkinsClient(args.jenkins_url, args.jenkins_username,
                               args.jenkins_password)
    client.create_node(args.hostname, args.name, args.desc, args.credential,
                       args.labels)


def _do_jenkins_node_delete(args):
    from . import jen
    if not args.jenkins_url:
        raise Exception('No jenkins server url provided.')
    client = jen.JenkinsClient(args.jenkins_url, args.jenkins_username,
                               args.jenkins_password)
    client.node_delete(args.name)


def main():
    parser = _parser()
    args = parser.parse_args()
    if 'func' not in args:
        sys.exit(parser.print_help())
    args.func(args)
    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

