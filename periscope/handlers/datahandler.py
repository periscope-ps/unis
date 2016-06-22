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

import periscope.settings as settings
from periscope.db import dumps_mongo
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler

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
        if res_id:
            resource["mid"] = res_id
            
        resource["selfRef"] = "{host}/{rid}".format(host = self.request.full_url().split('?')[0],
                                                       rid  = resource[self.Id])
        resource["$schema"] = resource.get("$schema", self.schemas_single[MIME['PSJSON']])
        
        return resource
    
    @tornado.gen.coroutine
    def _insert(self, resources):
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mids[resource["mid"]] = []
            mids[resource["mid"]].extend(resource["data"])

        for mid, data in mids.iteritems():
            push_data = { 'id': mid, 'data': data }
            self._subscriptions.publish(push_data, self._collection_name, self.trim_published_resource)
            self.application.db[mid].insert(data)
            
    @tornado.gen.coroutine
    def _post_return(self, resources):
        # don't return data posts to measurement collectors
        return

        response = []
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mids[resource["mid"]] = { "$or": [] }
            mids[resource["mid"]]["$or"].append( { self.timestamp: resource[self.timestamp] } )
            
        results = []
        for mid, query in mids.iteritems():
            results = yield self._return_resources(mid, query)
            
            for result in results:
                response.extend(result)
            
        self.write(dumps_mongo(response, indent=2))
    
    @tornado.gen.coroutine
    def _return_resources(self, mid, query):
        cursor = self.application.db[mid].find(query)
        response = []
        while (yield cursor.fetch_next):
            resource = cursor.next_object()
            response.append(ObjectDict._from_mongo(resource))
            
        if len(response) == 1:
            location = self.request.full_url().split('?')[0]
            if not location.endswith(response[0][self.Id]):
                location = location + "/" + response[0][self.Id]
                
            self.set_header("Location", location)
            raise tornado.gen.Return(response(response[0]))
        else:
            raise tornado.gen.Return(response)
        
    
    @tornado.web.asynchronous
    @tornado.web.removeslash
    @tornado.gen.coroutine
    def get(self, res_id=None):
        if not res_id:
            self.write_error(403, message = "Data request must include a metadata id")
            return
        
        # Parse arguments and set up query
        try:
            parsed = yield self._parse_get_arguments()
            options = dict(query  = parsed["query"]["query"],
                           limit  = parsed["limit"],
                           sort   = parsed["sort"],
                           skip   = parsed["skip"])
            if not options["limit"]:
                options.pop("limit", None)
            if res_id:
                options["query"][self.Id] = res_id
                
            options["query"]["status"] = { "$ne": "DELETED"  }
            options["fields"] = { "_id": 0 }
        except Exception as exp:
            self.write_error(403, message = exp)
            return

        # we don't want to wait here since this is a direct query on the state of the collection
        # we could have an SSE endpoint that implemented a hanging GET, allowing more data
        # over the HTTP connection as it arrived
        cursor = self.application.db[res_id].find(tailable=False, await_data=False, **options)
        count = yield cursor.count(with_limit_and_skip=True)
        
        if not count:
            self.write('[]')
            return
        elif count >= 1:
            self.write('[\n')
            
        citem = 0
        while (yield cursor.fetch_next):
            resource = cursor.next_object()
            self.write(dumps_mongo(resource, indent = 2).replace('\\\\$', '$').replace('$DOT$', '.'))
            citem = citem + 1
            if citem == count:
                self.write('\n]')
            else:
                self.write(',\n')
        
        yield self._add_response_headers(count)
        self.set_status(201)
        self.finish()
    
    def trim_published_resource(self, resource, fields):
        return {resource['id']: resource['data']}
