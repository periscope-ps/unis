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

"""
Databases related classes
"""
import time
import functools
import json
from periscope import settings
from json import JSONEncoder
from bson.objectid import ObjectId


class MongoEncoder(JSONEncoder):
    """Special JSON encoder that converts Mongo ObjectIDs to string"""
    def _iterencode(self, obj, markers=None):
        if isinstance(obj, ObjectId):
            return """ObjectId("%s")""" % str(obj)
        else:
            return JSONEncoder._iterencode(self, obj, markers)

class DBLayer(object):
    """Thin layer asynchronous model to handle network objects.

    Right now this layer doesn't do much, but provides away to intercept
    the database calls for any future improvements or updates.

    Unfortuantly uncapped collections in Mongo must have a uniqe '_id'
    field, so this layer will generate one for each insert based on the
    network resource id and the revision number.
    """
    
    def __init__(self, client, collection_name, capped=False, Id="id", \
        timestamp="ts"):
        """Intializes with a reference to the mongodb collection."""
        self.log = settings.get_logger()
        self.Id = Id
        self.timestamp = timestamp
        self.capped = capped
        self._collection_name = collection_name
        self._client = client
    
    @property
    def collection(self):
        """Returns a reference to the default mongodb collection."""
        return self._client[self._collection_name]
    
    @property
    def manifest(self):
        """Returns a reference to the manifest collection"""
        return self._client["manifests"]

    def find_one(self, query = {}, **kwargs):
        self.log.debug("find one for Collection: [" + self._collection_name + "]")
        
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
        result = self.collection.find_one(query, fields, **kwargs)

        return result
    
    def find(self, **kwargs):
        query = kwargs.pop("query", {})
        
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
    
        return self._client[self._collection_name].find(query, fields, **kwargs)

    def update(self, query, data, cert=None, replace=False, summarize=True, **kwargs):
        """Updates data found by query in the collection."""
        self.log.debug("Update for Collection: [" + self._collection_name + "]")
        if not replace:
            data = { "$set": data }
        futures =  [self.collection.find_and_modify(query, data, upsert=False, **kwargs)]

        if summarize:
            shard = self._create_manifest_shard(data, self._collection_name)
            sfut = self.manifest.insert(shard)
            futures.append(sfut)
        results = futures
        
        for r in results:
            if isinstance(r, dict) and not r.get("updatedExisting", True):
                raise(LookupError("Resource ID does not exist"))
        return results
    
    def remove(self, query, callback=None, **kwargs):
        """Remove objects from the database that matches a query."""
        self.log.debug("Delete for Collection: [" + self._collection_name + "]")
        results = self.collection.remove(query, callback=callback, **kwargs)
        return results
    
    def getRecParentNames(self, par, pmap):
        """ Gets all the child folder ids recursively for a given folder
            (exnode specific)"""
        if par:
            cursor = self.collection.find({"name": par, "mode": "directory"})
            self.log.debug("find for Collection: [" + self._collection_name + "]")
            pmap[par] = 1
            for resource in cursor:
                if resource == None:
                    pass
                else:
                    pmap[resource.get('id')] = 1
                self.getRecParentNames(resource.get('id'), pmap)
            return pmap.keys()
        else:          
            return None
    
    
    def _insert_id(self, data):
        if "_id" not in data and not self.capped:
            res_id = data.get(self.Id, str(ObjectId()))
            timestamp = data.get(self.timestamp, int(time.time() * 1000000))
            data["_id"] = "%s:%s" % (res_id, timestamp)
    
    def insert(self, data, collection, callback=None, summarize=True, **kwargs):
        """Inserts data to the collection."""
        
        self.capped = False
        self.manifests = "manifests"
                
        shards = []
        if isinstance(data, list) and not self.capped:
            for item in data:
                if summarize:
                    shards.append(self._create_manifest_shard(item, collection))
                self._insert_id(item)
        elif not self.capped:
            if summarize:
                shards.append(self._create_manifest_shard(data, collection))
            self._insert_id(data)

        futures = [self._client[collection].insert(data, **kwargs)]
        if summarize:
            futures.append(self._client[self.manifests].insert(shards))
        results = futures

        return results
   
    def _create_manifest_shard(self, resource, collection):
        if "\\$collection" in resource:
            tmpResource = resource["properties"]
        else:
            tmpResource = resource
        tmpResult = {}
        tmpResult["properties"] = self._flatten_shard(tmpResource)
        tmpResult["$shard"] = True
        tmpResult["$collection"] = collection
        from periscope.models import ObjectDict
        mongoObj = dict(ObjectDict(tmpResult)._to_mongoiter())
        return mongoObj
    
    def _flatten_shard(self, resource):
        tmpResults = {}
        for key, value in resource.items():
            if type(value) == dict:
                tmpInner = self._flatten_shard(value)
                for k_i, v_i in tmpInner.items():
                    tmpResults["{key}.{inner}".format(key = key, inner = k_i)] = v_i
            elif type(value) == list:
                tmpResults[key] = value
            else:
                tmpResults[key] = [value]
                
        return tmpResults


