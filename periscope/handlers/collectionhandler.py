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
#!/usr/bin/env python3

import falcon
import json
import functools
import jsonpointer
import periscope.settings as settings
import periscope.utils as utils
from urllib.parse import urlparse
from jsonpath import jsonpath
from periscope.models import schemaLoader
from requests import request
from periscope.settings import MIME
from periscope.handlers.resourcehandler import ResourceHandler
from bson.json_util import dumps
from periscope.models import NetworkResource
from periscope.models import HyperLink
from periscope.models import Topology
from periscope.models import schemaLoader


class CollectionHandler(ResourceHandler):

    def _put_resource(self, resource):
        try:
            for key in self._collections:
                if key in resource:
                    resource.pop(key, None)
        
            super(CollectionHandler, self)._put_resource(resource)
        except Exception as exp:
            raise exp

    def _modify_metadata_child(self, resource, col):
        uri = urlparse(self.req.url)
        try:
            resource["selfRef"] = "{scheme}://{netloc}/{col}/{uid}".format(scheme=uri.scheme,
                                                                           netloc=uri.netloc,
                                                                           col=col,
                                                                           uid = resource[self.Id])
                                                                           
            resource["$schema"] = settings.Resources[col]["schema"][MIME['PSJSON']]
        except Exception as exp:
            self.log.error("failed to match uri - {e}".format(e = exp))
        
        return resource
                
    def _process_resource(self, resource, res_id = None, run_validate = True):
        tmpResource = self._model_class(resource, schemas_loader = schemaLoader)
        tmpResource = self._add_post_metadata(tmpResource)
        #complete_links = (self.req.get_param("complete_links", default=None) != 'false')
        
        #ppi_classes = getattr(self.application, '_ppi_classes', [])
        #for pp in ppi_classes:
        #    pp.pre_post(tmpResource, self.application, self.request)
            
        if self.complete_links:
            if self._complete_href_links(resource, resource) < 0:
                raise ValueError("Invalid href in resource")
        
        links = [ self._create_child(key, tmpResource) for key in self._collections.keys() if key in tmpResource ]
        
        for values in links:
            tmpResource[values["collection"]] = values["hrefs"]
            
        return tmpResource
        
        
    def _create_child(self, key, resource):
        
        url = "{protocol}://{host}:{port}/{path}?validate=false&complete_links=false"
        links = []
        query = []
        
        for r in resource[key]:
            links.append(r) if "rel" in r and "href" in r else query.append(r)
            
        if query:

            resources = resource[key]
            
            try:
                for index in range(len(resources)):
                    self.complete_links = False

                    if key not in ['network', 'networks', 'domain', 'domains', 'topology', 'topologies', 'exnodes', 'exnode']:
                        tmpResource = super(CollectionHandler, self)._process_resource(resources[index], None, False)
                    else:
                        tmpResource = self._process_resource(resources[index], None, False)
                    
                    tmpResource = self._modify_metadata_child(tmpResource, key)
                    resources[index] = dict(tmpResource._to_mongoiter())
            except Exception as exp:
                message = "Could not add child resource. Not valid body - {exp}".format(exp = exp)
                self.resp.status = falcon.HTTP_400
                self.resp.body = json.dumps(message, indent=4)
                self.log.error(message)
                return
        
            try:
                self._insert(resources, settings.Resources[key]["collection_name"])
            except Exception as exp:
                message = "Could not add child resource. Could not process the POST request - {exp}".format(exp = exp)
                self.resp.status = falcon.HTTP_409
                self.resp.body = json.dumps(message, indent=4)
                self.log.error(message)
                return


            response = resources
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
            message = "Unrecognized resource type: %s" % type(resource)
            self.resp.status = falcon.HTTP_400
            self.resp.body = json.dumps(message, indent=4)
            self.log.error(message)
            return -1
        resource_name = self._models_index[fullname]
        resource_url = self.reverse_url(
            self._collections[resource_name]["name"], resource[self.Id]) 
        resource["selfRef"] = "%s://%s%s" % (
            self.req.scheme, self.req.host, resource_url)
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

