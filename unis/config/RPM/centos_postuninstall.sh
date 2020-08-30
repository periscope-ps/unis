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
USER=periscope
SERVICE=periscoped
HOME=/var/lib/periscope
SHARE=/usr/share/periscope
LOG=/var/log/periscoped.log

service ${SERVICE} stop

if grep -q -i "release 6" /etc/redhat-release
then
    if [ "$1" = "0" ]; then
      # Remove the SERVICE from the startup list
      chkconfig --del ${SERVICE}
      rm -f /etc/init.d/${SERVICE}
    fi
elif grep -q -i "release 7" /etc/redhat-release
then
    if [ "$1" = "0" ]; then
        # Prepare task for an uninstallation
        systemctl disable ${SERVICE}
        rm -f /etc/systemd/system/${SERVICE}.service
    fi
    systemctl daemon-reload
fi
