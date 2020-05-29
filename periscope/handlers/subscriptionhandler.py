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
import tornado.websocket
import tornado.gen

import periscope.settings as settings
import periscope.handlers.subscriptionmanager as subscriptionmanager

class SubscriptionHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(SubscriptionHandler, self).__init__(*args, **kwargs)
        self.log = self.application.log
        self.listening = False
        self.channels = []
        self._manager = subscriptionmanager.GetManager()
    
    @tornado.gen.coroutine
    def open(self, resource_type = None, resource_id = None):
        self.log.info("New websocket connection: {ip}".format(ip = self.request.remote_ip))
        
        # Wait for further subscription information
        if not resource_type:
            raise tornado.gen.Return()
        
        query_string = self.get_argument("query", None)
        fields_string = self.get_argument("fields", None)
        query = {}
        fields = None
        
        try:
            if query_string:
                query = json.loads(query_string)
            if fields_string:
                fields = fields_string.split(',')
            if resource_id:
                query['id'] = resource_id
            
            self._addSubscription(resource_type, query, fields)
        except ValueError as exp:
            self.write_message('Could not decode subscripition query: %s' % exp)
            self.log.warn('Could not decode subscription query: {exp} - {query}'.format(exp = exp, query = query_string))

    def on_message(self, msg):
        body = None
        try:
            body = json.loads(msg)
        except ValueError as exp:
            error = "Could not decode subscription query."
            self.log.warn(error)
            self.write_message(error)
            return
        
        query = body.get("query", {})
        fields = body.get("fields", None)
        address = body.get("resourceType", "").split("/")
        resource_type = address[0]
        if len(address) == 2:
            query["id"] = address[1]
        
        self._addSubscription(resource_type, query, fields)
        
    def deliver(self, msg):
        self.write_message(str(msg))
    
    def on_close(self):
        for channel in self.channels:
            self._manager.removeChannel(channel, self)
            
    def check_origin(self, origin):
        return True
    
    def _addSubscription(self, resource_type, query, fields):
        if resource_type:
            self.log.info("Adding subscription to websocket[{resource_type}]: {ip} - {query}".format(resource_type = resource_type, ip = self.request.remote_ip, query = query))
            channel = self._manager.createChannel(query, resource_type, fields, self)
            self.channels.append(channel)
