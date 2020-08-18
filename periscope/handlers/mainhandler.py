import json
from periscope.settings import MIME, Resources
from periscope.handlers.basehandler import BaseHandler

class MainHandler(BaseHandler):
        
    def on_get(self, req, resp):

        links = []
        resources = ["links", "ports", "nodes", "services", "paths", "networks", "domains", "topologies", "events", "data", "metadata", "measurements", "exnodes", "extents"]
        
        for resource in resources:
            href = "%s://%s/%s" % (req.scheme, req.host, resource)
            
            links.append({ "href": href, 
                           "rel": "full",
                           "targetschema": { "type": "array", "items": { "rel": "full", "href": Resources[resource]["schema"][MIME["PSJSON"]] } } })
        
        resp.set_header("Content-Type", MIME["JSON"])
        resp.body = json.dumps(links, indent=4)
