#!/usr/bin/env python

import tornado.web
import copy
import json
import functools
import time
from tornado.httpclient import AsyncHTTPClient
from asyncmongo.errors import IntegrityError
import tornado.gen

import periscope.settings as settings
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class EventsHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _insert(self, resources):
        resource = resources[0]
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch(resource["metadata_URL"],
                                           validate_cert=False,
                                           client_cert=settings.MS_CLIENT_CERT,
                                           client_key=settings.MS_CLIENT_KEY)
        
        if response.error:
            self.send_error(400, message="metadata is not found '%s'." % response.error)
        else:
            body = json.loads(response.body)[0]
            collections = yield self.application.db.collection_names()
            if body[self.Id] not in collections:
                self.application.get_db_layer(body[self.Id], "ts", "ts", True, resource["collection_size"])
                self.set_header("Location","%s/data/%s" % (self.request.full_url().split('?')[0], body[self.Id]))
                resource[self.timestamp] = int(time.time() * 1000000)
                resource[self.Id] = body[self.Id]
                yield self.dblayer.insert(resource)
            else:
                raise ValueError("event collection exists already")
            
    def _find(self, **options):
        options["query"].pop("status", None)
        if not options["query"]:
            return self.dblayer.find()
        elif self.Id in options["query"] or "$or" in options["query"]:
            return self.dblayer.find(**options)
        else:
            self._query = options["query"]
            return None
            
    @tornado.gen.coroutine
    def _add_response_headers(self, cursor):
        count = 1
        accept = self.accept_content_type
        self.set_header("Content-Type", accept + "; profile=" + self.schemas_single[accept])
        
        raise tornado.gen.Return(count)

    @tornado.gen.coroutine
    def _write_get(self, cursor, is_list = False):
        response = []
        if cursor:
            count = yield cursor.count()
            if not count:
                self.write('[]')
                raise tornado.gen.Return(count)
        
            while (yield cursor.fetch_next):
                resource = cursor.next_object()
                mid = resource["metadata_URL"].split('/')[resource["metadata_URL"].split('/').__len__() - 1]
                try:
                    res = yield self.generate_response(mid)
                except ValueError as exp:
                    raise ValueError(exp)
                response.insert(0, res)
        else:
            count = 0
            for d in self._query["$and"]:
                if 'mids' in d.keys():
                    if isinstance(d["mids"],dict):
                        for m in d['mids']['$in']:
                            try:
                                res = yield self.generate_response(m)
                            except ValueError as exp:
                                raise ValueError(exp)
                            count += 1
                            response.insert(0, res)
                    else:
                        try:
                            res = yield self.generate_response(d['mids'])
                        except ValueError as exp:
                            raise ValueError(exp)
                        count += 1
                        response.insert(0, res)
                        
        json_response = dumps_mongo(response, indent=2)
        self.write(json_response)
        raise tornado.gen.Return(count)
        
    @tornado.gen.coroutine
    def _return_resoures(self, query):
        try:
            cursor = self.dblayer.find(query)
            while (yield cursor.fetch_next):
                resource = cursor.next_object()
                self._subscriptions.publish(resource, self._collection_name)
        except Exception as exp:
            raise ValueError(exp)
        
        
    def del_stat_fields(self,generic):
        generic.pop("ns",None)
        generic.pop("numExtents",None)
        generic.pop("nindexes",None)
        generic.pop("lastExtentSize",None)
        generic.pop("paddingFactor",None)
        generic.pop("flags",None)
        generic.pop("totalIndexSize",None)
        generic.pop("indexSizes",None)
        generic.pop("max",None)
        generic.pop("ok",None)
        if generic["capped"] == 1:
            generic["capped"]="Yes"
        else:
            generic["capped"]="No"
            
    @tornado.gen.coroutine
    def generate_response(self, mid):
        tmpReponse = None
        try:
            command={"collStats": mid,"scale":1}
            generic = yield self.application.db.command(command)
        except Exception as exp:
            raise ValueError("At least one of the metadata ID is invalid.")
            raise tornado.gen.Return(None)
        
        self.del_stat_fields(generic)
        specific={}
        if 'ts' in self.request.arguments.keys():
            criteria = self.request.arguments['ts'][0].split('=')
            
            if criteria[0] == 'gte':
                specific["startTime"] = int(criteria[1])
            if criteria[0] == 'lte':
                specific["endTime"] = int(criteria[1])
            
            if self.request.arguments['ts'].__len__() > 1 :            
                criteria = self.request.arguments['ts'][1].split('=')
                if criteria[0] == 'gte':
                    specific["startTime"] = int(criteria[1])
                if criteria[0] == 'lte':
                    specific["endTime"] = int(criteria[1])
            
            db_query = {"ts": { "$gt": 0 } }
            if startTime in specific:
                db_query["ts"]["$gte"] = specific["startTime"]
            if endTime  in specific:
                db_query["ts"]["$lte"] = specific["endTime"]
            specific["numRecords"] = yield self.application.db[mid].find(db_query).count()
            
        raise tornado.gen.Return({ "mid": mid, "generic": generic, "queried": specific })
    
