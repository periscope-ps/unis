#!/usr/bin/env python
"""
Databases related classes
"""
import time
import functools
import settings
import tornado.gen
import json
from json import JSONEncoder
from netlogger import nllog
from settings import DB_AUTH

from periscope.models import ObjectDict

from bson.objectid import ObjectId
from bson.json_util import dumps

AuthField = DB_AUTH['auth_field']
AuthDefault = DB_AUTH['auth_default']

dumps_mongo = dumps

class MongoEncoder(JSONEncoder):
    """Special JSON encoder that converts Mongo ObjectIDs to string"""
    def _iterencode(self, obj, markers=None):
        if isinstance(obj, ObjectId):
            return """ObjectId("%s")""" % str(obj)
        else:
            return JSONEncoder._iterencode(self, obj, markers)

class DBLayer(object, nllog.DoesLogging):
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
        nllog.DoesLogging.__init__(self)
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

    @tornado.gen.coroutine
    def find_one(self, query = {}, **kwargs):
        self.log.debug("find one for Collection: [" + self._collection_name + "]")
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
        result = yield self.collection.find_one(query, fields=fields, **kwargs)

        raise tornado.gen.Return(result)
    
    def find(self, query = {}, **kwargs):
        """Finds one or more elements in the collection."""
        self.log.debug("find for Collection: [" + self._collection_name + "]")
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
        cursor = self.collection.find(query, fields=fields, **kwargs)
        
        return cursor
    
    def _insert_id(self, data):
        if "_id" not in data and not self.capped:
            res_id = data.get(self.Id, str(ObjectId()))
            timestamp = data.get(self.timestamp, int(time.time() * 1000000))
            data["_id"] = "%s:%s" % (res_id, timestamp)
    
    @tornado.gen.coroutine
    def insert(self, data, callback=None, summarize=True, **kwargs):
        """Inserts data to the collection."""
        shards = []
        self.log.debug("insert for Collection: [" + self._collection_name + "]")
        if isinstance(data, list) and not self.capped:
            for item in data:
                if summarize:
                    shards.append(self._create_manifest_shard(item))
                self._insert_id(item)
        elif not self.capped:
            if summarize:
                shards.append(self._create_manifest_shard(data))
            self._insert_id(data)

        yield self.manifest.insert(shards)
        results = yield self.collection.insert(data, callback=callback, **kwargs)
        
        raise tornado.gen.Return(results)
    
    
    @tornado.gen.coroutine
    def update(self, query, data,cert=None, replace = False, summarize = True, **kwargs):
        """Updates data found by query in the collection."""
        self.log.debug("Update for Collection: [" + self._collection_name + "]")
        if summarize:
            shard = self._create_manifest_shard(data)
            yield self.manifest.insert(shard)
        if not replace:
            data = { "$set": data }
        results = yield self.collection.update(query, data, **kwargs)
        raise tornado.gen.Return(results)
    
    @tornado.gen.coroutine
    def remove(self, query, callback=None, **kwargs):
        """Remove objects from the database that matches a query."""
        self.log.debug("Delete for Collection: [" + self._collection_name + "]")
        results = yield self.collection.remove(query, callback=callback, **kwargs)
        
        raise tornado.gen.Return(results)
    
    @tornado.gen.coroutine
    def getRecParentNames(self,par,pmap):
        """ Gets all the child folder ids recurssively for a given folder - specially for exnodes"""
        if par :
            cursor = self.collection.find({"parent" : par,"mode":"directory"})
            self.log.debug("find for Collection: [" + self._collection_name + "]")
            pmap[par] = 1
            while (yield cursor.fetch_next):
                resource = cursor.next_object()
                if resource == None:                 
                    pass
                else:
                    pmap[resource.get('id')] = 1
                yield self.getRecParentNames(resource.get('id'),pmap)
            raise tornado.gen.Return(pmap.keys())
        else:          
            raise tornado.gen.Return(None)
        
    def _create_manifest_shard(self, resource):
        if "\\$collection" in resource:
            tmpResource = resource["properties"]
        else:
            tmpResource = resource
        tmpResult = {}
        tmpResult["properties"] = self._flatten_shard(tmpResource)
        tmpResult["$shard"] = True
        tmpResult["$collection"] = self._collection_name
        return dict(ObjectDict(tmpResult)._to_mongoiter())
    
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
