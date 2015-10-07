#!/usr/bin/env python

import tornado.web
import copy
import json
import functools
import time
from tornado.httpclient import AsyncHTTPClient
from asyncmongo.errors import IntegrityError

import periscope.settings as settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class EventsHandler(NetworkResourceHandler):        
        
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def post(self, res_id=None):
        # Check if the schema for conetnt type is known to the server
        if self.accept_content_type not in self.schemas_single:
            message = "Schema is not defiend fot content of type '%s'" % \
                        (self.accept_content_type)
            self.send_error(500, message=message)
            return
        # POST requests don't work on specific IDs
        if res_id:
            message = "NetworkResource ID should not be defined."
            self.send_error(400, message=message)
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

    def on_post(self, request, error=None, res_refs=None, return_resources=True, last=True):
        """
        HTTP POST callback to send the results to the client.
        """
        
        if error:
            if isinstance(error, IntegrityError):
                self.send_error(409,
                    message="Could't process the POST request '%s'" % \
                        str(error).replace("\"", "\\\""))
            else:
                self.send_error(500,
                    message="Could't process the POST request '%s'" % \
                        str(error).replace("\"", "\\\""))
            return                
        self.set_status(201)
        #pool = self.application.async_db._pool
        #pool.close()
        self.finish()

    def verify_metadata(self, response, collection_size, post_body):
        if response.error:
            self.send_error(400, message="metadata is not found '%s'." % response.error)
        else:
            # (EK): FIX: body came back as an array in some cases, why?
            body=json.loads(response.body)
            if body["id"] not in self.application.sync_db.collection_names():
                self.application.get_db_layer(body["id"],"ts","ts",True,collection_size)
                self.set_header("Location","%s/data/%s" % (self.request.full_url().split('?')[0], body["id"]))
                callback = functools.partial(self.on_post,
                                             res_refs=None, return_resources=True)
                post_body["ts"] = int(time.time() * 1000000)
                post_body["id"] = body["id"]
                self.dblayer.insert(post_body, callback=callback)
            else:
                self.send_error(401, message="event collection exists already")  
            
    def post_psjson(self):
        """
        Handles HTTP POST request with Content Type of PSJSON.
        """
        profile = self._validate_psjson_profile()
        if not profile:
            return
        try:
            body = json.loads(self.request.body)
        except Exception as exp:
            self.send_error(400, message="malformatted json request '%s'." % exp)
            return
        

        callback = functools.partial(self.verify_metadata,
                                     collection_size=body["collection_size"], post_body=body)
        
        http_client = AsyncHTTPClient()
        http_client.fetch(body["metadata_URL"],
                          validate_cert=False,
                          client_cert=settings.MS_CLIENT_CERT,
                          client_key=settings.MS_CLIENT_KEY,
                          callback=callback)

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

       
    def generate_response(self,query,mid,response,index):
        try:
            command={"collStats":mid,"scale":1}
            generic = self.application.sync_db.command(command)
        except Exception as exp:
            self.send_error(400, message="At least one of the metadata ID is invalid.")
            return False
        
        self.del_stat_fields(generic)
        specific={}
        if 'ts' in self.request.arguments.keys():       
            criteria=self.request.arguments['ts'][0].split('=')
            
            if criteria[0]=='gte':
                specific["startTime"]=int(criteria[1])
            if criteria[0]=='lte':
                specific["endTime"]=int(criteria[1])
            
            if self.request.arguments['ts'].__len__() > 1 :            
                criteria=self.request.arguments['ts'][1].split('=')
                if criteria[0]=='gte':
                    specific["startTime"]=int(criteria[1])
                if criteria[0]=='lte':
                    specific["endTime"]=int(criteria[1])
            
            db_query=copy.deepcopy(query)
            del db_query["$and"][index]
            specific["numRecords"]=self.application.sync_db[mid].find(db_query).count()
            
        response.insert(0,{})
        response[0]["mid"]=mid
        response[0]["generic"]=generic
        response[0]["queried"]=specific

        return True
                                            
    @tornado.web.asynchronous
    @tornado.web.removeslash
    def get(self, res_id=None):
        """Handles HTTP GET"""
        accept = self.accept_content_type
        if res_id:
            self._res_id = unicode(res_id)
        else:
            self._res_id = None
            
        try:
            parsed = self._parse_get_arguments()
        except Exception, msg:
            return self.send_error(403, message=msg)
        query = parsed["query"]["query"]
        fields = parsed["fields"]
        limit = parsed["limit"]
        is_list = not res_id
        self.set_header("Content-Type", "application/json")
        if query.__len__() == 0:
            if self._res_id is None:
                q = {}
            else:
                q = {"id": self._res_id}
            cursor =  self.application.sync_db["events_cache"].find(q)
            index = -1
            response = []
            obj = next(cursor,None)
            while obj:
                index = index+1
                mid = obj["metadata_URL"].split('/')[obj["metadata_URL"].split('/').__len__() - 1]
                if not self.generate_response(query,mid,response,index):
                    return
                obj = next(cursor, None)
            try:
                json_response = dumps_mongo(response, indent=2)
                self.write(json_response)
                self.finish()
            except Exception as exp:
                self.send_error(400, message="1 At least one of the metadata ID is invalid.")
                return                
        else:
            index=-1
            response=[]
            for d in query["$and"]:
                index=index+1
                if 'mids' in d.keys():
                    if isinstance(d["mids"],dict):
                        for m in d['mids']['$in']:
                            if not self.generate_response(query,m,response,index):
                                return
                    else:
                        if not self.generate_response(query,d['mids'],response,index):
                            return
            try:
                json_response = dumps_mongo(response, indent=2)
                self.write(json_response)
                self.finish()
            except Exception as exp:
                self.send_error(400, message="1 At least one of the metadata ID is invalid.")
                return
