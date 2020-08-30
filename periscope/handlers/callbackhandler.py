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

from time import sleep
from pymongo import MongoClient
from periscope.settings import Resources, get_logger, DEFAULT_CONFIG
from periscope.models import Manifest
        
class CallbackHandler(object):
    def _aggregate_manifests(self, summary_size):
        def _trim_fields(resource, fields):
            resource.pop("_id", None)
            return resource
        
        def add_key(key, value, manifest, log):
            if key not in ["ts", "id", "_id", "\\$shard", "\\$collection"]:
                try:
                    prev = manifest["properties"][key] if key in manifest["properties"] else []
                    if prev == "*" or value == "*" or len(value) + len(prev) > summary_size:
                        prev = "*"
                    elif len(value) > 0 and type(value[0]) == dict:
                        prev += value
                    else:
                        prev = list(set(prev) | set(value))
                    manifest["properties"][key] = prev
                except Exception as exp:
                    log.error("Bad value in shard - {exp}".format(exp = exp))
        
        self.log = get_logger()
        mongo = MongoClient('localhost', 27017)
        
        collections = set()
        for key, collection in Resources.items():
            if collection["collection_name"]:
                collections.add(collection["collection_name"])
            
        for collection in collections:
            newManifest = { "$shard": False, "$collection": collection, "properties": {} }
            modified    = False
            shards      = mongo.unis_db["manifests"].find({ "\\$shard": True, "\\$collection": collection }, {'_id': False, "\\$shard": False, "\\$collection": False })
            manifest    = mongo.unis_db["manifests"].find_one({ "\\$shard": False, "\\$collection": collection })
            
            for shard in shards:
                modified = True
                #shard = shards.next_object()
                for key, value in shard["properties"].items():
                    add_key(key, value, newManifest, self.log)
                    
            if manifest:
                for key, value in manifest["properties"].items():
                    add_key(key, value, newManifest, self.log)
                    
            tmpManifest = dict(Manifest(newManifest)._to_mongoiter())
            if not manifest:
                mongo.unis_db["manifests"].insert(tmpManifest)
            else:
                tmpManifest["id"] = manifest["id"]
                mongo.unis_db["manifests"].update({ "\\$collection": collection }, tmpManifest)
        
        mongo.unis_db["manifests"].remove({ "\\$shard": True })
        
    def on_get(self, req, resp):
    
        self._aggregate_manifests(DEFAULT_CONFIG["unis"]["summary_size"])
