import json
import time
from periscope.settings import MIME
from bson.json_util import dumps
from periscope.handlers.resourcehandler import ResourceHandler

class EventsHandler(ResourceHandler):
        
    def _insert(self, resources, collection):
        
        resource = resources[0]
        
        url_values = resource["metadata_URL"].split("/")
        metadata_id = url_values[len(url_values) - 1]
        collection_name = url_values[len(url_values) - 2]
        data = self._mongo.unis_db[collection_name].find({"id" : metadata_id}).count()
        
        if data == 0:
            self.resp.status = falcon.HTTP_400
            self.resp.body = json.dumps(str(exp), indent=4)
        else:
            self._mongo.unis_db.create_collection(metadata_id,
                                      capped      = True,
                                      size        = resource["collection_size"],
                                      autoIndexId = False)
        
        
            resource[self.timestamp] = int(time.time() * 1000000)
            resource[self.Id] = metadata_id
            self.insert(resource, collection, summarize = False)
            
        return

    def _find(self, **options):
        options["query"].pop("\\$status", None)
        if not options["query"]:
            return self._mongo.unis_db[self.collection_name].find()
        elif self.Id in options["query"] or "$or" in options["query"]:
            return self._mongo.unis_db[self.collection_name].find(**options)
        else:
            self._query = options["query"]
            return None

    def _add_response_headers(self, cursor):
        count = 1
        accept = self.accept_content_type
        self.resp.set_header("Content-Type", accept + "; profile=" + self.schemas_single[accept])
        
        return count

    def _write_get(self, cursor, is_list = False, inline=False, unique=False):
        response = []
        
        if cursor:
            count = cursor.count()
            
            for resource in cursor:
                res = ""
                mid = resource["metadata_URL"].split('/')[resource["metadata_URL"].split('/').__len__() - 1]
                try:
                    res = self.generate_response(mid)
                except ValueError as exp:
                    raise ValueError(exp)
                response.insert(0, res)
        else:
            count = 0
            for d in self._query["$and"]:
                if 'mids' in d.keys():
                    if isinstance(d["mids"],dict):
                        for m in d['mids']['$in']:
                            try:
                                res = self.generate_response(m)
                            except ValueError as exp:
                                raise ValueError(exp)
                            count += 1
                            response.insert(0, res)
                    else:
                        try:
                            res = self.generate_response(d['mids'])
                        except ValueError as exp:
                            raise ValueError(exp)
                        count += 1
                        response.insert(0, res)
                        
        if self.accept_content_type == MIME["PSBSON"]:
            json_response = bson_encode(response)
        else:
            json_response = response
            
        buf = [json_response]

        return (buf, count)

    def _return_resoures(self, query):
        try:                
            for resource in self._mongo.unis_db[self.collection_name].find(query):
                self.publisher.publish(resource, self.collection_name)
        except Exception as exp:
            raise ValueError(exp)
        
        
    def del_stat_fields(self,generic):
        generic.pop("ns",None)
        generic.pop("numExtents",None)
        generic.pop("nindexes",None)
        generic.pop("lastExtentSize",None)
        generic.pop("paddingFactor",None)
        generic.pop("flags",None)
        generic.pop("totalIndexSize",None)
        generic.pop("indexSizes",None)
        generic.pop("max",None)
        generic.pop("ok",None)
        if generic["capped"] == 1:
            generic["capped"]="Yes"
        else:
            generic["capped"]="No"

    def generate_response(self, mid):
        tmpReponse = None
        try:
            command={"collStats": mid,"scale":1}            
            generic = self._mongo.unis_db.command(command)
        except Exception as exp:
            raise ValueError("At least one of the metadata ID is invalid. {}".format(exp))
            return
        
        
        self.del_stat_fields(generic)
        specific={}
        if 'ts' in self.req.params.keys():
            criteria = self.req.params['ts'][0].split('=')
            
            if criteria[0] == 'gte':
                specific["startTime"] = int(criteria[1])
            if criteria[0] == 'lte':
                specific["endTime"] = int(criteria[1])
            
            if self.req.params['ts'].__len__() > 1 :            
                criteria = self.req.params['ts'][1].split('=')
                if criteria[0] == 'gte':
                    specific["startTime"] = int(criteria[1])
                if criteria[0] == 'lte':
                    specific["endTime"] = int(criteria[1])
            
            db_query = {"ts": { "$gt": 0 } }
            if startTime in specific:
                db_query["ts"]["$gte"] = specific["startTime"]
            if endTime  in specific:
                db_query["ts"]["$lte"] = specific["endTime"]
            specific["numRecords"] = self._mongo.unis_db[mid].find(db_query).count()
            
        return {"mid": mid, "generic": generic, "queried": specific}
