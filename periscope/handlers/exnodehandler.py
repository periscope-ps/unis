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
#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
from netlogger import nllog
from tornado.httpclient import AsyncHTTPClient
import tornado.web
import tornado.gen

import periscope.settings as settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo

class FolderHandler(tornado.web.RequestHandler,nllog.DoesLogging):
    def initialize(self, dblayer,base_url):
        nllog.DoesLogging.__init__(self)
        self._dblayer = dblayer
        
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self,res_id=None):
        par = self.get_argument("parent",default=None)
        val = yield self._dblayer.getRecParentNames(par)
        self.log.info("Getting recurrsive folder ids for: [" + self._dblayer._collection_name + "]" + " with Parent " + par)
        if (val == None):
            self.write(json.dumps([]))
        else:
            self.write(json.dumps(val))
        self.set_header('Content-Type', 'application/json')
        self.finish()
        
class ExnodeHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _process_resource(self, resource, res_id = None, run_validate = True):
        resource = yield super(ExnodeHandler, self)._process_resource(resource, res_id, run_validate)
        self.modified = False
        
        if resource["mode"] == "directory":
            parent = None
            if resource["parent"]:
                parent = resource["parent"]["href"]
            query = { "parent.href": parent, "name": resource["name"] }
            cursor = self.dblayer.find(query)
            
            count = yield cursor.count()
            if count:
                yield cursor.fetch_next
                oldResource = cursor.next_object()
                resource["$schema"]  = oldResource.get("$schema", self.schemas_single[MIME['PSJSON']])
                resource["selfRef"]  = oldResource["selfRef"]
                resource["modified"] = oldResource[self.timestamp]
                resource[self.timestamp] = oldResource[self.timestamp]
                resource[self.Id]        = oldResource[self.Id]
                self.modified = True
        else:
            yield [ self._insert_extents(extent, resource["selfRef"]) for extent in resource["extents"] ]
            resource.pop("extents", None)

        resource["modified"] = resource.get("modified", resource.get(self.timestamp, 0))
        raise tornado.gen.Return(resource)
    
    def _insert_extents(self, extent, parent):
        http_client = AsyncHTTPClient()
        extent["parent"] = {"href": parent,
                            "rel": "full"}
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
        try:
            self._subscriptions.publish(resources, self._collection_name, { "action": "POST" })
            yield [ self.dblayer.update( { self.Id: resource[self.Id] }, resource) 
                    if self.modified 
                    else self.dblayer.insert(resource) for resource in resources ]
        except Exception as exp:
            raise exp
        
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
        if not self._include_allocations or resource.get("mode", None) == "directory":
            raise tornado.gen.Return(resource)
        
        try:
            extents = yield self._get_extents(resource["selfRef"])
            resource["extents"] = json.loads(extents.body)
        except Exception as exp:
            raise Exception("Could not load extent data - {exp}".format(exp = exp))
        
        raise tornado.gen.Return(resource)
    
    def _get_extents(self, parent):
        http_client = AsyncHTTPClient()
        url = "{protocol}://{host}/extents?parent.href={parent}"
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
        try:
            resource.pop("extents", None)
            yield super(ExnodeHandler, self)._put_resource(resource)
        except Exception as exp:
            raise exp
