#!/usr/bin/env python

import tornado.web
import json

from periscope.settings import MIME

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, base_url, resources):
        self._resources = resources
    
    def get(self):
        links = []
        for resource in self._resources:
            href = "%s://%s%s" % (self.request.protocol,
                self.request.host, self.reverse_url(resource))
            links.append({"href": href, "rel": "full"})
        self.set_header("Content-Type", MIME["JSON"])
        self.write(json.dumps(links, indent=4))
