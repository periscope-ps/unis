#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
import tornado.web


from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class ExtentHandler(NetworkResourceHandler):
    def initialize(self, dblayer, base_url,
                   Id="id",
                   timestamp="ts",
                   schemas_single=None,
                   schemas_list=None,
                   allow_get=False,
                   allow_post=True,
                   allow_put=True,
                   allow_delete=True,
                   tailable=False,
                   model_class=None,
                   accepted_mime=[MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML']],
                   content_types_mime=[MIME['SSE'], MIME['PSJSON'],
                                       MIME['PSBSON'], MIME['PSXML'], MIME['HTML']],
                   collections={},
                   models={}):
        self.exnode_layer = collections["exnodes"]
        self.exnode_model = models["exnodes"]
        super(ExtentHandler, self).initialize(dblayer=dblayer, base_url=base_url, Id=Id, timestamp=timestamp, 
                                              schemas_single=schemas_single, schemas_list=schemas_list,
                                              allow_get=allow_get, allow_post=allow_post, allow_put=allow_put,
                                              allow_delete=allow_delete, tailable=tailable, model_class=model_class,
                                              accepted_mime=accepted_mime, content_types_mime=content_types_mime)
    
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def post(self, res_id=None):
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defined for content of type '%s'" % (self.accept_content_type)
            self.send_error(500, message = message)
            return
        
        if res_id:
            message = "NetworkResource ID should not be defined."
            self.send_error(500, message = message)
            return
        
        try:
            resource = json.loads(self.request.body)
            query = { "id": resource["parent"] }
            callback = functools.partial(self._find_and_update_exnode,
                                         extent = resource)
            self._cursor = self.exnode_layer.find(query, callback)
        except Exception as exp:
            self.write_error(500, message = exp)

        
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def _find_and_update_exnode(self, response, error, extent):
        if error:
            self.send_error(500, message = error)
            return

        if not response:
            self.send_error(404, message = "Error: No exnode found for this extent.")
            return
            
        response[0].get("extents").append(extent)
        query = {}
        query[self.Id] = response[0].get(self.Id)

        self.exnode_layer.update(query, response[0], callback = self._do_post)

    def _do_post(self, response, error):
        if error:
            self.send_error(500, message = error)
            return

        self.post_psjson()
