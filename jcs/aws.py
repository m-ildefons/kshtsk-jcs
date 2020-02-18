import hashlib
import time
import os
import sys
import subprocess
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config


class AWSClient:
    def __init__(self, access_key, secret_key, region_name):
        self._access_key = access_key
        self._secret_key = secret_key
        self._region_name = region_name
        self._ec2_client = boto3.client('ec2', aws_access_key_id=self._access_key,
                                        aws_secret_access_key=self._secret_key,
                                        region_name=self._region_name)
        self._ec2 = boto3.resource('ec2', aws_access_key_id=self._access_key,
                                   aws_secret_access_key=self._secret_key,
                                   region_name=self._region_name)
        self._s3_client = boto3.client('s3', aws_access_key_id=self._access_key,
                                       aws_secret_access_key=self._secret_key,
                                       region_name=self._region_name,
                                       config=Config(signature_version='s3v4'))
        self._iam_client = boto3.client('iam', aws_access_key_id=self._access_key,
                                        aws_secret_access_key=self._secret_key,
                                        region_name=self._region_name)

    def _ec2_image_id(self, image_name):
        resp = self._ec2_client.describe_images(
            Filters=[{'Name': 'name', 'Values': [image_name]}])
        if len(resp['Images']) > 1:
            raise Exception('Found multiple ({}) images with name "{}"'.format(
                len(resp['Images']), image_name))
        elif len(resp['Images']) == 0:
            return None
        return resp['Images'][0]['ImageId']

    def _ec2_image_name(self, image_path):
        image_name = os.path.basename(image_path)
        if image_name.endswith('.xz'):
            image_name = image_name[:-3]
        if image_name.endswith('.raw'):
            image_name = image_name[:-4]
        return image_name

    def ec2_image_create(self, image_path, image_arch):
        image_name = self._ec2_image_name(image_path)
        image_id = self._ec2_image_id(image_name)
        if image_id:
            print('EC2 image {} already exists (Id: {}).'.format(
                image_name, image_id))
            return {'image_name': image_name, 'image_id': self._ec2_image_id(image_name)}

        print('EC2 uploading image {} as new AMI ...'.format(image_name))
        cmd = ['ec2uploadimg',
               '-s', self._secret_key, '--access-id', self._access_key,
               '-d', image_name,
               '-m', 'arm64' if image_arch == 'aarch64' else image_arch,
               '-n', image_name,
               '-r', self._region_name,
               '--ena-support',
               image_path
        ]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print('Failed to call "{}" (rc: {}): {}'.format(
                e.cmd, e.returncode, e.output))
            sys.exit(1)
        # now get the imageId and return it
        return {'image_name': image_name, 'image_id': self._ec2_image_id(image_name)}

    def ec2_instance_create(self, instance_name, instance_type, image_name, key_name, tags={}):
        image_id = self._ec2_image_id(image_name)
        resp = self._ec2_client.run_instances(ImageId=image_id, InstanceType=instance_type,
                                              KeyName=key_name, MinCount=1, MaxCount=1)
        instance_id = resp['Instances'][0]['InstanceId']
        print('New EC2 instance is "{}" ({}). Waiting...'.format(instance_id,
                                                             instance_name))
        instance = self._ec2.Instance(instance_id)
        instance.wait_until_running()
        instance = self._ec2.Instance(instance_id)
        print('EC2 instance "{}" running. {}'.format(
            instance_id, instance.public_ip_address))

        # tags for the resources
        tags_all = []
        for key, value in tags.items():
            tags_all.append({'Key': key, 'Value': value})
        self._ec2_client.create_tags(Resources=[instance_id], Tags=tags_all)

        return instance.public_ip_address

    def ec2_instance_delete(self, instance_id):
        resp = self._ec2_client.terminate_instances(InstanceIds=[instance_id])
        print('EC2 instance "{}" deleted'.format(instance_id))

    def ec2_instance_delete_by_tags(self, tags):
        # add same default tag as we add in ec2_instance_create()
        filters_all = []
        for key, value in tags.items():
            filters_all.append({'Name': 'tag:{}'.format(key), 'Values': [value]})
        print('EC2 search for deletable instances with filters: {}'.format(filters_all))
        for instance in self._ec2.instances.filter(Filters=filters_all):
            instance.terminate()
            print('EC2 instance "{}" deleted'.format(instance.id))
