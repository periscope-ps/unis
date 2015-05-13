#!/usr/bin/env python

import json
import functools
import jsonpointer
from periscope.models import schemaLoader
from jsonpath import jsonpath
from netlogger import nllog
import tornado.gen as gen
import tornado.web
from tornado.httpclient import AsyncHTTPClient

import periscope.settings as settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo
from periscope.models import NetworkResource
from periscope.models import HyperLink
from periscope.models import Topology
from periscope.models import schemaLoader
import periscope.utils as utils


class CollectionHandler(NetworkResourceHandler):
    def initialize(self, collections, *args, **kwargs):
        self._collections = collections
        super(CollectionHandler, self).initialize(*args, **kwargs)
        self._models_index = {}
        self._dblayers_index = {}
        self._cache = {}
        for key, value in self._collections.items():
            self._models_index[value["model_class"]] = key
            dblayer = self.application.get_db_layer(value["collection_name"],
                    value["id_field_name"],
                    value["timestamp_field_name"],
                    value["is_capped_collection"],
                    value["capped_collection_size"]
                )
            self._dblayers_index[key] = dblayer
    
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def post(self):
        # Check if the schema for conetnt type is known to the server
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defiend fot content of type '%s'" % \
                        (self.accept_content_type)
            self.send_error(500, message=message)
            return
        
        # Load the appropriate content type specific POST handler
        if self.content_type == MIME['PSJSON']:
            self.post_psjson()
        elif self.content_type == MIME['PSBSON']:
            self.post_psbson()
        else:
            self.send_error(500,
                message="No POST method is implemented fot this content type")
            return
        return
    
    @gen.engine
    def post_psjson(self):
        """
        Handles HTTP POST request with Content Type of PSJSON.
        """
        profile = self._validate_psjson_profile()
        run_validate = True
        complete_links = True
        if self.get_argument("validate", None) == 'false':
            run_validate = False
        if self.get_argument("complete_links", None) == 'false':
            complete_links = False
        if not profile:
            return
        try:
            body = json.loads(self.request.body)
        except Exception as exp:
            self.send_error(400, message="malformatted json request '%s'." % exp)
            return
        
        try:
            collections = []
            if isinstance(body, list):
                for item in body:
                    collections.append(self._model_class(item,
                        schemas_loader=schemaLoader))
            else:
                collections = [self._model_class(body,
                        schemas_loader=schemaLoader)] 
        except Exception as exp:
            self.send_error(400, message="malformatted request " + str(exp))
            return
                
        # Validate schema
        try:
            for collection in collections:
                if collection.get("$schema", None) != \
                    self.schemas_single[self.accept_content_type]:
                     self.send_error(400,
                     message="Not valid body '%s'; expecting $schema: '%s'." % \
                     (collection.get("$schema", None), self.schemas_single[self.accept_content_type]))
                     return
                if run_validate == True:
                    collection._validate()
        except Exception as exp:
            self.send_error(400, message="Not valid $schema '%s'." % exp)
            return
        
        # (EK): make this cleaner and more efficient
        if getattr(self.application, '_ppi_classes', None):
            try:
                for collection in collections:
                    # check the top-level object
                    for pp in self.application._ppi_classes:
                        pp.pre_post(collection, self.application, self.request)
                        # now check each resource in the collection
                        for key in self._collections.keys():
                            if key in collection:
                                for pp in self.application._ppi_classes:
                                    pp.pre_post(collection[key], self.application, self.request)
            except Exception, msg:
                self.send_error(400, message=msg)
                return
        
        self._cache = {}
        coll_reps = []
        for collection in collections:
            collection["selfRef"] = "%s/%s" % (self.request.full_url().split('?')[0], collection[self.Id])
                    
            # Convert JSONPath and JSONPointer Links to Hyper Links
            if complete_links:
                ret = self._complete_href_links(collection, collection)
            else:
                ret = collections
            # Check if something went wrong
            if ret < 0:
                return
            
            res_refs = [
                {
                    self.Id: collection[self.Id],
                    self.timestamp: collection[self.timestamp]
                }
            ]
            has_error = False
            keys_to_insert = []
            http_client = AsyncHTTPClient()
            
            # Async calls to insert all the resources included in the request
            args = "?"
            
            args += 'validate=false'
            args += '&complete_links=false'
            
            responses = yield [
                gen.Task(
                    http_client.fetch,
                    "%s://%s%s%s"  % (self.request.protocol, self.request.host, self.reverse_url(key), args),
                    method = "POST",
                    body = dumps_mongo(collection[key]),
                    request_timeout=180,
                    validate_cert=False,
                    client_cert= settings.CLIENT_SSL_OPTIONS['certfile'],
                    client_key= settings.CLIENT_SSL_OPTIONS['keyfile'],
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": MIME['PSJSON'],
                        "Connection": "close"
                        }
                    )
                    for key in self._collections.keys()
                    if key in collection
            ]
            
            for response in responses:
                if response.code >= 400:
                    self.send_error(response.code, message=response.body)
                    return
           
            for key in self._collections:
                if key not in collection:
                    continue
                for index in range(len(collection[key])):
                    if 'selfRef' in collection[key][index]:
                        collection[key][index] = {"href": collection[key][index]["selfRef"], "rel": "full"}
            coll_reps.append(dict(collection._to_mongoiter()))
        
        callback = functools.partial(self.on_post, res_refs=res_refs)
        self.dblayer.insert(coll_reps, callback=callback)
        
    def set_self_ref(self, resource):
        """Assignes a selfRef to a resource"""
        fullname = utils.class_fullname(resource)
        if fullname not in self._models_index:
            self.send_error(400,
                message="Unrecognized resource type: %s" % type(resource))
            return -1
        resource_name = self._models_index[fullname]
        resource_url = self.reverse_url(
            self._collections[resource_name]["name"], resource[self.Id]) 
        resource["selfRef"] = "%s://%s%s" % (
            self.request.protocol, self.request.host, resource_url)
        return 0
            
    def _complete_href_links(self, parent_collection, current):
        """Resolves self hyperlinks (JSONPath and JSONPointers."""
        if isinstance(current, HyperLink) or \
            (isinstance(current, dict) and "href" in current):
            if isinstance(current["href"], (unicode, str)):
                resource = None
                if current["href"] in self._cache:
                    resource = self._cache[current["href"]]
                elif current["href"].startswith("#"):
                    resource = jsonpointer.resolve_pointer(parent_collection,
                              current["href"][1:])
                    if not resource:
                        resource = "Unresolved"
                elif current["href"].startswith("$"):
                    path = jsonpath(parent_collection,
                        current["href"], result_type="PATH")
                    if path:
                        resource = eval("parent_collection%s" % path[0].lstrip("$"))
                    else:
                        resource = "Unresolved"
                self._cache[current["href"]] = resource
                if resource and resource != "Unresolved":
                    if "selfRef" not in resource:
                        ret = self.set_self_ref(resource)
                        if ret < 0:
                            return ret
                    current["href"] = resource["selfRef"]
            return 0
        elif isinstance(current, list):
            keys = range(len(current))
        elif isinstance(current, dict):
            keys = current.keys()
        else:
           return 0
        
        for key in keys:
            value = current[key]
            if isinstance(value, (NetworkResource, Topology)) and \
                "selfRef" not in value:
                ret = self.set_self_ref(value)
                if ret < 0:
                    return ret
            if isinstance(value, list) or isinstance(value, dict):
                ret = self._complete_href_links(parent_collection, value)
                if ret < 0:
                    return ret
        return 0

