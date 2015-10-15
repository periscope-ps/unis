#!/usr/bin/env python
"""
Databases related classes
"""
import time
import functools
import settings
import tornado.gen
from json import JSONEncoder
from netlogger import nllog
from settings import DB_AUTH

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
    
    @tornado.gen.coroutine
    def find(self, query, callback=None, ccallback = None,**kwargs):
        """Finds one or more elements in the collection."""
        self.log.info("find for Collection: [" + self._collection_name + "]")
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
        cursor = yield self.collection.find(query, fields=fields, **kwargs)
        if ccallback:
            self._client['$cmd'].find_one({'count' : self._collection_name , 'query' : query}, _is_command=True, callback=ccallback)
        
        raise tornado.gen.Return(findCursor)
    
    def _insert_id(self, data):
        if "_id" not in data and not self.capped:
            res_id = data.get(self.Id, str(ObjectId()))
            timestamp = data.get(self.timestamp, int(time.time() * 1000000))
            data["_id"] = "%s:%s" % (res_id, timestamp)

    @tornado.gen.coroutine
    def insert(self, data, callback=None, **kwargs):
        """Inserts data to the collection."""
        self.log.info("insert for Collection: [" + self._collection_name + "]")
        if isinstance(data, list) and not self.capped:
            for item in data:
                self._insert_id(item)
        elif not self.capped:
            self._insert_id(data)
        results = yield self.collection.insert(data, callback=callback, **kwargs)
        
        raise tornado.gen.Return(results)


    @tornado.gen.coroutine
    def update(self, query, data,cert=None, callback=None, **kwargs):
        """Updates data found by query in the collection."""
        self.log.info("Update for Collection: [" + self._collection_name + "]")
        results = yield self.collection.update(query, data, callback=callback, **kwargs)
        
        raise tornado.gen.Return(results)
    

    @tornado.gen.coroutine
    def remove(self, query, callback=None, **kwargs):
        """Remove objects from the database that matches a query."""
        self.log.info("Delete for Collection: [" + self._collection_name + "]")
        results = yield  self.collection.remove(query, callback=callback, **kwargs)
        
        raise tornado.gen.Return(results)
