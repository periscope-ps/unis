#!/usr/bin/env python

import copy
import json
import re
import urllib2
from netlogger import nllog
import time
import traceback
from tornado.httpclient import HTTPError
import tornado.web
import tornado.gen

from periscope.db import dumps_mongo
from periscope.models import ObjectDict
from periscope.settings import MIME
from ssehandler import SSEHandler

import subscriptionmanager

import bson
if hasattr(bson, "dumps"):
    # standalone bson
    bson_decode = bson.loads
    bson_valid = None
else:
    # pymongo's bson
    bson_decode = bson.decode_all
    bson_valid = bson.is_valid

def decode(str):
    while True:
        dec = urllib2.unquote(str)
        if dec == str:
            break
        str = dec
    return dec


class NetworkResourceHandler(SSEHandler, nllog.DoesLogging):
    """Generic Network resources handler"""

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
                   collection_name=None,
            accepted_mime=[MIME['SSE'], MIME['PSJSON'], MIME['PSBSON'], MIME['PSXML']],
            content_types_mime=[MIME['SSE'], MIME['PSJSON'],
                                MIME['PSBSON'], MIME['PSXML'], MIME['HTML']]):
        """
        Initializes handler for certain type of network resources.

        Parameters:
        
        collection_name: name of the database collection name that
                        stores information about the network resource.
        
        base_url: the base the path to access this resource, e.g., /nodes
        
        schemas_single: a dictionary that represents the network
                        resources schema to be validated againest.
                        The dictionary is indexed by content-type.
        
        schemas_list: a dictionary that represents the listing of this
                        resources schema to be validated againest.
        
        allow_get: User client can issue HTTP GET requests to this resource
        
        allow_post: User client can issue HTTP POST requests to this resource
        
        allow_put: User client can issue HTTP PUT requests to this resource
        
        allow_delete: User client can issue HTTP DELETE requests to this
                        resource.

        
        tailable: The underlying database collection is a capped collection.
        """
        # TODO (AH): Add ability to Enable/Disable different HTTP methods
        #if not isinstance(dblayer, DBLayer):
        #    raise TypeError("dblayer is not instance of DBLayer")
        nllog.DoesLogging.__init__(self)
        self.Id = Id
        self.timestamp = timestamp
        self._dblayer = dblayer
        self._base_url = base_url
        self.schemas_single = schemas_single
        self.schemas_list = schemas_list
        self._allow_get = allow_get
        self._allow_post = allow_post
        self._allow_put = allow_put
        self._allow_delete = allow_delete
        self._accepted_mime = accepted_mime
        self._content_types_mime = content_types_mime
        self._tailable = tailable
        self._model_class = model_class
        self._subscriptions = subscriptionmanager.GetManager()
        self._collection_name = collection_name
        
        if self.schemas_single is not None and \
            MIME["JSON"] not in self.schemas_single and \
            MIME["PSJSON"] in self.schemas_single:
                self.schemas_single[MIME["JSON"]] = self.schemas_single[MIME["PSJSON"]]
        if tailable and allow_delete:
            raise ValueError("Capped collections do not support" + \
                            "delete operation")
    
    @property
    def dblayer(self):
        """Returns a reference to the DB Layer."""
        if not getattr(self, "_dblayer", None):
            raise TypeError("No DB layer is defined for this handler.")
        return self._dblayer
    
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
            raw = self.request.headers.get("Accept", MIME['PSJSON'])
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
                raise HTTPError(406,
                    "Unsupported accept content type '%s'" %
                    self.request.headers.get("Accept", None))
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
            raw = self.request.headers.get("Content-Type", MIME['PSJSON'])
            regex = re.findall(
                "(?P<type>\w+\/\w+(\+\w+)?)(;[^;,]*)?([ ]*,[ ]*)?",
                raw
            )
            content_type = [k[0] for k in regex]
            for accepted_mime in self._content_types_mime:
                if accepted_mime in content_type:
                    self._content_type = accepted_mime
                    return self._content_type
            raise HTTPError(415,
                "Unsupported content type '%s'" %
                    self.request.headers.get("Content-Type", ""))
        return self._content_type
    
    @property
    def supports_streaming(self):
        """
        Returns true if the client asked for HTTP Streaming support.
        
        Any request that is of type text/event-stream or application/json
        with Connection = keep-alive is considered a streaming request
        and it's up to the client to close the HTTP connection.
        """
        if self.request.headers.get("Connection", "").lower() == "keep-alive":
            return self.request.headers.get("Accept", "").lower() in \
                    [MIME['PSJSON'], MIME['SSE']]
        else:
            return False
                        
        
    def write_error(self, status_code, **kwargs):
        """
        Overrides Tornado error writter to produce different message
        format based on the HTTP Accept header from the client.
        """
        if self.settings.get("debug") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            content_type = self.accept_content_type or MIME['PSJSON']
            self.set_header("Content-Type", content_type)
            result = "{"
            for key in kwargs:
                result += '"%s": "%s",' % (key, kwargs[key])
            result = result.rstrip(",") + "}\n"
            self.write(result)
            self.finish()

    def set_default_headers(self):
        # Headers to allow cross domains requests to UNIS
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with')
        
        
    def _parse_get_arguments(self):
        """Parses the HTTP GET areguments given by the user."""
        def convert_value_type(key, value, val_type):
            if val_type == "integer":
                try:
                    return int(value)
                except:
                    raise HTTPError(400,
                        message="'%s' is not of type '%s'" % (key, val_type))
            if val_type == "number":
                try:
                    return float(value)
                except:
                    raise HTTPError(400,
                        message="'%s' is not of type '%s'" % (key, val_type))
            if val_type == "string":
                try:
                    return unicode(value)
                except:
                    raise HTTPError(400,
                        message="'%s' is not of type '%s'" % (key, val_type))
            if val_type == "boolean":
                try:
                    bools = {"true": True, "false": False, "1": True, "0": False}
                    return bools[value.lower()]
                except:
                    raise HTTPError(400,
                        message="'%s' is not of type '%s'" % (key, val_type))
            raise HTTPError(400,
                        message="Unkown value type '%s' for '%s'." % (val_type, key))
            
        def process_value(key, value):
            val = None
            in_split = value.split(",")
            if len(in_split) > 1:
                return process_in_query(key, in_split)[key]
            operators = ["lt", "lte", "gt", "gte","not","eq","null"]
            for op in operators:
                if value.startswith(op + "="):
                    if op == "not":
                        tmpVal = re.compile("^"+process_value(key, value.lstrip(op + "=")) + "$", re.IGNORECASE)
                    elif op == "eq":                        
                        tmpVal = process_value(key, value.lstrip(op + "="))
                        tmpVal = float(tmpVal)
                        return tmpVal
                    elif op =="null":
                        return None
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
            in_q = [process_value(key, val) for val in values]       
            return {key: {"$in": in_q}}
        
        def process_or_query(key, values):
            or_q = []
            if key:
                or_q.append({key: process_value(key, values[0])})
                values = values[1:]
            for val in values:
                keys_split = val.split("=", 1)
                if len(keys_split) != 2:
                    raise HTTPError(400, message="Not valid OR query.")
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
        
        query = copy.copy(self.request.arguments)
        # First Reterive special parameters
        # fields
        fields = self.get_argument("fields", {})
        query.pop("fields", None)
        if fields:
            fields = dict([(name, 1) for name in fields.split(",")])
        # max results
        limit = self.get_argument("limit", default=None)
        query.pop("limit", None)
        if limit:
            limit = convert_value_type("limit", limit, "integer")

        # Get certificate
        cert = self.get_argument("cert", default=None)
        query.pop("cert", None)
        
        skip = self.get_argument("skip", default=0)
        query.pop("skip", None)
        if skip:
            skip = convert_value_type("skip", skip, "integer")
            
        sort = self.get_argument("sort", default=None)
        query.pop("sort", None)
        if sort:
            sortDict = {}
            sortStr = convert_value_type("sort", sort, "string")
            """ Parse sort options and create the array """
            sortStr = sortStr.split(",")
            for opt in sortStr:
                pair = opt.split(":")
                sortDict[pair[0]] = pair[1]
            sortDict[self.timestamp] = "-1"
            sort = sortDict.items()

            
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
        if getattr(self.application, '_ppi_classes', None):
            for pp in self.application._ppi_classes:
                ret = []                
                ret = pp.process_query(ret, self.application, self.request,Handler=self)
                if query_ret["list"]:
                    for item in query_ret["query"]["$and"]:
                        ret.append(item)
                query_ret["query"].update({"$and": ret})        
        ret_val = {"fields": fields, "limit": limit, "query": query_ret , "skip" : skip , "sort" : sort , "cert" : cert}
        return ret_val
    
    

    # Template Method for GET
    @tornado.web.asynchronous
    @tornado.web.removeslash
    @tornado.gen.coroutine
    def get(self, res_id = None, *args):
        super(NetworkResourceHandler, self).get(*args)

        # Parse arguments and set up query
        try:
            parsed = self._parse_get_arguments()
            options = dict(query  = parsed["query"]["query"],
                           fields = parsed["fields"],
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
        
        keep_alive = self.supports_streaming or self.supports_sse()
        if keep_alive and self._tailable:
            # This spins off a perpetual connection
            self._get_tailable(query = options["query"], fields = options["fields"])
        else:
            try:
                cursor = self._find(**options)
            except Exception as exp:
                self.write_error(404, message = "Could not find resource - {exp}".format(exp = exp))
                return
            
            try:
                count = yield self._write_get(cursor)
            except Exception as exp:
                self.write_error(500, message = "Failure during post processing - {exp}".format(exp = exp))
                return
            
            yield self._add_response_headers(count)
            self.set_status(201)
            self.finish()
            
    def _find(self, **kwargs):
        return self.dblayer.find(**kwargs)
    
    @tornado.gen.coroutine
    def _add_response_headers(self, count):
        accept = self.accept_content_type
        self.set_header("Content-Type", accept + "; profile=" + self.schemas_single[accept])
        
        self.set_header('X-Count', count)

        raise tornado.gen.Return(count)
    
    @tornado.gen.coroutine
    def _write_get(self, cursor):
        count = yield cursor.count()
        if not count:
            self.write('[]')
            raise tornado.gen.Return(count)
        elif count > 1:
            self.write('[\n')

        # Write first entry
        yield cursor.fetch_next
        resource = cursor.next_object()
        resource = yield self._post_get(resource)
        json_response = dumps_mongo(resource, indent=2).replace('\\\\$', '$').replace('$DOT$', '.')
        self.write(json_response)
        
        while (yield cursor.fetch_next):
            self.write(',\n')
            resource = cursor.next_object()
            resource = yield self._post_get(resource)
            json_response = dumps_mongo(resource, indent=2).replace('\\\\$', '$').replace('$DOT$', '.')
            self.write(json_response)
            
        if count > 1:
            self.write('\n]')
            
        raise tornado.gen.Return(count)

    @tornado.gen.coroutine
    def _post_get(self, resource):
        raise tornado.gen.Return(resource)
    
    @tornado.gen.coroutine
    def _get_tailable(self, query, fields):
        cursor = self._find(query      = query,
                            fields     = fields,
                            tailable   = True,
                            await_data = True)
        self.write('[')
        first = True
        while True:
            if not cursor.alive:
                self.write(']')
                self.finish()
            if (yield cursor.fetch_next):
                if not first:
                    self.write(',')
                else:
                    first = False
                resource = cursor.next_object()
                json_resonse = dumps_mongo(response, indent=2).replace('\\\\$', '$').replace('$DOT$', '.')
                self.write(json_response)
                
    
    # Template Method for POST
    @tornado.web.asynchronous
    @tornado.web.removeslash
    @tornado.gen.coroutine
    def post(self, res_id=None):
        try:
            self._validate_request(res_id)
        except ValueError as exp:
            self.write_error(400, message = "Validation Error - {exp}".format(exp = exp))
            return
        
        run_validate = (self.get_argument("validate", None) != 'false')
        
        """
        Decode and create the resources
        """
        try:
            resources = self._get_json()
        except ValueError as exp:
            self.write_error(400, message = exp)
            return
        
        if not isinstance(resources, list):
            resources = [resources]
        
        try:
            for index in range(len(resources)):
                tmpResource = yield self._process_resource(resources[index], res_id, run_validate)
                resources[index] = dict(tmpResource._to_mongoiter())
        except Exception as exp:
            self.write_error(400, message="Not valid body - {exp}".format(exp = exp))
            return
        
        """
        Insert resources
        """
        try:
            yield self._insert(resources)
        except Exception as exp:
            self.write_error(409, message = "Could not process the POST request - {exp}".format(exp = exp))
            return
        
        """
        Return new records
        """        
        try:
            yield self._post_return(resources)
        except ValueError as exp:
            self.write_error(409, message = "Could not process reponse - {exp}".format(exp = exp))
            return
        except Exception as exp:
            self.write_error(404, message = "Post did not return any data - {exp}".format(exp = exp))
            return
        
        accept = self.accept_content_type
        self.set_header("Content-Type", accept + \
                        " ;profile="+ self.schemas_single[accept])
        self.set_status(201)
        self.finish()

    @tornado.gen.coroutine
    def _insert(self, resources):
        yield self.dblayer.insert(resources)

    @tornado.gen.coroutine
    def _process_resource(self, resource, res_id = None, run_validate = True):
        tmpResource = self._model_class(resource)
        tmpResource = self._add_post_metadata(tmpResource, res_id)

        if run_validate == True:
            tmpResource._validate()
            
        ppi_classes = getattr(self.application, '_ppi_classes', [])
        for pp in ppi_classes:
            pp.pre_post(tmpResource, self.application, self.request, Handler = self)
            
        raise tornado.gen.Return(tmpResource)

    @tornado.gen.coroutine
    def _post_return(self, resources):
        query = {"$or": [ { self.Id: res[self.Id], self.timestamp: res[self.timestamp] } for res in resources ] }
        yield self._return_resources(query)
        
        
    # Template Method for PUT
    @tornado.web.asynchronous
    @tornado.web.removeslash
    @tornado.gen.coroutine
    def put(self, res_id=None):
        try:
            self._validate_request(res_id, require_id = True)
        except ValueError as exp:
            self.write_error(400, message = "Validation Error - {exp}".format(exp = exp))
            return
        
        try:
            resource = self._get_json()
            resource = self._model_class(resource, auto_id = False)
            resource = self._add_post_metadata(resource)
        except ValueError as exp:
            self.write_error(400, message = exp)
            return
        
        if self.Id not in resource:
            resource[self.Id] = res_id
            
        if resource[self.Id] != res_id:
            self.write_error(400,
                message="Different ids in the URL" + \
                 "'%s' and in the body '%s'" % (body[self.Id], res_id))
            return
        
        try:
            resource._validate()
        except Exception as exp:
            self.write_error(400, message="Not valid body " + str(exp))
            return
        
        """
        Update resources
        """
        try:
            self._put_resource(resource)
        except Exception as exp:
            self.write_error(409, message = "Could not process the POST request - {exp}".format(exp = exp))
            return
        
        accept = self.accept_content_type
        self.set_header("Content-Type", accept + \
                        " ;profile="+ self.schemas_single[accept])
        self.set_status(201)
        
        try:
            query = { self.Id: resource[self.Id], self.timestamp: resource[self.timestamp]  }
            yield self._return_resources(query)
        except ValueError as exp:
            self.write_error(409, message = "Could not process reponse - {exp}".format(exp = exp))
            return
        self.finish()
    
    @tornado.gen.coroutine
    def _update(self, query, resource):
        yield self.dblayer.update(query, resource)

    @tornado.gen.coroutine
    def _put_resource(self, resource):
        query = { self.Id: resource[self.Id] }
        yield self._update(query, dict(resource._to_mongoiter()))

    
    @tornado.web.asynchronous
    @tornado.web.removeslash
    @tornado.gen.coroutine
    def delete(self, res_id=None):
        try:
            self._validate_request(res_id, require_id = True)
        except ValueError as exp:
            self.write_error(400, message = "Validation Error - {exp}".format(exp = exp))
            return
        
        res_ids = []
        cursor = self._find(query = { self.Id: res_id }, projection = { "_id": False, self.Id: True })
        while (yield cursor.fetch_next):
            resource = cursor.next_object()
            res_ids.append(resource[self.Id])
            
        update = { "status": "DELETED", self.timestamp: int(time.time() * 1000000) }
        query = {"$or": res_ids }
        yield self.dblayer.update(query, update)
        self.finish()

        
    def _get_json(self):
        if self.content_type == MIME['PSBSON']:
            if bson_valid:
                if not bson_valid(self.request.body):
                    raise ValueError("validate: not a bson document")
            try:
                body = bson_decode(self.request.body)
            except Exception as exp:
                raise ValueError("decode: not a bson document")
            
        elif self.content_type == MIME['PSJSON']:
            try:
                body = json.loads(self.request.body)
            except Exception as exp:
                raise ValueError("malformatted json request - {exp}.".format(exp = exp))
        else:
            raise ValueError("No Post method is implemented for this content type")
        
        return body

    def _validate_request(self, res_id, allow_id = False, require_id = False):
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defined for content of type '%s'" % \
                      (self.accept_content_type)
            self.write_error(500, message=message)
            return False
        if not allow_id and res_id:
            message = "NetworkResource ID should not be defined."
            raise ValueError(message)
        if require_id and not res_id:
            message = "NetworkResource ID is not defined."
            raise ValueError(message)
        
        self._validate_psjson_profile()
        
        return True
    
    def _add_post_metadata(self, resource, res_id = None):
        if res_id:
            resource[self.Id] = res_id
        
        resource["selfRef"] = "{host}/{rid}".format(host = self.request.full_url().split('?')[0],
                                                       rid  = resource[self.Id])
        resource["$schema"] = resource.get("$schema", self.schemas_single[MIME['PSJSON']])
        
        if resource["$schema"] != self.schemas_single[self.accept_content_type]:
            raise ValueError("Bad schema")
        return resource

    @tornado.gen.coroutine
    def _return_resources(self, query):
        try:
            cursor = self._find(query = query)
            response = []
            while (yield cursor.fetch_next):
                resource = cursor.next_object()
                response.append(ObjectDict._from_mongo(resource))
                self._subscriptions.publish(resource, self._collection_name)
        
            if len(response) == 1:
                location = self.request.full_url().split('?')[0]
                if not location.endswith(response[0][self.Id]):
                    location = location + "/" + response[0][self.Id]

                self.set_header("Location", location)
                self.write(dumps_mongo(response[0], indent=2))
            else:
                self.write(dumps_mongo(response, indent=2))
        except Exception as exp:
            raise ValueError(exp)
        
    def _validate_psjson_profile(self):
        """
        Validates if the profile provided with the content-type is valid.
        """
        regex = re.compile(".*(?P<p>profile\=(?P<profile>[^\;\ ]*))")
        content_type = self.request.headers.get("Content-Type", "")
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
            raise ValueError("Bad Schema {schema}".format(schema = profile))
        return profile
