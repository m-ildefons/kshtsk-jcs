Jenkins Cloud Slave (jcs)
-------------------------

`Jenkins Cloud Slave`_ is a command line interface to create
`Jenkins`_ slave servers. With that, new Jenkins slaves can
be dynamically created eg. on public clouds (AWS) or private
clouds (OpenStack).

Installation
============

You can install `jcs` inside of a virtualenv::

  virtualenv venv
  source venv/bin/activate
  pip install git+git://github.com/toabctl/jcs.git#egg=jcs[aws,obs,jenkins]

Usage
=====
Some examples how to use `jcs`. All the following calls to `jcs`
expect that some environment variables are set (the parameters
can also be given as CLI switches, eg. `--jenkins-url` but for
shorter commands, we use the env vars here).

For Jenkins::

  export JENKINS_URL=https://localhost
  export JENKINS_USERNAME=user
  export JENKINS_PASSWORD=superSecure!

When doing something with AWS, also theses are needed::

  export AWS_ACCESS_KEY_ID=my-access-key
  export AWS_SECRET_ACCESS_KEY=my-secret-access-key

When doing something with OpenStack::

  export OS_CLOUD=my-cloud

where `my-cloud` needs to be defined in the `clouds.yaml` file

All-in-one - Create a Jenkins slave on AWS/EC2 from an OBS image
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Assuming you have an EC2-ready image on the `OpenBuildService`_ (OBS) that you
want to use as a jenkins slave, do::

  jcs create --key-name my-keypair-name --jenkins-credential cred-description \
      http://download.suse.de/ibs/Devel:/Storage:/images/openSUSE_Leap_15.1/minimal-openSUSE-Leap-15.1.aarch64-ec2-hvm.raw.xz \
      jenkins-slave-name

Where `--key-name` is the key that must be available on the cloud
to be able to login into the instance. `--jenkins-credential` is the
credential that is registered inside the Jenkins master. Here, use the
description of the credential (not the ID).
The image from OBS is only downloaded once and cached in `~/.cache/jcs`.
The image will only downloaded again, if the sha256 changed.

To delete the whole stack (Jenkins node and EC2 instance), do::

  jcs delete jenkins-slave-name

Note: This only works if the slave got created with `jcs create` because
it uses EC2 tags to build the relation between the jenkins slave name
and the EC2 instance.

Add node as Jenkins slave
+++++++++++++++++++++++++

If you already have a node that should be registered as a Jenkins slave,
all you need are Jenkins credentials (for creating the node in Jenkins),
some node information and a Jenkins credential (to log into the node)::

  export JENKINS_URL=https://localhost
  export JENKINS_USERNAME=user
  export JENKINS_PASSWORD=superSecure!

  jcs jenkins-node-add my-slave-hostname-or-ip slave-name "slave description" \
    slave-credentials "label1 label2"

* The `slave_credentials` needs to be the "credential description" (not the ID).
  This is a `limitation`_ of `jenkinsapi`_ which is used to talk to Jenkins.
* Instead of using the `JENKINS_*` enviroment variables, command line switches
  (`--jenkins-url`, `--jenkins-username` and `--jenkins-password`) are also
  available. See `jcs -h`.

Remove node as Jenkins slave
++++++++++++++++++++++++++++

Similar to `jenkins-node-add`, removing the node can be done with::

  jcs jenkins-node-remove slave-name

The environment variables (`JENKINS_*`) or command line switches (`--jenkins-*`)
must be set when executing this command.

Download a OBS image
++++++++++++++++++++

Downloading a image from OBS::

  jcs obs-image-download http://download.suse.de/ibs/Devel:/Storage:/images/openSUSE_Leap_15.1/minimal-openSUSE-Leap-15.1.x86_64-ec2-hvm.raw.xz

The downloaded images are cached unter `~/.cache/jcs`.

.. _`Jenkins Cloud Slave`: https://github.com/toabctl/jcs
.. _`Jenkins`: https://jenkins.io/
.. _`jenkinsapi`: https://github.com/pycontribs/jenkinsapi
.. _`limitation`: https://github.com/pycontribs/jenkinsapi/issues/766
.. _`OpenBuildService`: https://openbuildservice.org/
