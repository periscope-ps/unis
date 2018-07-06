# =============================================================================
#  periscope-ps (unis)
#
#  Copyright (c) 2012-2016, Trustees of Indiana University,
#  All rights reserved.
#
#  This software may be modified and distributed under the terms of the BSD
#  license.  See the COPYING file for details.
#
#  This software was created at the Indiana University Center for Research in
#  Extreme Scale Technologies (CREST).
# =============================================================================
#!/usr/bin/env python

import json
import functools
import time
import tornado.web

from tornado.ioloop import IOLoop

from periscope.settings import MIME
from networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo


class DelegationHandler(NetworkResourceHandler):
    def initialize(self, **kwargs):
        kwargs.pop("collections", None)
        super(DelegationHandler, self).initialize(**kwargs)
    
    def _find(self, **kwargs):
        if self.Id in kwargs["query"].keys() or self.timestamp in kwargs["query"].keys():
            self._filter = False
        else:
            self._filter = True


        return self.dblayer.find()
    
    @tornado.gen.coroutine
    def _write_get(self, cursor, is_list, inline=False):
        exclude = [ "sort", "limit", "fields", "skip", "cert" ]
        interest_fields = [ key for key, val in self.request.arguments.items() if key not in exclude]
        interest_fields = [v.replace(".", "$DOT$") for v in interest_fields]
        
        manifest = {
            "redirect": True,
            "instances": []
        }
        
        count = yield cursor.count()
        if not count:
            self.write('[]')
            raise tornado.gen.Return(count)
        
        count = 0
        now = time.time()
        
        while (yield cursor.fetch_next):
            add_member = True
            member = cursor.next_object()
            if "href" in member:
                properties = member["properties"]
                if now > member.get("ttl", 0) + member["ts"]:
                    self.log.debug("Removing {h}: Too old".format(h=member['href']))
                    add_member = False
                elif self._filter:
                    for field in interest_fields:
                        vals = properties.get(field, [])
                        if vals != "*" and unicode(self.get_argument(field)) not in vals:
                            self.log.debug(u"Removing {h}: Bad member {m} - {v1} \u2209 {v2}".format(h=member["href"], m=field, v1=self.get_argument(field), v2=vals))
                            add_member = False
                        
                if not self._filter or (add_member and properties):
                    manifest["instances"].append(member["href"])
                    count += 1
                
        self.write(json.dumps(manifest, indent = 2))
        raise tornado.gen.Return(count)
