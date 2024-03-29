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
import time
from tornado.httpclient import AsyncHTTPClient
import tornado.gen

import periscope.settings as settings
from periscope.settings import MIME
from .networkresourcehandler import NetworkResourceHandler
from periscope.db import dumps_mongo
from periscope.utils import DBError


class EventsHandler(NetworkResourceHandler):
    async def _insert(self, resources):
        resource = resources[0]
        http_client = AsyncHTTPClient()
        response = await http_client.fetch(resource["metadata_URL"],
                                           validate_cert=False,
                                           client_cert=settings.MS_CLIENT_CERT,
                                           client_key=settings.MS_CLIENT_KEY)
        
        if response.error:
            self.send_error(400, message="metadata is not found '%s'." % response.error)
        else:
            body = json.loads(response.body)
            collections = await self.application.db.list_collection_names()
            if body[self.Id] not in collections:
                await self.application.get_db_layer(body[self.Id], "ts", "ts", True, resource["collection_size"])
                self.set_header("Location","%s/data/%s" % (self.request.full_url().split('?')[0], body[self.Id]))
                resource[self.timestamp] = int(time.time() * 1000000)
                resource[self.Id] = body[self.Id]
                await self.dblayer.insert([resource], summarize = False)
            else:
                raise ValueError("event collection exists already")
            
    async def _find(self, **options):
        options["query"].pop("\\$status", None)
        if not options["query"]:
            return await self.dblayer.count(**options), self.dblayer.find()
        elif self.Id in options["query"] or "$or" in options["query"]:
            return await self.dblayer.count(**options), self.dblayer.find(**options)
        else:
            self._query = options["query"]
            return None, None
        
    async def _add_response_headers(self, cursor):
        count = 1
        accept = self.accept_content_type
        self.set_header("Content-Type", accept + "; profile=" + self.schemas_single[accept])

        return count

    async def _write_get(self, cursor, is_list = False, inline=False, unique=False, count=0):
        response = []
        if cursor:
            async for resource in cursor:
                try:
                    mid = resource["metadata_URL"].split('/')[-1]
                    response.insert(0, await self.generate_response(mid))
                except ValueError as exp:
                    raise
        else:
            count = 0
            for d in self._query["$and"]:
                if 'mids' in d.keys():
                    if isinstance(d["mids"],dict):
                        for m in d['mids']['$in']:
                            try:
                                res = await self.generate_response(m)
                            except ValueError as exp:
                                raise
                            count += 1
                            response.insert(0, res)
                    else:
                        try:
                            res = await self.generate_response(d['mids'])
                        except ValueError as exp:
                            raise
                        count += 1
                        response.insert(0, res)

        if self.accept_content_type == MIME["PSBSON"]:
            json_response = bson_encode(response)
        else:
            json_response = dumps_mongo(response, indent=2)
        self.write(json_response)
        return count
        
    async def _return_resoures(self, query):
        try:
            async for record in self.dblayer.find(query):
                self._subscriptions.publish(resource, self._collection_name)
        except Exception as exp:
            raise ValueError(exp)

    def del_stat_fields(self,generic):
        generic.pop("ns",None)
        generic.pop("numExtents",None)
        generic.pop("nindexes",None)
        generic.pop("lastExtentSize",None)
        generic.pop("paddingFactor",None)
        generic.pop("flags",None)
        generic.pop("totalIndexSize",None)
        generic.pop("indexSizes",None)
        generic.pop("max",None)
        generic.pop("ok",None)
        if generic["capped"] == 1:
            generic["capped"]="Yes"
        else:
            generic["capped"]="No"

    async def generate_response(self, mid):
        tmpReponse = None
        try:
            command={"collStats": mid,"scale":1}
            generic = await self.application.db.command(command)
        except Exception as exp:
            raise DBError("At least one of the metadata ID is invalid.")

        self.del_stat_fields(generic)
        specific={}
        if 'ts' in self.request.arguments.keys():
            criteria = self.request.arguments['ts'][0].split('=')

            if criteria[0] == 'gte':
                specific["startTime"] = int(criteria[1])
            if criteria[0] == 'lte':
                specific["endTime"] = int(criteria[1])
            
            if self.request.arguments['ts'].__len__() > 1 :            
                criteria = self.request.arguments['ts'][1].split('=')
                if criteria[0] == 'gte':
                    specific["startTime"] = int(criteria[1])
                if criteria[0] == 'lte':
                    specific["endTime"] = int(criteria[1])
            
            db_query = {"ts": { "$gt": 0 } }
            if startTime in specific:
                db_query["ts"]["$gte"] = specific["startTime"]
            if endTime  in specific:
                db_query["ts"]["$lte"] = specific["endTime"]
            specific["numRecords"] = await self.application.db[mid].count_documents(db_query)

        return {"mid": mid, "generic": generic, "queried": specific}
    
