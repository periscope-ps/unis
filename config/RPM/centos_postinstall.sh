#!/bin/bash

USER=periscope
HOME=/var/lib/periscope
SVDIR=/etc/supervisor
SHARE=/usr/share/periscope
LOG=/var/log/periscope.log

wget http://www.ultimate.com/phil/python/download/jsonpath-0.54.tar.gz -O /tmp
tar -xf /tmp/jsonpath-0.54.tar.gz -C /tm
cd /tmp/jsonpath-0.54
python setup.py build
python setup.py install
rm -rf jsonpath-0.54*
cd -

easy_install supervisor
easy_install argparse

/usr/bin/getent group ${USER} || /usr/sbin/groupadd -r ${USER}
/usr/bin/getent passwd ${USER} || /usr/sbin/useradd -r -d ${HOME} -s /sbin/nologin -g ${USER} ${USER}

if [ ! -d ${HOME} ]; then
    mkdir -p ${HOME}
fi

if [ ! -d ${SVDIR}/conf.d ]; then
    mkdir -p ${SVDIR}/conf.d
fi

chown ${USER}:${USER} ${SVDIR}
chown ${USER}:${USER} ${HOME}
cp ${SHARE}/supervisord.conf ${SVDIR}/supervisor.conf
cp ${SHARE}/unis.conf ${SVDIR}/conf.d/unis.conf

touch ${LOG}
chown ${USER}:${USER} ${LOG}

if grep -q -i "release 6" /etc/redhat-release
then
    cp ${SHARE}/periscoped /etc/init.d/periscoped
    chmod +x /etc/initd.d/periscoped
    chown root:root /etc/init.d/periscoped
    chkconfig --add periscoped
elif grep -q -i "release 7" /etc/redhat-release
then
    cp ${SHARE}/periscoped.service /etc/systemd/system/periscoped.service
    systemctl daemon-reload
    systemctl enable periscoped
fi
