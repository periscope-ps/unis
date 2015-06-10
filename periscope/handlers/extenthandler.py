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
    
    def post_psjson(self, **kwargs):
        """
        Handles HTTP POST request with Content Type of PSJSON.
        """
        profile = self._validate_psjson_profile()
        run_validate = True
        if self.get_argument("validate", None) == 'false':
            run_validate = False
            
        if not profile:
            return
        try:
            body = json.loads(self.request.body)
        except Exception as exp:
            self.send_error(400, message="malformatted json request '%s'." % exp)
            return
        
        try:
            resources = []
            if isinstance(body, list):
                for item in body:
                    resources.append(self._model_class(item))
            else:
                resources = [self._model_class(body)]
        except Exception as exp:
            self.send_error(400, message="malformatted request " + str(exp))
            return
        
        # Validate schema
        res_refs =[]
        for index in range(len(resources)):
            try:
                item = resources[index]
                item["selfRef"] = "%s/%s" % \
                                  (self.request.full_url().split('?')[0], item[self.Id])
                item["$schema"] = item.get("$schema", self.schemas_single[MIME['PSJSON']])
                if item["$schema"] != self.schemas_single[self.accept_content_type]:
                    self.send_error(400,
                                    message="Not valid body '%s'; expecting $schema: '%s'." % \
                                    (item["$schema"], self.schemas_single[self.accept_content_type]))
                    return
                if run_validate == True:
                    item._validate()
                res_ref = {}
                res_ref[self.Id] = item[self.Id]
                res_ref[self.timestamp] = item[self.timestamp]
                res_refs.append(res_ref)
                resources[index] = dict(item._to_mongoiter())
            except Exception as exp:
                self.send_error(400, message="Not valid body '%s'." % exp)
                return
        
        self._find_exnode(resources)
        
        # PPI processing/checks
        if getattr(self.application, '_ppi_classes', None):
            try:
                for resource in resources:
                    for pp in self.application._ppi_classes:
                        pp.pre_post(resource, self.application, self.request)
            except Exception, msg:
                self.send_error(400, message=msg)
                return

        callback = functools.partial(self.on_post,
                                     res_refs=res_refs, return_resources=True, **kwargs)
        self.dblayer.insert(resources, callback=callback)

        for res in resources:
            self._subscriptions.publish(res)

            
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def _find_exnode(self, allocations):
        query = {}
        query[self.Id] = allocations[0].get("parent")
        
        callback = functools.partial(self._update_exnode, allocations = allocations)
        self.exnode_layer.find(query, callback)

    @tornado.web.asynchronous
    @tornado.web.removeslash
    def _update_exnode(self, response, error, allocations):
        if error:
            self.send_error(500, message = error)
            return
        
        if not response:
            self.send_error(404, message = "Error: No exnode found for this extent.")
            return

        exnode = response[0]
        for alloc in allocations:
            alloc.pop("_id", None)
            exnode["extents"].append(alloc)
        
        query = {}
        query[self.Id] = exnode.get(self.Id)
        
        self.exnode_layer.update(query, exnode, lambda *_, **__: None)



    def put_psjson(self, res_id):
        try:
            body = json.loads(self.request.body)
            resource = self._model_class(body, auto_id = False)
        except Exception as exp:
            self.send_error(400, message="malformed json requenst - {exp}".format(exp = exp))
            return

        try:
            query = { "id": resource["parent"] }
            callback = functools.partial(self._find_exnode_and_update, allocation = resource)
            self._cursor = self.exnode_layer.find(query, callback)
            self._subscriptions.publish(resource)
        except ValueError as exp:
            self.write_error(500, message = "malformed json request - {exp}".format(exp = exp))
            return
        except Exception as exp:
            self.write_error(500, message = exp)
            

    @tornado.web.asynchronous
    @tornado.web.removeslash
    def _find_exnode_and_update(self, response, error, allocation):
        if error:
            self.send_error(500, message = error)
            return
        
        if not response:
            self.send_error(404, message = "Error: No exnode found for this extent.")
            return

        try:
            print response
            exnode = response[0]
        except Exception as exp:
            self.send_error(500, message = exp)
            return
        
        allocations = []
        for alloc in exnode["extents"]:
            if alloc["id"] != allocation["id"]:
                allocations.append(alloc)
            else:
                allocation = dict(alloc.items() + allocation.items())
                allocations.append(allocation)
                break
        
        exnode["extents"] = allocations
        query = {}
        query[self.Id] = response[0].get(self.Id)
        
        
        callback = functools.partial(self._finish_put, allocation = allocation)
        self.exnode_layer.update(query, exnode, callback)


    def _finish_put(self, response, error, allocation):
        if error:
            self.send_error(500, message = error)
            return

        res_ref = {}
        res_ref[self.Id] = allocation[self.Id]
        res_ref[self.timestamp] = allocation[self.timestamp]
        query = {}
        query[self.Id] = allocation[self.Id]
        callback = functools.partial(self.on_put, res_ref= res_ref, 
            return_resource=True)
        self.dblayer.update(query, allocation, callback=callback)
