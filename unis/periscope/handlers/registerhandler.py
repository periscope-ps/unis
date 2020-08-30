#!/usr/bin/env python
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

import json
from periscope import settings
from periscope.settings import MIME, get_db_layer
from periscope.models import Manifest, ObjectDict
from periscope.handlers.networkresourcehandler import NetworkResourceHandler

class RegisterHandler(NetworkResourceHandler):
    def _insert(self, resources, collection):
        accessPoint = resources[0]["accessPoint"]
        tmpExists = self.dblayer.find_one({ "accessPoint": accessPoint })
        if tmpExists:
            self.dblayer.update({ "accessPoint": accessPoint }, resources[0], replace = True, multi=False)
        else:
            self.dblayer.insert(resources)
        
        for manifest in resources[0]["properties"]["summary"]:
            manifest = ObjectDict._from_mongo(manifest)
            manifest["href"] = accessPoint
            manifest["ttl"] = resources[0]["ttl"]
            manifest.pop(self.timestamp, 0)
            self._update_manifest(manifest, accessPoint)
        
    def _update_manifest(self, manifest, source):
        tmpDB = get_db_layer(manifest["$collection"], self.Id, self.timestamp, False, 0)
        tmpManifest = tmpDB.find_one({ "href": source })
        mongoManifest = dict(Manifest(manifest)._to_mongoiter())
        
        if tmpManifest:
            tmpDB.update({ "href": source }, mongoManifest, replace = True)
        else:
            tmpDB.insert(mongoManifest)

