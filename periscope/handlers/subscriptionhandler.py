#!/usr/bin/env python

import json
import tornado.websocket
import tornado.gen
import tornadoredis
from netlogger import nllog

import periscope.settings as settings
import subscriptionmanager

class SubscriptionHandler(tornado.websocket.WebSocketHandler, nllog.DoesLogging):
    def __init__(self, *args, **kwargs):
        super(SubscriptionHandler, self).__init__(*args, **kwargs)
        nllog.DoesLogging.__init__(self)
        self._manager = subscriptionmanager.GetManager()
        self.listening = False
        self.channels = []

    def open(self, resource_type = None, resource_id = None):
        self.log.info("New websocket connection: {ip}".format(ip = self.request.remote_ip))

        # Initialize the redis client for publishing.
        self.client = tornadoredis.Client()
        self.client.connect()

        # Wait for further subscription information
        if not resource_type:
            return

        query_string = self.get_argument("query", None)
        fields_string = self.get_argument("fields", None)
        query = {}
        fields = None
        
        self.log.info("Adding subscription to websocket: {ip} - {query}".format(ip = self.request.remote_ip, query = query_string))
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
            self.client.disconnect()
            self.client = None

        
    @tornado.gen.engine
    def listen(self, channel):
        yield tornado.gen.Task(self.client.subscribe, str(channel))

        if not self.listening:
            self.client.listen(self.deliver)
            self.listening = True
        
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
        resource_type = body.get("resourceType", None)
        
        self.log.info("Adding subscription to websocket: {ip} - {query}".format(ip = self.request.remote_ip, query = json.dumps(query)))
        self._addSubscription(resource_type, query, fields)
        
    def deliver(self, msg):
        if msg.kind == 'message':
            self.write_message(str(msg.body))
        if msg.kind == 'disconnect':
            self.write_message('This connection terminated '
                               'due to a Redis server error.')
            self.close()
    
    def on_close(self):
        if self.client and self.client.subscribed:
            for channel in self.channels:
                self._manager.removeChannel(channel)
                self.client.unsubscribe(channel)
                
            self.client.disconnect()
            
    def check_origin(self, origin):
        return True
    
    
    def _addSubscription(self, resource_type, query, fields):
        if resource_type:
            channel = self._manager.createChannel(query, resource_type, fields)
            self.channels.append(channel)
            self.listen(channel)




class AggSubscriptionHandler(SubscriptionHandler):
    def open(self, resource_type = None):
        try:
            self.log.info("ws_connect=%s" % self.request.remote_ip)
            query_string = self.get_argument("query", None)
            fields_string = self.get_argument("fields", None)
            query = {}
            fields = None
            # this works only for /data at the moment

            self.idDict = dict()
            self.fields = fields
	    self.resource_type = resource_type # [SGS-179]

            # This handler works with many channels, on_message
            self.client = tornadoredis.Client()
            self.client.connect()
        except Exception as exp:
            self.write_message('Error in subscription: %s' % exp)
            self.client = None
            return

    def on_close(self):
        if self.client and self.client.subscribed:
            for i in self.idDict.keys():
                self.dcChannel(i)
        self.client.disconnect()
        self.log.info("ws_disconnect=%s" % self.request.remote_ip)

    def dcChannel(self,id) :
        channel = self.idDict.get(id)
        self._manager.removeChannel(channel)
        self.client.unsubscribe(channel)
        # Remove the id from the map
        self.log.info("unsubscribe=%s" % id)
        self.idDict.pop(id)
    
    @tornado.gen.engine
    def listen(self, channel):
        yield tornado.gen.Task(self.client.subscribe, str(channel))
        if not self.listening:
            self.client.listen(self.deliver)
            self.listening = True
        
    def on_message(self, msg):
        try:
            query = {}
            msg_json = json.loads(msg)
            id = msg_json["id"]
            if msg_json.has_key("disconnect"):
                if (msg_json["disconnect"]):
                    self.dcChannel(id)
                    return
                
            # DO nothing if id is already registered
            if self.idDict.get(id):
                pass
            else:
                query['id'] = id
                channel = self._manager.createChannel(query, self.resource_type, self.fields) # [SGS-179]
                self.idDict[id] = channel
                self.listen(channel)
                self.log.info("subscribe=%s" % id)
        except Exception as exp:
            pass

