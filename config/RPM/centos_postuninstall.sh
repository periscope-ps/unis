USER=periscope
SERVICE=periscoped
HOME=/var/lib/periscope
SHARE=/usr/share/periscope
LOG=/var/log/periscoped.log

if grep -q -i "release 6" /etc/redhat-release
then
    chkconfig --del ${SERVICE}
    rm -f /etc/init.d/${SERVICE}
elif grep -q -i "release 7" /etc/redhat-release
then
    systemctl disable ${SERVICE}
    rm -f /etc/systemd/system/${SERVICE}.service
    systemctl daemon-reload
fi

service ${SERVICE} stop
userdel ${USER}
