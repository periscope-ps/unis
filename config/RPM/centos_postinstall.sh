#!/bin/bash

USER=periscope
ETC=/etc/periscope
HOME=/var/lib/periscope
SVDIR=/etc/supervisor
SHARE=/usr/share/periscope

wget http://www.ultimate.com/phil/python/download/jsonpath-0.54.tar.gz -O /tmp/jsonpath-0.54.tar.gz
tar -xf /tmp/jsonpath-0.54.tar.gz -C /tmp
cd /tmp/jsonpath-0.54
python setup.py build
python setup.py install
cd -
rm -rf /tmp/jsonpath-0.54*

easy_install argparse
easy_install netlogger
easy_install motor
easy_install tornado==4.2
easy_install tornado-redis

/usr/bin/getent group ${USER} || /usr/sbin/groupadd -r ${USER}
/usr/bin/getent passwd ${USER} || /usr/sbin/useradd -r -d ${HOME} -s /sbin/nologin -g ${USER} ${USER}

if [ ! -d ${ETC} ]; then
    mkdir -p ${ETC}
fi

if [ ! -d ${HOME} ]; then
    mkdir -p ${HOME}
fi

chown -R ${USER}:${USER} ${HOME}

if [ ! -f ${ETC}/unis.conf ]; then
    cp ${SHARE}/unis.conf ${ETC}/unis.conf
fi

if [ ! -f ${ETC}/ms.conf ]; then
    cp ${SHARE}/ms.conf ${ETC}/ms.conf
fi

if grep -q -i "release 6" /etc/redhat-release
then
    cat ${SHARE}/periscoped.supervisor.conf >> /etc/supervisord.conf
    cp ${SHARE}/periscoped /etc/init.d/periscoped
    chmod +x /etc/init.d/periscoped
    chown root:root /etc/init.d/periscoped
    chkconfig --add periscoped
elif grep -q -i "release 7" /etc/redhat-release
then
    cp ${SHARE}/periscoped.supervisor.conf /etc/supervisord.d/periscope.ini
    cp ${SHARE}/periscoped.service /etc/systemd/system/periscoped.service
    systemctl daemon-reload
    systemctl enable periscoped
    service supervisord restart
fi
