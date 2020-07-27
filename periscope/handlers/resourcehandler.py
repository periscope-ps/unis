import falcon
import os, json
import copy, time
import zmq, re
import random
import sys
import time
import urllib.request
import bson
from pymongo import MongoClient
from uuid import uuid4
from urllib.parse import urlparse
from bson.json_util import dumps
from bson.objectid import ObjectId
from periscope.settings import MIME, Resources
from periscope.utils import *
from periscope.models import *
from periscope.handlers.subscriptionhandler import *
from periscope.handlers.basehandler import BaseHandler

if hasattr(bson, "dumps"):
    # standalone bson
    bson_decode = bson.loads
    bson_encode = bson.dumps
    bson_valid = None
else:
    # pymongo's bson
    bson_decode = bson.decode_all
    bson_encode = bson.BSON.encode
    bson_valid = bson.is_valid

def decode(str):
    while True:
        dec = urllib.request.unquote(str)
        if dec == str:
            break
        str = dec
    return dec
    
class ResourceHandler(BaseHandler):

    @property
    def accept_content_type(self):
        """
        HTTP has methods to allow the client and the server to negotiate
        the content type for their communication.
        
        Rigth now, this is simple implementation, but additional more complex
        methods can be added in the future.
        
        See:
            http://www.w3.org/Protocols/rfc2616/rfc2616-sec12.html
            
            http://www.ietf.org/rfc/rfc2295.txt
            
            http://httpd.apache.org/docs/2.2/content-negotiation.html
            
            http://www.w3.org/TR/webarch/#def-coneg
        """
        if not getattr(self, '_accept', None):
            self._accept = None
            raw = self.req.headers.get("Accept", MIME['PSJSON'])
            regex = re.findall(
                "(?P<type>(\w+|\*)\/(\w+|\*)(\+\w+)?)(;[^;,]*)?([ ]*,[ ]*)?",
                raw
            )
            accept = [k[0] for k in regex]
            for accepted_mime in self._accepted_mime:
                if accepted_mime in accept:
                    self._accept = accepted_mime
            if "*/*" in accept:
                self._accept = MIME['JSON']
            if not self._accept:
                message = "HTTP 406: Unsupported accept content type '%s'" % self.req.headers.get("Accept", None)
                raise Exception(message)
        return self._accept
        
    @property
    def content_type(self):
        """
        Returns the content type of the client's request
        
        See:
            
            http://www.w3.org/Protocols/rfc2616/rfc2616-sec12.html
            
            http://www.ietf.org/rfc/rfc2295.txt
            
            http://httpd.apache.org/docs/2.2/content-negotiation.html
            
            http://www.w3.org/TR/webarch/#def-coneg
        """
        
        if not getattr(self, '_content_type', None):
            raw = self.req.headers.get("Content-Type", MIME['PSJSON'])
            regex = re.findall(
                "(?P<type>\w+\/\w+(\+\w+)?)(;[^;,]*)?([ ]*,[ ]*)?",
                raw
            )
            content_type = [k[0] for k in regex]
            for accepted_mime in self._content_types_mime:
                if accepted_mime in content_type:
                    self._content_type = accepted_mime
                    return self._content_type
            message = "HTTP 415: Unsupported content type '%s'" % self.req.headers.get("Content-Type", "")
            raise Exception(message)
        
        return self._content_type
    
    @property
    def supports_streaming(self):
        """
        Returns true if the client asked for HTTP Streaming support.
        
        Any request that is of type text/event-stream or application/json
        with Connection = keep-alive is considered a streaming request
        and it's up to the client to close the HTTP connection.
        """
        if self.req.headers.get("Connection", "").lower() == "keep-alive":
            return self.req.headers.get("Accept", "").lower() in \
                    [MIME['PSJSON'], MIME['SSE']]
        else:
            return False
        
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

        # Parse arguments and set up query
        try:
            parsed = self._parse_get_arguments() 
            
            options = dict(query  = parsed["query"]["query"],
                           fields = parsed["fields"],
                           limit  = parsed["limit"],
                           sort   = parsed["sort"],
                           skip   = parsed["skip"])
            
            inline = parsed["inline"]
            if not options["limit"]:
                options.pop("limit", None)
            if res_id:
                options["query"][self.Id] = res_id
                is_list = True
                if "limit" not in options and not len(options["fields"]) and not options["skip"]:
                    options["limit"] = 1
                    is_list = False
            else:
                is_list = "query" in options and options["query"]
            options["query"]["\\$status"] = { "$ne": "DELETED"  }

        except Exception as exp:
            resp.status = falcon.HTTP_403
            resp.body = json.dumps(str(exp), indent=4)
            self.log.error(str(exp))
            return

        
        keep_alive = self.supports_streaming # or self.supports_sse()
        if keep_alive and self._tailable:
            # This spins off a perpetual connection
            self._get_tailable(query = options["query"], fields = options["fields"])
        else:
            try:
                cursor = self._find(**options)
            except Exception as exp:
                message = "Could not find resource - {exp}".format(exp = exp)
                resp.status = falcon.HTTP_404
                resp.body = json.dumps(message, indent=4)
                self.log.error(message)
                return
            
            try:
                (buf, count) = self._write_get(cursor, is_list, inline, parsed['unique'])
            except Exception as exp:
                message = "Failure during post processing - {exp}".format(exp = exp)
                resp.status = falcon.HTTP_404
                resp.body = json.dumps(message, indent=4)
                self.log.error(message)
                return
            
        self._add_response_headers(count)
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(buf, indent=4)
        
        return
        
            
    def _find(self, **kwargs):
        
        query = kwargs.pop("query", {})
        
        fields = kwargs.pop("fields", {})
        fields["_id"] = 0
    
        return self._mongo.unis_db[self.collection_name].find(query, fields, **kwargs)
    
    def _add_response_headers(self, count):
        
        accept = self.accept_content_type
        self.resp.set_header("Content-Type", accept + "; profile=" + self.schemas_single[accept])
        self.resp.set_header('X-Count', count)
        
        return
    
    def _write_get(self, cursor, is_list=False, inline=False, unique=False):
        
        seen = {}
        count = cursor.count(with_limit_and_skip=True)
        is_list = count != 1 or is_list
        buf = ""
        
        if self.accept_content_type == MIME["PSBSON"]:
            results = []
            for resource in cursor:
                if not unique or str(resource.get('id', resource)) not in seen:
                
                  seen[str(resource.get('id', resource))] = True
                  results.append(resource)
                  buf.append(resource)
            
            if results and not is_list: results = results[0]
            results = bson_encode({'d': results})
            return (results, count)
        else:
            buf = []
            if not count:
                return (buf, count)
                
            for resource in cursor:
                if not unique or str(resource.get('id', resource)) not in seen:                
                  seen[str(resource.get('id', resource))] = True
                  buf.append(resource)
        
        return (buf, count)

    def _parse_get_arguments(self):
        
        """Parses the HTTP GET areguments given by the user."""
        def convert_value_type(key, value, val_type):
            message = "HTTP 400: '%s' is not of type '%s'" % (key, val_type)
            
            if val_type == "integer":
                try:
                    return int(value)
                except:
                    raise Exception(message)
            if val_type == "number":
                try:
                    return float(value)
                except:
                    raise Exception(message)
            if val_type == "string":
                try:
                    return unicode(value)
                except:
                    raise Exception(message)
            if val_type == "boolean":
                try:
                    bools = {"true": True, "false": False, "1": True, "0": False}
                    return bools[value.lower()]
                except:
                    raise Exception(message)

            message = "HTTP 400: Unkown value type '%s' for '%s'." % (val_type, key)
            
            raise Exception(message)

        def process_value(key, value):
            
            val = None
            in_split = value.split(",")
            if len(in_split) > 1:
                return process_in_query(key, in_split)[key]
            operators = ["lt", "lte", "gt", "gte", "not", "eq", "null", "recfind", "reg"]
            for op in operators:
                if value.startswith(op + "="):
                    if op == "not":
                        tmpVal = re.compile("^"+ process_value(key, value.lstrip(op + "=")) + "$", re.IGNORECASE)
                    elif op == "eq":                        
                        tmpVal = process_value(key, value.lstrip(op + "="))
                        tmpVal = float(tmpVal)
                        return tmpVal
                    elif op == "null":
                        return None
                    elif op == "reg":
                        tmpVal = re.compile(process_value(key, value.lstrip(op + "=")), re.IGNORECASE)
                        return tmpVal
                    elif op == "recfind":
                        tmpVal = process_value(key, value.lstrip(op + "="))
                        par = self.dblayer.getRecParentNames(tmpVal,{})
                        return {"$in" : par}
                    else:
                        tmpVal = process_value(key, value.lstrip(op + "="))
                        if op in ["lt", "lte", "gt", "gte"]:
                            tmpVal = float(tmpVal)

                    val = {"$"+ op : tmpVal}
                    return val
            value_types = ["integer", "number", "string", "boolean"]
            for t in value_types:
                if value.startswith(t + ":"):
                    val = convert_value_type(key, value.split(t + ":")[1], t)
                    return val
            if key in ["ts", "ttl"] or op in ["lt", "lte", "gt", "gte"]:
                val = convert_value_type(key, value, "number")
                return val
            return value

        def process_exists_query(key, value):
            
            value = value[7:]
            or_q = []
            or_q.append({key: { "$exists": convert_value_type(key, value, "boolean") } })
            if value == "false":
                or_q.append({ key: None })
            return  { "$or": or_q }
                    
        def process_in_query(key, values):

            in_q = [] 
            for val in values:
                tmpVal = process_value(key, val)
                in_q.append(tmpVal)
            return {key: {"$in": in_q}}
                
        def process_or_query(key, values):
            
            or_q = []
            if key:
                or_q.append({key: process_value(key, values[0])})
                values = values[1:]
            for val in values:
                keys_split = val.split("=", 1)
                
                if len(keys_split) != 2:
                    raise Exception("HTTP 400: Not valid OR query.")
                k = keys_split[0]
                v = keys_split[1]
                or_q.append({k: process_value(k, v)})
            return {"$or": or_q}
        
        def process_and_query(key, values):
            
            and_q = []
            for val in values:
                split_or = val.split("|")
                if len(split_or) > 1:
                    and_q.append(process_or_query(key, split_or))
                    continue
                split = val.split(",")

                if len(split) == 1:
                    and_q.append({key: process_value(key, split[0])})
                else:
                    and_q.append(process_in_query(key, split))
            return {"$and": and_q}
        
        query = copy.copy(self.req.params)
        
        for k in query.keys():
            if type(query[k]) is not list:
                query[k] = [query[k]]

        # First Reterive special parameters
        # fields
        field_ls = self.req.get_param("fields", default="").split('neg=')
        
        state = 0 if len(field_ls) >= 2 else 1
        fields = {}
        if field_ls[-1]:
            fields = dict([(name, state) for name in field_ls.pop().split(',')])
        query.pop("fields", None)
        # max results
        limit = self.req.get_param("limit", default=None)
        query.pop("limit", None)
        if limit:
            limit = convert_value_type("limit", limit, "integer")
            
        # Get certificate
        cert = self.req.get_param("cert", default=None)
        query.pop("cert", None)
        
        skip = self.req.get_param("skip", default=0)
        query.pop("skip", None)
        if skip:
            skip = convert_value_type("skip", skip, "integer")

        inline = self.req.get_param("inline", default=False)
        if not inline==False:
            inline = True
        query.pop("inline", None)
        
        sort = self.req.get_param("sort", default = [])
        query.pop("sort", None)
        if sort:
            sortDict = { self.timestamp: -1 }
            sortStr = convert_value_type("sort", sort, "string")
            """ Parse sort options and create the array """
            sortStr = sortStr.split(",")
            for opt in sortStr:
                pair = opt.split(":")
                if (len(pair) > 1):
                    sortDict[pair[0]] = int(pair[1])
                else:
                    raise ValueError("sort parameter is not a tuple!")
            sort = list(sortDict.items())
        else:
            sortDict = { self.timestamp: -1 }
            sort = list(sortDict.items())

        unique = query.pop('unique', ['false']) != ['false']
        query_ret = []
        
        for arg in query:
            if isinstance(query[arg], list) and len(query[arg]) > 1:
                and_q = process_and_query(arg, query[arg])
                query_ret.append(and_q)
                continue
            query[arg] = ",".join(query[arg])
            if query[arg].startswith("reg="):
                param = decode(query[arg][4:])
                val = re.compile(process_value(arg,param), re.IGNORECASE)
                query_ret.append({arg: val})
                continue
            if query[arg].startswith("exists="):
                query_ret.append(process_exists_query(arg, query[arg]))
                continue
            split_or = query[arg].split("|")
            if len(split_or) > 1:
                query_ret.append(process_or_query(arg, split_or))
                continue
            split = query[arg].split(",")
            if len(split) > 1:
                in_q = process_in_query(arg, split)
                query_ret.append(in_q)
            else:
                query_ret.append({arg: process_value(arg, split[0])})
        if query_ret:
            query_ret = {"list": True, "query": {"$and": query_ret}}
        else:
            query_ret = {"list": False, "query": {}}

        # do any PPI query updates if there was an original query
        '''
        if getattr(self.application, '_ppi_classes', None):
            for pp in self.application._ppi_classes:
                ret = []
                ret = pp.process_query(ret, self.application, self.request,Handler=self)
                if query_ret["list"]:
                    for item in query_ret["query"]["$and"]:
                        ret.append(item)
                query_ret["query"].update({"$and": ret})           
        '''

        ret_val = {"fields": fields, "limit": limit, "query": query_ret, "skip": skip,
                   "sort": sort , "cert": cert, "inline": inline, "unique": unique}
        
        return ret_val
        
        
        
        
    def on_post(self, req, resp, res_id=None):
        
        #res_id = None
        self.timestamp = "ts"
        self.Id = "id"
        self.req = req
        self.resp = resp
        self.resource_name = req.path.split("/")[1]
        self.collection_name = Resources[self.resource_name]["collection_name"] 
        self.schemas_single = Resources[self.resource_name]["schema"]
        self._model_class = load_class(Resources[self.resource_name]["model_class"])
        self._accepted_mime = [MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML']]
        self._content_types_mime = [MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML'], MIME['HTML']]
        self.publisher = SubscriptionHandler()
        self.action = "POST"
        self._mongo = MongoClient('localhost', 27017)
        
        #print ("Hitting post req => {}".format(req))
        
        try:
            self._validate_request(res_id)
        except ValueError as exp:
            message = "Validation Error - {exp}".format(exp = exp)
            resp.status = falcon.HTTP_400
            resp.body = json.dumps(message, indent=4)
            self.log.error(message)
            return
        
        run_validate = (self.req.get_param("validate", default=None) != 'false')
        
        """
        Decode and create the resources
        """
        try:
            resources = self._get_documents()
        except ValueError as exp:
            resp.status = falcon.HTTP_400
            resp.body = json.dumps(str(exp), indent=4)
            self.log.error(str(exp))
            return
        
        if not isinstance(resources, list):
            resources = [resources]
        
        try:
            for index in range(len(resources)):
                tmpResource = self._process_resource(resources[index], res_id, run_validate)
                resources[index] = dict(tmpResource._to_mongoiter())
        except Exception as exp:
            message = "Not valid body - {exp}".format(exp = exp)
            resp.status = falcon.HTTP_400
            resp.body = json.dumps(message, indent=4)
            self.log.error(message)
            return
        
        """
        Insert resources
        """
        try:
            self._insert(resources)
        except Exception as exp:
            message = "Could not process the POST request - {exp}".format(exp = exp)
            resp.status = falcon.HTTP_409
            resp.body = json.dumps(message, indent=4)
            self.log.error(message)
            return
        
        """
        Return new records
        """
        buf = self._post_return(resources)
        
        accept = self.accept_content_type
        resp.set_header("Content-Type", accept + \
                        " ;profile="+ self.schemas_single[accept])
        resp.status = falcon.HTTP_201
        resp.body = json.dumps(buf, indent=2)

    def _insert(self, resources):
        
        self.insert(resources)
        self.publisher.publish(resources, self.collection_name, { "action": "POST" })
    
    def _insert_id(self, data):
        if "_id" not in data and not self.capped:
            res_id = data.get(self.Id, str(ObjectId()))
            timestamp = data.get(self.timestamp, int(time.time() * 1000000))
            data["_id"] = "%s:%s" % (res_id, timestamp)
    
    def insert(self, data, callback=None, summarize=True, **kwargs):
        """Inserts data to the collection."""
        
        self.capped = False
        self.manifests = "manifests"
                
        shards = []
        if isinstance(data, list) and not self.capped:
            for item in data:
                if summarize:
                    shards.append(self._create_manifest_shard(item))
                self._insert_id(item)
        elif not self.capped:
            if summarize:
                shards.append(self._create_manifest_shard(data))
            self._insert_id(data)

        futures = [self._mongo.unis_db[self.collection_name].insert(data, **kwargs)]
        if summarize:
            futures.append(self._mongo.unis_db[self.manifests].insert(shards))
        results = futures

        return results
   
    def _create_manifest_shard(self, resource):
        if "\\$collection" in resource:
            tmpResource = resource["properties"]
        else:
            tmpResource = resource
        tmpResult = {}
        tmpResult["properties"] = self._flatten_shard(tmpResource)
        tmpResult["$shard"] = True
        tmpResult["$collection"] = self.collection_name
        return dict(ObjectDict(tmpResult)._to_mongoiter())
    
    def _flatten_shard(self, resource):
        tmpResults = {}
        for key, value in resource.items():
            if type(value) == dict:
                tmpInner = self._flatten_shard(value)
                for k_i, v_i in tmpInner.items():
                    tmpResults["{key}.{inner}".format(key = key, inner = k_i)] = v_i
            elif type(value) == list:
                tmpResults[key] = value
            else:
                tmpResults[key] = [value]
                
        return tmpResults
        
    def _add_post_metadata(self, resource):
        uri = urlparse(self.req.url)
        try:
            resource["selfRef"] = "{scheme}://{netloc}/{col}/{uid}".format(scheme=uri.scheme,
                                                                           netloc=uri.netloc,
                                                                           col=uri.path.split("/")[1],
                                                                           uid = resource[self.Id])
            resource["$schema"] = resource.get("$schema", self.schemas_single[MIME['PSJSON']])
        except Exception as exp:
            self.log.error("failed to match uri - {e}".format(e = exp))
        
        return resource
        
    def _process_resource(self, resource, res_id = None, run_validate = True):
        
        tmpResource = self._model_class(resource)
        tmpResource = self._add_post_metadata(tmpResource)
                
        if tmpResource.get(self.timestamp) == None:
            tmpResource[self.timestamp] = int(time.time() * 1000000)
        
        if run_validate == True:
            tmpResource._validate()
            
        ppi_classes = [] #getattr(self.application, '_ppi_classes', [])
        for pp in ppi_classes:
            pp.pre_post(tmpResource, self.application, self.request, Handler = self)
            
        return tmpResource

    def _post_return(self, resources):
        
        query = {"$or": [ { self.Id: res[self.Id], self.timestamp: res[self.timestamp] } for res in resources ] }
        return self._return_resources(query)
        
    def _get_documents(self):
        
        if self.content_type == MIME['PSBSON']:
            if bson_valid:
                if not bson_valid(self.req.body):
                    raise ValueError("validate: not a bson document")
            try:
                body = bson_decode(self.req.body)
            except Exception as exp:
                raise ValueError("decode: not a bson document")
            
        if self.content_type == MIME['PSJSON']:
            try:
                body = self.req.json
            except Exception as exp:
                raise ValueError("malformatted json request - {exp}.".format(exp = exp))
        else:
            raise ValueError("No Post method is implemented for this content type")

        return body

    def _validate_request(self, res_id, require_id = False):
        
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defined for content of type '%s'" % \
                      (self.accept_content_type)
            resp.status = falcon.HTTP_500
            resp.body = json.dumps(message, indent=4)
            self.log.error(message)
            return False
        if require_id:
            if not res_id:
                message = "NetworkResource ID is not defined."
                raise ValueError(message)
        
        self._validate_psjson_profile()
        
        return True
        
    def _validate_psjson_profile(self):
        """
        Validates if the profile provided with the content-type is valid.
        """
        regex = re.compile(".*(?P<p>profile\=(?P<profile>[^\;\ ]*))")
        content_type = self.req.headers.get("Content-Type", "")

        # use the default schema
        if "profile" not in content_type:
            content_type += ";profile=" + \
                self.schemas_single[self.accept_content_type]
        match = re.match(regex, content_type)
        if not match:
            raise ValueError("Bad Content Type {content_type}".format(content_type = content_type))
        profile = match.groupdict().get("profile", None)
        if not profile:
            raise ValueError("Bad Content Type {content_type}".format(content_type = content_type))
        if profile != self.schemas_single[self.accept_content_type]:
            self.log.debug("Old or unexpected schema definition {schema}".format(schema = profile))
            
        return profile
        
    def _return_resources(self, query):

        try:
            response = []
            for doc in self._mongo.unis_db[self.collection_name].find(query):
                resource = ObjectDict._from_mongo(doc)
                response.append(resource)
        
            if len(response) == 1:
                location = self.req.url.split('?')[0]
                
                if not location.endswith(response[0][self.Id]):
                    location = location + "/" + response[0][self.Id]

                self.resp.set_header("Location", location)
                return response[0]
            else:
                return response
        except Exception as exp:
            raise ValueError(exp)

