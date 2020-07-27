import json
import zmq
import time
from periscope.handlers.basehandler import BaseHandler

class SubscriptionHandler(BaseHandler):
        
    def publish(self, resources, collection = None, headers = {}, trim_function = None):
        
        resources = resources if isinstance(resources, list) else [resources]
        for resource in resources:
            if "_id" in resource:
                del resource["_id"]
            self._publish(resource, collection, headers, trim_function)
            
    def _publish(self, resource, collection = None, headers = {}, trim_function = None):
        port = "5556"
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind("tcp://*:%s" % port)
        
        trim = trim_function or self.trim_published_resource
        trimmed_resource = trim(resource, None)
        headers["collection"] = headers.get("collection", collection)
        headers["id"] = headers.get("id", resource["id"])
        
        message = {
                    "headers": headers,
                    "data": trimmed_resource
                  }
                
        #msg = {"headers" : headers, "data" : resources[0]}
        time.sleep(1)
        socket.send(bytes("{}...{}".format(collection, message), 'utf-8'))
        
    def trim_published_resource(self, resource, fields):
    
        result = {}
        if fields == None:
            return resource
        else:
            for field in fields:
                result[field] = resource[field]
            
            return result

