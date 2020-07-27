import json
import time
import falcon
from pymongo import MongoClient
from periscope.utils import *
from periscope.settings import MIME, Resources
from periscope.handlers.resourcehandler import ResourceHandler

class DataHandler(ResourceHandler):

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
            
        resource["selfRef"] = "{host}/{rid}".format(host = self.req.url.split('?')[0],
                                                       rid  = resource[self.Id])
        resource["$schema"] = resource.get("$schema", self.schemas_single[MIME['PSJSON']])
        
        return resource
    
    def _insert(self, resources):
        
        mids = {}
        for resource in resources:
            if resource["mid"] not in mids:
                mids[resource["mid"]] = []
            mids[resource["mid"]].extend(resource["data"])
        
        for mid, data in mids.items():
            push_data = { 'id': mid, 'data': data }
            self._mongo.unis_db[self.collection_name].insert(push_data)
            self.publisher.publish(push_data, self.collection_name, { "action": "POST", "collection": "data/{}".format(mid) },
                                        self.trim_published_resource)
            
    def _post_return(self, resources):
        # don't return data posts to measurement collectors
        return

    def trim_published_resource(self, resource, fields):
        return {resource['id']: resource['data']}


    def on_get(self, req, resp, res_id=None):
    
        self.req = req
        self.resp = resp
        self.timestamp = "ts"
        self.Id = "id"
        self._tailable = False
        self.resource_name = req.path.split("/")[1]
        self.collection_name = Resources[self.resource_name]["collection_name"]
        self.schemas_single = Resources[self.resource_name]["schema"]
        self._model_class = load_class(Resources[self.resource_name]["model_class"])
        self._accepted_mime = [MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML']]
        self._content_types_mime = [MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML'], MIME['HTML']]
        self._mongo = MongoClient('localhost', 27017)
        
        if not res_id:
            message = "Data request must include a metadata id"
            resp.status = falcon.HTTP_403
            resp.body = json.dumps(message, indent=4)
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
            
            options["query"]["\\$status"] = { "$ne": "DELETED"  }
            options["fields"] = { "_id": 0 }
        except Exception as exp:
            resp.status = falcon.HTTP_403
            resp.body = json.dumps(string(exp), indent=4)
            return
            
        query = options.pop("query")
        fields = options.pop("fields", {})
        cursor = self._mongo.unis_db[res_id].find(query, fields, **options)
        count = cursor.count(with_limit_and_skip=True)
        buf = []
        
        if not count:
            buf = []
        
        for resource in cursor:
            buf.append(resource)
                
        self._add_response_headers(count)
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(buf, indent=4)
        
        return        

