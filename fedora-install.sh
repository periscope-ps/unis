#!/bin/bash
#
# Self-extracting bash script that installs UNIS and the MS
#
# create self extracting tarball like this (from parent dir):
# 'tar zc peri-tornado | cat peri-tornado/ubuntu-install.sh - > peri-tornado.sh'
# Supports: Debian based distributions
# Depends: python 2.6

if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

PYTHON_VERSION=`python --version 2>&1 | awk '{print $2}'`
PV_MAJOR=${PYTHON_VERSION:0:1}
PV_MINOR=${PYTHON_VERSION:2:1}

if [ $PV_MAJOR != 2 ]; then
   echo "Python version is ${PYTHON_VERSION}, periscope requires 2.6 or greater, but less than 3"
   exit 1
fi

if [ $PV_MINOR -lt 6 ]; then
   echo "Python version is ${PYTHON_VERSION}, periscope requires 2.6 or greater, but less than 3"
   exit 1
fi


SKIP=`awk '/^__TARFILE_FOLLOWS__/ { print NR + 1; exit 0; }' $0`
THIS=`pwd`/$0
tail -n +$SKIP $THIS | tar -xz

# Installation steps for LAMP Toolkit
DIR=peri-tornado

GENSOURCES_FILE="/etc/yum.repos.d/10gen.repo"

GEN_REPO='[10gen]\nname=10gen Repository\nbaseurl=http://downloads-distro.mongodb.org/repo/redhat/os/x86_64\ngpgcheck=0\nenabled=1\n'

ARCH=`uname -m`
if [ $ARCH == 'i686' -o $ARCH == 'i386' ]
  then
    GEN_REPO='[10gen]\nname=10gen Repository\nbaseurl=http://downloads-distro.mongodb.org/repo/redhat/os/i686\ngpgcheck=0\nenabled=1\n'
fi

echo -e ${GEN_REPO} > ${GENSOURCES_FILE}
yum -y install mongo-10gen mongo-10gen-server
yum -y install python-setuptools

#git clone git://github.com/ahassany/asyncmongo.git
#cd asyncmongo
#sudo python setup.py install
#cd ..

yum -y install m2crypto
yum -y install libnl-devel
cd ${DIR}
python ./setup.py install

mkdir -p /usr/local/etc/certs/
install -D periscope/ssl/* /usr/local/etc/certs/

exit 0

__TARFILE_FOLLOWS__
