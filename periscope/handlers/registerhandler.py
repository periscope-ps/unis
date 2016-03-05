#!/usr/bin/env python

import json
import tornado.gen
import tornado.websocket

from tornado.httpclient import AsyncHTTPClient

from periscope import settings
from periscope.settings import MIME
from periscope.models import Manifest, ObjectDict
from networkresourcehandler import NetworkResourceHandler

class RegisterHandler(NetworkResourceHandler):
    @tornado.gen.coroutine
    def _insert(self, resources):
        accessPoint = resources[0]["accessPoint"]
        tmpExists = yield self.dblayer.find_one({ "accessPoint": accessPoint })
        if tmpExists:
            yield self.dblayer.update({ "accessPoint": accessPoint }, resources[0], replace = True)
        else:
            yield self.dblayer.insert(resources)
        
        for manifest in resources[0]["properties"]["summary"]:
            manifest = ObjectDict._from_mongo(manifest)
            manifest["href"] = accessPoint
            yield self._update_manifest(manifest, accessPoint)
        
    @tornado.gen.coroutine
    def _subscribe(self, accessPoint):
        url = accessPoint.split("://")
        if url[0] == "http":
            protocol = "ws"
        else:
            protocol = "wss"
        base_url = url[1]
        
        url = "{protocol}://{base_url}subscribe/manifests".format(protocol = protocol, base_url = base_url)
        self._subscription = yield tornado.websocket.websocket_connect(url)

        while True:
            data = yield self._subscription.read_message()
            if data is None: break
            try:
                resource = json.loads(data)
                resource["href"] = accessPoint
                yield self._update_manifest(resource, accessPoint)
            except Exception as exp:
                self.log.error("Bad update from child instance - {exp}".format(exp = exp))
        
    
    @tornado.gen.coroutine
    def _update_manifest(self, manifest, source):
        tmpDB = self.application.get_db_layer(manifest["$collection"], self.Id, self.timestamp, False, 0)
        tmpManifest = yield tmpDB.find_one({ "href": source })
        mongoManifest = dict(Manifest(manifest)._to_mongoiter())
        if tmpManifest:
            yield tmpDB.update({ "href": source }, mongoManifest, replace = True)
        else:
            yield tmpDB.insert(mongoManifest)
