#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient
import tornado.web
import tornado.gen

import periscope.settings as settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class ExnodeHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _process_resource(self, resource, res_id = None, run_validate = True):
        resource = yield super(ExnodeHandler, self)._process_resource(resource, res_id, run_validate)
        if resource["mode"] == "directory":
            query = { "parent": resource["parent"], "name": resource["name"] }
            cursor = self.dblayer.find(query)
            
            count = yield cursor.count()
            if count:
                yield cursor.fetch_next
                oldResource = cursor.next_object()
                resource["$schema"]  = oldResource.get("$schema", self.schemas_single[MIME['PSJSON']])
                resource["selfRef"]  = oldResource["selfRef"]
                resource["modified"] = resource[self.timestamp]
                resource[self.timestamp] = oldResource[self.timestamp]
                resource[self.Id]        = oldResource[self.Id]
            else:
                resource.pop("modified", None)
        else:
            print resource["extents"]
            yield [ self._insert_extents(extent, resource[self.Id]) for extent in resource["extents"] ]
            resource.pop("extents", None)
            resource.pop("modified", None)
            
        raise tornado.gen.Return(resource)
    
    
    
    def _insert_extents(self, extent, parent):
        http_client = AsyncHTTPClient()
        extent["parent"] = parent
        url = "{protocol}://{host}/extents"
        return tornado.gen.Task(
            http_client.fetch,
            url.format(protocol = self.request.protocol,
                       host     = self.request.host),
            method = "POST",
            body   = dumps_mongo(extent),
            request_timeout = 180,
            validate_cert = False,
            client_cert     = settings.CLIENT_SSL_OPTIONS['certfile'],
            client_key      = settings.CLIENT_SSL_OPTIONS['keyfile'],
            headers         = { "Cache-Control": "no-cache",
                                "Content-Type": MIME["PSJSON"],
                                "connection": "close" }
        )
    
    @tornado.gen.coroutine
    def _insert(self, resources):
        yield [ self.dblayer.update( { self.Id: resource[self.Id] }, resource) if "modified" in resource else self.dblayer.insert(resource) for resource in resources ]
        
    def _find(self, **kwargs):
        self._include_allocations = True
        if "fields" in kwargs and kwargs["fields"]:
            if "extents" not in kwargs["fields"]:
                self._include_allocations = False
            else:
                kwargs["fields"]["mode"] = True
        
        return super(ExnodeHandler, self)._find(**kwargs)
            
    @tornado.gen.coroutine
    def _post_get(self, resource):
        if not self._include_allocations or resource["mode"] == "directory":
            raise tornado.gen.Return(resource)
        
        try:
            extents = yield self._get_extents(resource[self.Id])
            resource["extents"] = json.loads(extents.body)
        except Exception as exp:
            raise Exception("Could not load extent data - {exp}".format(exp = exp))
        
        raise tornado.gen.Return(resource)
    
    def _get_extents(self, parent):
        http_client = AsyncHTTPClient()
        url = "{protocol}://{host}/extents?parent={parent}"
        return tornado.gen.Task(
            http_client.fetch,
            url.format(protocol = self.request.protocol,
                       host     = self.request.host,
                       parent   = parent),
            method = "GET",
            request_timeout = 180,
            validate_cert = False,
            client_cert     = settings.CLIENT_SSL_OPTIONS['certfile'],
            client_key      = settings.CLIENT_SSL_OPTIONS['keyfile'],
            headers         = { "Cache-Control": "no-cache",
                                "Content-Type": MIME["PSJSON"],
                                "connection": "close" }
        )
    
    
    @tornado.gen.coroutine
    def _put_resource(self, resource):
        resource.pop("extents", None)
        super(ExnodeHandler, self)._put_resource(resource)
