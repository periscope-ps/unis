#!/usr/bin/env python

import periscope.settings
import tornado.web

class SchemaHandler(tornado.web.RequestHandler):
    def initialize(self, base_url):
        None
    def get(self, res_id=None):
        """Handles HTTP GET"""        
        args = self.request.arguments
        if 'name' in args.keys() and "node" in settings.SCHEMAS:
            """ Return schema json """  
            self.write(schemaLoader.get(settings.SCHEMAS["node"]))                      
        else:
            self.write(settings.SCHEMAS)                    
        self.finish()
