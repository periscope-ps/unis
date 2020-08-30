# =============================================================================
#  periscope-ps (unis)
#
#  Copyright (c) 2012-2016, Trustees of Indiana University,
#  All rights reserved.
#
#  This software may be modified and distributed under the terms of the BSD
#  license.  See the COPYING file for details.
#
#  This software was created at the Indiana University Center for Research in
#  Extreme Scale Technologies (CREST).
# =============================================================================
#!/bin/bash

USER=periscope
ETC=/etc/periscope
HOME=/var/lib/periscope
SVDIR=/etc/supervisor
SHARE=/usr/share/periscope

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
