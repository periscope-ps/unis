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

import falcon
from periscope.handlers.collectionhandler import CollectionHandler

def initialize(req, resp, resource, params):
    resource._dblayer = get_db_layer(resourceObj["collection_name"], 
                                    resourceObj["id_field_name"],
                                    resourceObj["timestamp_field_name"],
                                    resourceObj["is_capped_collection"],
                                    resourceObj["capped_collection_size"])

class FolderHandler(object):
    @falcon.before(initialize)
    def on_get(self, req, resp, res_id=None):
        par = req.get_param("parent", default=None)
        val = self._dblayer.getRecParentNames(par)
        #self.log.info("Getting recurrsive folder ids for: [" + self._dblayer._collection_name + "]" + " with Parent " + par)
        buf = []
        if (val != None):
            buf = val
        resp.set_header('Content-Type', 'application/json')        
        resp.body = json.dumps(buf, indent=4)

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
