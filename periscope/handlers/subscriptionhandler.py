import json
import zmq
import time
from periscope.handlers.basehandler import BaseHandler

class SubscriptionHandler(BaseHandler):
        
    def publish(self, resources, collection_name, action):
        port = "5556"
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind("tcp://*:%s" % port)
        msg = {"headers" : {"action" : action, "collection" : collection_name}, "data" : resources[0]}
        time.sleep(1)
        socket.send(bytes("{}...{}".format(collection_name, msg), 'utf-8'))

