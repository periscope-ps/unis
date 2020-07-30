import json
import zmq
import time
from periscope.handlers.basehandler import BaseHandler

__manager__ = None

def GetSubscriptionManager():
    global __manager__
    
    
    if not __manager__:
        __manager__ = SubscriptionHandler()
        __manager__.socket_bind()

    return __manager__
    
class SubscriptionHandler(BaseHandler):

    def __init__(self):
        self.socket = None
        
    def publish(self, resources, collection = None, headers = {}, trim_function = None):
        
        resources = resources if isinstance(resources, list) else [resources]
        for resource in resources:
            if "_id" in resource:
                del resource["_id"]
            self._publish(resource, collection, headers, trim_function)
            
    def socket_bind(self):
    
        if self.socket is None:
            port = "5556"
            context = zmq.Context()
            self.socket = context.socket(zmq.PUB)
            self.socket.bind("tcp://*:%s" % port)
        
        return self.socket
            
    def _publish(self, resource, collection = None, headers = {}, trim_function = None):
        
        trim = trim_function or self.trim_published_resource
        trimmed_resource = trim(resource, None)
        headers["collection"] = headers.get("collection", collection)
        headers["id"] = headers.get("id", resource["id"])
        
        message = {
                    "headers": headers,
                    "data": trimmed_resource
                  }
                
        self.socket.send(bytes("{}...{}".format(collection, message), 'utf-8'))
        
    def trim_published_resource(self, resource, fields):
    
        result = {}
        if fields == None:
            return resource
        else:
            for field in fields:
                result[field] = resource[field]
            
            return result

