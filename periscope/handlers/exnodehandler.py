#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
import tornado.web


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
        self.allocation_layer = collections["extents"]
        self.allocation_model = models["extents"]
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
        
        try:
            if self.request.body.endswith('}') or self.request.body.endswith('}'):
                resource = json.loads(self.request.body)
            else:
                end = self.request.body.rfind("}") + 1
                resource = json.loads(self.request.body[:end])
        except Exception as exp:
            self.send_error(500, message = "Could not parse json - {exp}".format(exp = exp))
            return
        
        if resource["mode"] == "directory":
            query = {}
            query["parent"] = resource["parent"]
            query["name"]   = resource["name"]
            callback = functools.partial(self._on_get_siblings, _candidateExnode = self.request)
            self._cursor = self.dblayer.find(query, callback)
        else:
            self.post_psjson(exnode = resource)
        
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
            self.post_psjson(exnode = json.loads(self.request.body))

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
            resources = []
            if isinstance(kwargs["exnode"], list):
                for item in kwargs["exnode"]:
                    resources.append(self._model_class(item))
            else:
                resources = [self._model_class(kwargs["exnode"])]
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


                if item["mode"] == "file":
                    item["extents"] = self.update_allocations(item)
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


    def update_allocations(self, resource):
        allocations = []

        try:
            for alloc in resource["extents"]:
                tmpAllocation = self.allocation_model(alloc)
                tmpAllocation["parent"] = resource[self.Id]
                tmpAllocation["selfRef"] = "%s/%s/%s" % (self.request.full_url().split('?')[0].rsplit('/', 1)[0],
                                                         "extents",
                                                         tmpAllocation[self.Id])

                mongo_alloc = dict(tmpAllocation._to_mongoiter())
                allocations.append(mongo_alloc)
                self._subscriptions.publish(tmpAllocation)
                
            self.allocation_layer.insert(allocations, lambda *_, **__: None)
        except Exception as exp:
            raise NameError(exp)

        for alloc in allocations:
            alloc.pop("_id", None)
            
        return allocations
