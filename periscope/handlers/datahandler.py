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
import tornado.web

from urllib.parse import urlparse,urlunparse

import periscope.settings as settings
from periscope.db import dumps_mongo, DBLayer
from periscope.settings import MIME
from periscope.handlers.networkresourcehandler import NetworkResourceHandler

class DataHandler(NetworkResourceHandler):
    def _validate_request(self, res_id, allow_id = False, require_id = False):
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defined for content of type '%s'" % \
                      (self.accept_content_type)
            self.send_error(500, message=message)
            return False
        if self._validate_psjson_profile():
            return False
        
        return True
    
    def _add_post_metadata(self, resource, res_id = None):
        loc = urlparse(self.request.full_url())._replace(query=None, fragment=None)
        resource["mid"] = res_id or resource["mid"]
        resource["selfRef"] = loc._replace(path=f"{loc.path}/{resource['mid']}").geturl()
        resource["$schema"] = resource.get("$schema", self.schemas_single[MIME['PSJSON']])
        
        return resource
    
    async def _insert(self, resources):
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mids[resource["mid"]] = []
            mids[resource["mid"]].extend(resource["data"])
        
        for mid, data in mids.items():
            push_data = { 'id': mid, 'data': data }
            self._subscriptions.publish(push_data, self._collection_name, { "action": "POST", "collection": "data/{}".format(mid) },
                                        self.trim_published_resource)
            await DBLayer(self.application.db, mid, True).insert(data)

    async def _post_return(self, resources):
        return
    
    async def _return_resources(self, mid, query):
        resp = []
        async for record in DBLayer(self.application.db, mid, True).find(query):
            resp.append(ObjectDict._from_mongo(record))

        if len(resp) == 1:
            location = self.request.full_url().split('?')[0]
            if not location.endswith(response[0][self.Id]):
                location = location + "/" + response[0][self.Id]
                
            self.set_header("Location", location)
            return resp[0]
        else:
            return resp
        
    
    @tornado.web.removeslash
    async def get(self, res_id=None):
        if not res_id:
            self.write_error(403, message = "Data request must include a metadata id")
            return
        
        # Parse arguments and set up query
        try:
            parsed = await self._parse_get_arguments()
            options = dict(query  = parsed["query"]["query"],
                           limit  = parsed["limit"],
                           sort   = parsed["sort"],
                           skip   = parsed["skip"])
            if not options["limit"]:
                options.pop("limit", None)
            
            options["query"]["\\$status"] = { "$ne": "DELETED"  }
            options["fields"] = { "_id": 0 }
        except Exception as exp:
            self.write_error(403, message = exp)
            return
            
        # we don't want to wait here since this is a direct query on the state of the collection
        # we could have an SSE endpoint that implemented a hanging GET, allowing more data
        # over the HTTP connection as it arrived
        query = options.pop("query")
        count = await DBLayer(self.application.db, res_id, True).count(query, **options)

        if not count:
            self.write('[]')
            return

        first = True
        async for record in DBLayer(self.application.db, res_id, True).find(query):
            self.write('[\n' if first else ',\n')
            first = False
            self.write(dumps_mongo(record, indent=2).replace('\\\\$', '$').replace('$DOT$', '.'))
        self.write('\n]')
        
        await self._add_response_headers(count)
        self.set_status(200)
        self.finish()

    def trim_published_resource(self, resource, fields):
        return {resource['id']: resource['data']}
