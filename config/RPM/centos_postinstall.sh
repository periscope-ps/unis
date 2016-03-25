#!/bin/bash

USER=periscope
HOME=/var/lib/periscope
SVDIR=/etc/supervisor
SHARE=/usr/share/pariscope
LOG=/var/log/periscope.log

/usr/bin/getent group ${USER} || /usr/sbin/groupadd -r ${USER}
/usr/bin/getent passwd ${USER} || /usr/sbin/useradd -r -d ${HOME} -s /sbin/nologin -g ${USER} ${USER}

if [ ~ -d ${HOME} ]; then
    mkdir ${HOME}
fi

if [ ~ -d ${SVDIR}/conf.d ]; then
    mkdir ${SVDIR}/conf.d
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
