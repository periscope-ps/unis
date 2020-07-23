import json
from pymongo import MongoClient
from uuid import uuid4
from periscope.settings import MIME, Resources
from periscope.handlers.basehandler import BaseHandler

class AboutHandler(BaseHandler):
        
    def on_get(self, req, resp):

        self._mongo = MongoClient('localhost', 27017)
    
        uuid = self._mongo.unis_db['about'].find()[0]['uuid']
        
        about = {
            "uid": str(uuid),
            "haschild": "false",
            "depth": 0
        }

        resp.set_header("Content-Type", MIME["JSON"])
        resp.body = json.dumps(about, indent=4)
