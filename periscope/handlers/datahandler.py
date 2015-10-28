#!/usr/bin/env python

import json
import functools
import tornado.web
from motor import MotorClient

import periscope.settings as settings
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
            tmpResource["mid"] = res_id
            
        tmpResource["selfRef"] = "{host}/{rid}".format(host = self.request.full_url().split('?')[0],
                                                       rid  = tmpResource[self.Id])
        tmpResource["$schema"] = tmpResource.get("$schema", self.schemas_single[MIME['PSJSON']])
        
        if tmpResource["$schema"] != self.schemas_single[self.accept_content_type]:
            self.send_error(400, message="Not valid schema - got {got}, expected {expected}".format(got      = tmpResource["$schema"],
                                                                                                    expected = self.schemas_single[self.accept_content_type]))
            raise ValueError("Bad schema")
        return tmpResource
    
    @tornado.gen.coroutine
    def _insert(self, resources):
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mids[resource["mid"]] = []
            mids[resource["mid"]].extend(resource["data"])
            
        collections = yield self.application.db.collection_names()
        db_commands = []
        for mid, data in mids.iteritems():
            if mid in collections:
                db_commands.append(self.application.db[mid].insert(data))
            results = yield db_commands
            
    @tornado.gen.coroutine
    def _post_return(self, resources):
        response = []
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mid[resources["mid"]] = { "$or": [] }
            mids[resource["mid"]]["$or"].append( { self.Id: resource[self.Id], self.timestamp: resource[self.timestamp] } )
            
            results = []
            for mid, query in mids.iteritems():
                try:
                    yield self._return_resources(mid, query)
                except tornado.gen.Return as result:
                    results.append(result)
                    
        for result in results:
            response.extend(result)
            
        self.write(dumps_mongo(response, indent=2))
    
    @tornado.gen.coroutine
    def _return_resources(self, mid, query):
        cursor = self.application.db[mid].find(query)
        response = []
        while (yield cursor.fetch_next()):
            resource = cursor.next_object()
            response.append(ObjectDict._from_mongo(resource))
            push_data = { 'id': mid, 'data': [ resource ] }
            self._subscriptions.publish(resource, self._collection_name, self.trim_published_resource)
            
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
            #self.send_error(500, message = "Data request must include a metadata id")
            return
        
        # Parse arguments and set up query
        try:
            parsed = self._parse_get_arguments()
            options = dict(query  = parsed["query"]["query"],
                           limit  = parsed["limit"],
                           sort   = parsed["sort"],
                           skip   = parsed["skip"])
            if not options["limit"]:
                options.pop("limit", None)
            if res_id:
                options["query"][self.Id] = res_id
                
            options["query"]["status"] = { "$ne": "DELETED"  }
        except Exception as exp:
            self.write_error(403, message = exp)
            return

        cursor = self.application.db[res_id].find(tailable=True, await_data=True, **options)
        count = yield cursor.count()
        
        if not count:
            self.write('[]')
            return
        elif count > 1:
            self.write('[\n')
            
        yield cursor.fetch_next
        resource = cursor.next_object()
        self.write(json.dumps(resource, indent = 2).replace('\\\\$', '$').replace('$DOT$', '.'))
        
        for i in range(1, count):
            yield cursor.fetch_next
            self.write(',\n')
            resource = cursor.next_object()
            self.write("{result}".format(result = json.dumps(resource, indent =2 )).replace('\\\\$', '$').replace('$DOT$', '.'))
            
        if count > 1:
            self.write('\n]')

        
        yield self._add_response_headers(count)
        self.set_status(201)
        self.finish()

        
    
    def trim_published_resource(self, resource, fields):
        return {resource['id']: resource['data']}
