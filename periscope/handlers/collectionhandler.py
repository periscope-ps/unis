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

import asyncio, json, jsonpointer
import tornado.web
from jsonpath import jsonpath
from tornado.httpclient import AsyncHTTPClient

import periscope.settings as settings
from periscope.settings import MIME
from periscope.handlers.networkresourcehandler import NetworkResourceHandler
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


    async def _put_resource(self, resource):
        try:
            for key in self._collections:
                if key in resource:
                    resource.pop(key, None)
        
            super(CollectionHandler, self)._put_resource(resource)
        except Exception as exp:
            raise exp
        
    async def _process_resource(self, resource, res_id = None, run_validate = True):
        tmpResource = self._model_class(resource, schemas_loader = schemaLoader)
        tmpResource = self._add_post_metadata(tmpResource)
        complete_links = (self.get_argument("complete_links", None) != 'false')
        
        
        ppi_classes = getattr(self.application, '_ppi_classes', [])
        for pp in ppi_classes:
            pp.pre_post(tmpResource, self.application, self.request)

        if complete_links:
            if self._complete_href_links(resource, resource) < 0:
                raise ValueError("Invalid href in resource")

        links = await asyncio.gather(*[self._create_child(k, tmpResource) for k in self._collections.keys() if k in tmpResource])
        for values in links:
            tmpResource[values["collection"]] = values["hrefs"]

        return tmpResource

    async def _create_child(self, key, resource):
        http_client = AsyncHTTPClient()
        url = "{protocol}://{host}{path}?validate=false&complete_links=false"
        links = []
        query = []
        for r in resource[key]:
            links.append(r) if "rel" in r and "href" in r else query.append(r)
        if query:
            response = await tornado.gen.Task(
                http_client.fetch,
                url.format(protocol = self.request.protocol, host = self.request.host, path = self.reverse_url(key)),
                method          = "POST",
                body            = dumps_mongo(query),
                request_timeout = 180,
                validate_cert   = False,
                client_cert     = settings.CLIENT_SSL_OPTIONS['certfile'],
                client_key      = settings.CLIENT_SSL_OPTIONS['keyfile'],
                headers         = { "Cache-Control": "no-cache",
                                    "Content-Type": MIME["PSJSON"],
                                    "connection": "close" }
            )
            if response.code >= 400:
                raise Exception("Could not add child resource")

            response = json.loads(response.body)
            if not isinstance(response, list):
                links.append({ "href": response["selfRef"], "rel": "full" })
            else:
                for r in response:
                    links.append({ "href": r["selfRef"], "rel": "full" })

        return { "collection": key, "hrefs": links }
    
        
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
            if isinstance(current["href"], (bytes, str)):
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
