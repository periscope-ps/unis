#!/usr/bin/env python

import json
import tornado.websocket
import tornado.gen
import tornadoredis
from netlogger import nllog

import periscope.settings
from subscriptionmanager import SubscriptionManager

class SubscriptionHandler(tornado.websocket.WebSocketHandler, nllog.DoesLogging):
    def __init__(self, *args, **kwargs):
        super(SubscriptionHandler, self).__init__(*args, **kwargs)
        nllog.DoesLogging.__init__(self)
        self._manager = SubscriptionManager()
        self.listening = False

    def open(self, resource_type = None, resource_id = None):
        try:
            query_string = self.get_argument("query", None)
            fields_string = self.get_argument("fields", None)
            query = {}
            fields = None

            if query_string:
                query = json.loads(query_string)

            if fields_string:
                fields = fields_string.split(',')                
            query['\\$schema'] = settings.SCHEMAS[resource_type]
            if resource_id:
                query['id'] = resource_id

            # This handler only handles one channel, on open
            self.channel = self._manager.createChannel(query, fields)
            self.listen()
        except Exception as exp:
            self.write_message('Error in subscription: %s' % exp)
            self.client = None
            return
        
    @tornado.gen.engine
    def listen(self):
        self.client = tornadoredis.Client()
        self.client.connect()
        yield tornado.gen.Task(self.client.subscribe, str(self.channel))
        self.client.listen(self.deliver)
        self.listening = True
        
    def on_message(self, msg):
        pass
        
    def deliver(self, msg):
        if msg.kind == 'message':
            self.write_message(str(msg.body))
        if msg.kind == 'disconnect':
            self.write_message('This connection terminated '
                               'due to a Redis server error.')
            self.close()
    
    def on_close(self):
        if self.client and self.client.subscribed:
            self.client.unsubscribe(self.channel)
            self.client.disconnect()
            
    def check_origin(self, origin):
        return True





class AggSubscriptionHandler(SubscriptionHandler):
    def open(self, resource_type = None):
        global query_list
        try:
            self.log.info("ws_connect=%s" % self.request.remote_ip)
            query_string = self.get_argument("query", None)
            fields_string = self.get_argument("fields", None)
            query = {}
            fields = None
            # this works only for /data at the moment

            self.idDict = dict()
            self.fields = fields

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
                channel = self._manager.createChannel(query, self.fields)
                self.idDict[id] = channel
                self.listen(channel)
                self.log.info("subscribe=%s" % id)
        except Exception as exp:
            pass

