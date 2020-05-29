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
import functools
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient
import tornado.web
import tornado.gen

import periscope.settings as settings
from periscope.settings import MIME
from .collectionhandler import CollectionHandler
from periscope.db import dumps_mongo

class FolderHandler(tornado.web.RequestHandler):
    def initialize(self, dblayer,base_url):
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
        
class ExnodeHandler(CollectionHandler):
    @tornado.gen.coroutine
    def _post_get(self, resource, inline=False):
        if not inline or resource.get("mode", None) == "directory":
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
