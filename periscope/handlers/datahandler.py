#!/usr/bin/env python

import json
import functools
import tornado.web
from asyncmongo.errors import IntegrityError, TooManyConnections

import periscope.settings as settings
from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler


class DataHandler(NetworkResourceHandler):        
        
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
        #if res_id:
        #    message = "NetworkResource ID should not be defined."
        #    self.send_error(400, message=message)
        #    return
        self._res_id=res_id
        #Load the appropriate content type specific POST handler
        if self.content_type == MIME['PSJSON']:
            self.post_psjson()
        elif self.content_type == MIME['PSBSON']:
            self.post_psbson()
        else:
            self.send_error(500,
                message="No POST method is implemented for this content type")
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
        
        if return_resources:
            query = {"$or": []}
            for res_ref in res_refs:
                query["$or"].append(res_ref)
            self.dblayer.find(query, self._return_resources)
        else:
            if last:
                accept = self.accept_content_type
                self.set_header("Content-Type", accept + \
                                " ;profile="+ self.schemas_single[accept])
                if len(res_refs) == 1:
                    self.set_header("Location",
                                    "%s/%s" % (self.request.full_url().split('?')[0], res_refs[0][self.Id]))
                
                self.set_status(201)
                #pool = self.application.async_db._pool
                #pool.close()
                self.finish()   
                     
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

        ''' Let's not add properties into each /data object
            Should protect the collection instead

        try:
            for pp in self.application._ppi_classes:
                pp.pre_post(body, self.application, self.request)
        except Exception, msg:
            self.send_error(400, message=msg)
            return
        '''

        if self._res_id:
            res_refs =[]
            if self._res_id in self.application.sync_db.collection_names():
                callback = functools.partial(self.on_post,
                        res_refs=res_refs, return_resources=False,last=True)
                try:
                    self.application.async_db[self._res_id].insert(body["data"], callback=callback)
                except TooManyConnections:
                    self.send_error(503, message="Too many DB connections")
                    return
                
                push_data = {'id': self._res_id,
                             'data': body["data"],
                             }
                self._subscriptions.publish(push_data, self._collection_name, trim_published_resource)
            else:
                self.send_error(400, message="The collection for metadata ID '%s' does not exist" % self._res_id)
                return
        else:
            col_names = self.application.sync_db.collection_names()
            data={}
            for i in range(0,body.__len__()):
                mid = body[i]['mid']
                dataraw = body[i]['data']
                if(mid in data.keys()):
                    data[mid].extend(dataraw)
                else :
                    data[mid]=dataraw
                   
            mids = data.keys()
            
            for i in range(0,mids.__len__()):    
                res_refs =[]
                if mids[i] in col_names:
                    if i+1 == mids.__len__():
                        callback = functools.partial(self.on_post,
                                                     res_refs=res_refs, return_resources=False,last=True)
                    else:
                        callback = functools.partial(self.on_post,
                                                     res_refs=res_refs, return_resources=False,last=False)
                    try:
                        self.application.async_db[mids[i]].insert(data[mids[i]], callback=callback)
                    except TooManyConnections:
                        self.send_error(503, message="Too many DB connections")
                        return
                    
                    push_data = {'id': mids[i],
                                 'data': data[mids[i]],
                                 }
                    self._subscriptions.publish(push_data, self.collection_name, trim_published_resource)
                else:
                    self.send_error(400, message="The collection for metadata ID '%s' does not exist" % mids[i])
                    return

    @tornado.web.asynchronous
    @tornado.web.removeslash
    def get(self, res_id=None):
        """Handles HTTP GET"""
        accept = self.accept_content_type
        if res_id:
            self._res_id = unicode(res_id)
        else:
            self.send_error(500, message="You need to specify the metadata ID in the URL while querying the data")
            return
        
        try:
            parsed = self._parse_get_arguments()
        except Exception, msg:
            return self.send_error(403, message=msg)
        query = parsed["query"]["query"]
        fields = parsed["fields"]
        fields["_id"] = 0
        limit = parsed["limit"]
        if limit == None:
            limit = 1000000000

        is_list = True #, not res_id
        if query:
            is_list = True
        callback = functools.partial(self._get_on_response,
                                     new=True, is_list=is_list, query=query)
        self._find(query, callback, fields=fields, limit=limit)

    def _find(self, query, callback, fields=None, limit=None,sort=None):
        """Query the database.

        Parameters:

        callback: a function to be called back in case of new data.
                callback function should have `response`, `error`,
                and `new` fields. `new` is going to be True.
        """
        keep_alive = self.supports_streaming or self.supports_sse()
        if self._res_id:
            query[self.Id] = self._res_id
        options = dict(query=query, callback=callback)#, await_data=True)
        # Makes it a tailable cursor
        if keep_alive and self._tailable:
            options.update(dict(tailable=True, timeout=False))
        if fields:
            options["fields"] = fields
        if limit:
            options["limit"] = limit

        if "sort" not in options:
            options["sort"] = []        
        IsTsPresent = False
        if sort :                         
            """ Parse sort options and create the array """
            sortStr = sort                        
            """ Split it and then add it to array"""
            sortOpt = sortStr.split(",")
            for opt in sortOpt :
                x = opt.split(":")
                if x[0] == "ts":
                    IsTsPresent = True
                try :                    
                    options["sort"].append((x[0],int(x[1])))                
                except:
                    """ Ignore , """
                    #print "Sort takes integer argument 1 or -1 "                
                    #self.set_header('X-error', "Sort takes integer argument 1 or -1")
        if not IsTsPresent:
            options["sort"].append(("ts", -1))
            
        self._query = query
        db_layer = self.application.get_db_layer(self._res_id, "ts", "ts",
                                                 True,  5000)
        logger.info('periscope.datahandler._find '+ "".join(str(x) for x in options["sort"]))
        query.pop("id", None)
        options['ccallback'] = self.countCallback
        self.countFinished = False 
        self.mainFinished = False
        self._cursor = db_layer.find(**options)

    def trim_published_resource(self, resource, fields):
        return {resource['id']: resource['data']}
