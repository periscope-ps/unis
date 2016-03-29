USER=periscope
SERVICE=periscoped
HOME=/var/lib/periscope
SHARE=/usr/share/periscope
LOG=/var/log/periscoped.log

service ${SERVICE} stop

if grep -q -i "release 6" /etc/redhat-release
then
    chkconfig --del ${SERVICE}
    rm -f /etc/init.d/${SERVICE}
elif grep -q -i "release 7" /etc/redhat-release
then
    if [ "$1" = "0" ]; then
        # Prepare task for an uninstallation
        systemctl disable ${SERVICE}
        rm -f /etc/systemd/system/${SERVICE}.service
    fi
    systemctl daemon-reload
fi
