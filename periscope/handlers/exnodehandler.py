#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
import tornado.web


import periscope.settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class ExnodeHandler(NetworkResourceHandler):
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
        self.extent_layer = collections["extents"]
        self.extent_model = models["extents"]
        super(ExnodeHandler, self).initialize(dblayer=dblayer, base_url=base_url, Id=Id, timestamp=timestamp, 
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
        
        resource = json.loads(self.request.body)
        if resource["mode"] == "directory":
            query = {}
            query["parent"] = resource["parent"]
            query["name"]   = resource["name"]
            callback = functools.partial(self._on_get_siblings, _candidateExnode = self.request)
            self._cursor = self.dblayer.find(query, callback)
        else:
            try:
                extents  = resource["extents"]
                self.request.body = json.dumps(resource)
                self.post_psjson(extents = extents)
            except Exception as exp:
                self.write_error(500, message = exp)
        
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def _on_get_siblings(self, response, error, _candidateExnode = None):
        if error:
            self.send_error(500, message = error)
            return

        if response:
            # There is already an exnode sibling with that name
            # Get the Id of the old exnode and update the content
            #  with the content of the new exnode
            body     = json.loads(_candidateExnode.body)
            resource = self._model_class(body)
            
            res_id = response[0].get(self.Id)
            resource["$schema"]  = response[0].get("$schema", self.schemas_single[MIME['PSJSON']])
            resource["selfRef"]  = response[0].get("selfRef")
            resource["modified"] = resource[self.timestamp]
            resource[self.Id]    = response[0].get("id")
            res_refs = []
            ref = {}
            ref[self.Id] = res_id
            ref[self.timestamp] = resource[self.timestamp]
            res_refs.append(ref)
            resource = dict(resource._to_mongoiter())
            
            query = {}
            query[self.Id] = res_id
            
            callback = functools.partial(self.on_post, res_refs = res_refs, return_resources = True, extents = [])
            self.dblayer.update(query, resource, callback = callback)
            self._subscriptions.publish(resource)
        else:
            # This is a unique exnode
            # Execute normal post
            self.request = _candidateExnode
            self.post_psjson()

    def on_post(self, request, error=None, res_refs=None, return_resources=True, **kwargs):
        try:
            if "extents" in kwargs and len(kwargs["extents"]) > 0:
                extents = []
                
                for extent in kwargs["extents"]:
                    tmpExtent = self.extent_model(extent)
                    tmpExtent["parent"] = res_refs[0]["id"]
                    tmpExtent["selfRef"] = "%s/%s/%s" % (self.request.full_url().split('?')[0].rsplit('/', 1)[0],
                                                     "extents",
                                                     tmpExtent[self.Id])
                    mongo_extent = dict(tmpExtent._to_mongoiter())
                    extents.append(mongo_extent)
                    self._subscriptions.publish(mongo_extent)
                
                self.extent_layer.insert(extents, lambda *_, **__: None)
        except Exception as exp:
            print exp
            self.send_error(400, message="decode: could not decode extents")
            return
            
        super(ExnodeHandler, self).on_post(request = request, error = error, res_refs = res_refs, return_resources = return_resources, **kwargs)
