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
import time
import functools
import periscope.settings as settings
from periscope.settings import MIME
from periscope.handlers.collectionhandler import CollectionHandler
        
class ExnodeHandler(CollectionHandler):
    def _post_get(self, resource, inline=False):
        
        if not inline or resource.get("mode", None) == "directory":
            return resource
        
        try:
            extents = self._get_extents(resource["selfRef"])
            
            resource["extents"] = extents
        except Exception as exp:
            raise Exception("Could not load extent data - {exp}".format(exp = exp))
        
        return resource
    
    def _get_extents(self, parent):
        fields = {}
        fields["_id"] = 0

        data = self._mongo.unis_db["extents"].find({"parent.href" : parent}, fields)
        extents = []
        
        for resource in data:
          extents.append(resource)
        
        return extents
