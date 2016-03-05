#!/usr/bin/env python

import json
import functools
from tornado.ioloop import IOLoop
import tornado.web


from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class DelegationHandler(NetworkResourceHandler):
    def _find(self, **kwargs):
        if self.Id in self.request.arguments.keys()  or self.timestamp in self.request.arguments.keys():
            self._resId = True
        else:
            self._resId = None
            
        return self.dblayer.find()
    
    @tornado.gen.coroutine
    def _write_get(self, cursor, is_list):
        exclude = [ "sort", "limit", "fields", "skip", "cert" ]
        interest_fields = [ key for key, val in self.request.arguments.items() if key not in exclude]
        interest_fields = map(lambda val: val.replace(".", "$DOT$"), interest_fields)
        do_filter = self._resId == None
        
        manifest = {
            "redirect": True,
            "instances": []
        }
        
        count = yield cursor.count()
        if not count:
            self.write('[]')
            raise tornado.gen.Return(count)
        
        count = 0
        
        while (yield cursor.fetch_next):
            add_member = True
            member = cursor.next_object()
            properties = member["properties"]
            if do_filter:
                for field in interest_fields:
                    if field not in properties or (properties[field] != "*" and unicode(self.get_argument(field)) not in properties[field]):
                        add_member = False
                        
            if add_member and properties:
                manifest["instances"].append(member["href"])
                count += 1
                
        self.write(json.dumps(manifest, indent = 2))
        raise tornado.gen.Return(count)
