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
'''
Usage:
  periscoped [options]

Options:
  -l FILE --log=FILE           File to store log information
  -d LEVEL --log-level=LEVEL   Select log verbosity [ERROR, DEBUG, CONSOLE]
  -c FILE --config-file=FILE   File with extra configurations [default: /etc/periscope/unis.cfg]
  -p PORT --port=PORT          Run on PORT
  -r --lookup                  Run UNIS as a lookup service
  -S --soft-start              Poll backend port for connection when set, defaults to fail-fast
  --soft-start-pollrate=RATE   Rate of polling in seconds during soft start [default: 5]
'''

import configparser, docopt
import asyncio, motor, tornado.httpserver, tornado.web, tornado.ioloop
import functools, json, logging, time, sys, collections
import socket, requests

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from urllib.parse import urlparse
from uuid import uuid4

from periscope.settings import MIME
from periscope.settings import SCHEMAS
from periscope import settings
from periscope.db import DBLayer
from periscope.utils import load_class
from periscope.models import Manifest, ObjectDict
from periscope.pp_interface import PP_INTERFACE as PPI
from periscope.handlers import DelegationHandler

class PeriscopeApplication(tornado.web.Application):
    @property
    def log(self):
        if not hasattr(self, "_log"):
            self._log = settings.get_logger(level=self.options['log-level'], filename=self.options['log'])
        return self._log

    @property
    def options(self):
        def _build_pair(keys, value):
            d = self._options
            for k in keys[:-1]: d = d[k]
            
            if ".".join(keys) in settings.LIST_OPTIONS:
                value = value.split(",")
            try: value = {"true": True, "false": False}.get(value, value)
            except TypeError: pass
            
            d[keys[-1]] = value

        if not hasattr(self, "_options"):
            class DefaultDict(collections.defaultdict):
                def get(self, k, default=None):
                    val = super(DefaultDict, self).get(k, default)
                    return val or default

            tmpOptions = docopt.docopt(__doc__)
            self._options = DefaultDict(dict, settings.DEFAULT_CONFIG)
            tmpConfig = configparser.RawConfigParser(allow_no_value = True)
            tmpConfig.read(tmpOptions["--config-file"])

            for s in tmpConfig.sections():
                sp = lambda k, p: [k] if p == 'general' else ([p] + [k])
                [_build_pair(sp(k.lower(), s.lower()), o) for k,o in tmpConfig.items(s)]

            for key, option in tmpOptions.items():
                if option not in [None, False]:
                    self._options[key.lstrip("--")] = option
            self.log.debug("Configuration flags:")
            {self.log.debug("  {}: {}".format(k, v)) for k,v in self._options.items()}
        return self._options

    async def get_db_layer(self, collection_name, id_field_name,
                     timestamp_field_name, is_capped_collection, capped_collection_size):
        if collection_name == None:
            return None
        # Add capped collection if needed
        if is_capped_collection:
            await self.db.create_collection(collection_name,
                                            capped      = True,
                                            size        = capped_collection_size,
                                            autoIndexId = False)

        # Ensure indexes
        if id_field_name != timestamp_field_name:
            await self.db[collection_name].create_index([ (id_field_name, 1), (timestamp_field_name, -1)],
                                                        unique = True)
            await self.db[collection_name].create_index([ (timestamp_field_name, -1)],
                                                        unique = False)

        # Create Layer
        db_layer = DBLayer(self.db,
                           collection_name,
                           is_capped_collection,
                           id_field_name,
                           timestamp_field_name)

        return db_layer

    async def make_resource_handler(self, name,
                                    pattern,
                                    base_url,
                                    handler_class,
                                    model_class,
                                    collection_name,
                                    schema,
                                    is_capped_collection,
                                    capped_collection_size,
                                    id_field_name,
                                    timestamp_field_name,
                                    allow_get,
                                    allow_post,
                                    allow_put,
                                    allow_delete,
                                    accepted_mime,
                                    content_types_mime,
                                    **kwargs):

        # Prepare the DBlayer
        db_layer = await self.get_db_layer(collection_name, id_field_name, timestamp_field_name, is_capped_collection, capped_collection_size)

        # Load classes
        if type(handler_class) in [str, bytes]:
            handler_class = load_class(handler_class)
        if type(model_class) in [str, bytes]:
            model_class = load_class(model_class)

        # Make the handler
        handler = (
            tornado.web.URLSpec(base_url + pattern, handler_class,
                                dict(
                                    dblayer=db_layer,
                                    Id=id_field_name, timestamp=timestamp_field_name,
                                    base_url=base_url+pattern,
                                    allow_delete=allow_delete,
                                    schemas_single=schema,
                                    model_class=model_class,
                                    collection_name=collection_name,
                                    **kwargs
                                ),
                                name=name
            )
        )
        return handler

    async def _make_getparent_handler(self,name,pattern,base_url,handler_class):
        db_layer = await self.get_db_layer("exnodes", "id", "ts", False, 0)
        scm_handler = (
            tornado.web.URLSpec(base_url + pattern, handler_class,
                                dict(
                                    dblayer=db_layer,
                                    base_url=base_url+pattern,
                                    ),
                                    name=name
                                )
            )
        return scm_handler

    def _make_getSchema_handler(self,name,pattern,base_url,handler_class):
        scm_handler = (
            tornado.web.URLSpec(base_url + pattern, handler_class,
                                dict(
                                    base_url=base_url+pattern,
                                    ), 
                                    name=name
                                )
            )
        return scm_handler
    
    def _make_main_handler(self, name,  pattern, base_url, handler_class, resources):
        if type(handler_class) in [str, bytes]:
            handler_class = load_class(handler_class)
        main_handler = (
            tornado.web.URLSpec(base_url + pattern, handler_class,
                dict(
                    resources=resources,
                    base_url=base_url+pattern,
                ),
                name=name
            )
        )
        return main_handler
    
    async def _generate_uuid(self):
        async for record in self.db['about'].find():
            self.options['uuid'] = record['uuid']
        if self.options.get('uuid', None) is None:
            self.options['uuid'] = uuid4()
            await self.db['about'].insert_one({'uuid': self.options['uuid']})

    async def _report_to_root(self):
        manifests = []
        async for record in self.db["manifests"].find({"\\$shard": False}, {"_id": False}):
            manifests.append(ObjectDict._from_mongo(record))

        import time
        service = {
            u"id": u"unis_" + urlparse(self.options['unis']['url']).hostname,
            u"ts": int(time.time() * 1e6),
            u"\$schema": str(SCHEMAS["service"]),
            u"accessPoint": u"%s/" % (self.options['unis']['url']),
            u"name": u"unis_" + urlparse(self.options['unis']['url']).hostname,
            u"status": u"ON",
            u"serviceType": u"ps:tools:unis",
            u"ttl": int(self.options["unis"]["summary_collection_period"]),
            u"communities": self.options["unis"]["communities"],
            u"runningOn": {
                u"href": u"%s/nodes/%s" % (self.options['unis']['url'], socket.gethostname()),
                u"rel": u"full"
            },
            u"properties": {
                u"summary": manifests,
                u"depth": self._depth
            }
        }
        
        for lookup in self.options["unis"]["root_urls"]:
            service_url = lookup + '/register'
            http_client = AsyncHTTPClient()

            content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
            resp = await http_client.fetch(service_url,
                                           method="POST",
                                           body=json.dumps(service),
                                           headers = {
                                               "Content-Type": content_type,
                                               "Cache-Control": "no-cache",
                                               "Accept": MIME['PSJSON'],
                                               "Connection": "close"})
            self.registered(resp, fatal=False)

    def registered(self, response, fatal = True):
        if response.error:
            self._log.error("Couldn't connect to Client: ERROR {e}  {b}".format(e = response.error, b = response.body))
            if fatal:
                import sys
                sys.exit()
        else:
            body=json.loads(response.body)

    def make_simple_handler(self, name, pattern, base_url, handler_class, **kwargs):
        if type(handler_class) in [str, bytes]:
            handler_class = load_class(handler_class)
        handler = ( tornado.web.URLSpec(base_url + pattern, handler_class, dict(**kwargs), name=name) )
        return handler

    async def _aggregate_manifests(self):
        def _trim_fields(resource, fields):
            resource.pop("_id", None)
            return resource

        def add_key(key, value, manifest):
            if key not in ["ts", "id", "_id", "\\$shard", "\\$collection"]:
                try:
                    prev = manifest["properties"][key] if key in manifest["properties"] else []
                    if prev == "*" or value == "*" or len(value) + len(prev) > self.options["unis"]["summary_size"]:
                        prev = "*"
                    elif len(value) > 0 and type(value[0]) == dict:
                        prev += value
                    else:
                        prev = list(set(prev) | set(value))
                    manifest["properties"][key] = prev
                except Exception as exp:
                    self._log.error("Bad value in shard - {exp}".format(exp = exp))
                    
        while True:
            await asyncio.sleep(float(self.options["unis"]["summary_collection_period"]))
            m = self.db["manifests"]
            collections = set()
            for key, collection in settings.Resources.items():
                if collection["collection_name"]:
                    collections.add(collection["collection_name"])
            
            for collection in collections:
                view = {k: False for k in ["_id", "\\$shard", "\\$collection"]}
                manifest    = await m.find_one({ "\\$shard": False, "\\$collection": collection })
                manifest = manifest or { "$shard": False, "$collection": collection, "properties": {} }

                async for record in m.find({"\\$shard": True, "\\$collection": collection}, view):
                    [add_key(k,v,newManifest) for k,v in record["properties"].items()]

                manifest = dict(Manifest(manifest)._to_mongoiter())
                await m.update_one({"\\$collection": collection}, manifest, upsert=True)

            await m.remove({ "\\$shard": True })
            if self.options["unis"]["root_urls"]:
                self._report_to_root()
    
    async def initialize(self):
        # Init Locals
        hdl = []
        # Create Handlers
        if 'auth' in self.options and self.options["auth"]["enabled"]:
            from periscope.auth import ABACAuthService

            self._auth = ABACAuthService(settings.SSL_OPTIONS['certfile'],
                                         settings.SSL_OPTIONS['keyfile'],
                                         settings.AUTH_STORE_DIR,
                                         self.get_db_layer("authNZ",
                                                           "id", "ts", False, 0))
            hdl += [await self.make_simple_handler(**a) for a in settings.AuthResources.values()]

        l = {**{"handler_class": "periscope.handlers.DelegationHandler"},
             **{k: False for k in ["allow_delete", "allow_put", "allow_post"]}}
        for r in settings.Resources.values():
            hdl.append(await self.make_resource_handler(**(l if self.options['lookup'] else r)))

        hdl += [self.make_simple_handler(**s) for s in settings.Subscriptions.values()]
        
        hdl.append(self._make_getSchema_handler(**settings.getSchema))
        hdl.append(self._make_main_handler(**settings.main_handler_settings))
        hdl.append(self._make_main_handler(**settings.about_handler_settings))
        hdl.append(await self._make_getparent_handler(**settings.getParent))
        if bool(self.options["lookup"]):
            hdl.append(self.make_resource_handler(**settings.reg_settings))

        # Generate UUID
        await self._generate_uuid()

        # Register measurement store
        self.add_handlers(".*", hdl)

        if self.options["unis"]["use_ms"] and not bool(self.options["lookup"]):
            import time
            if self.options["unis_ssl"]["enable"]:
                http_str = "https"
            else:
                http_str = "http"
            service = {
                u"id": u"ms_" + socket.gethostname(),
                u"ts": int(time.time() * 1e6),
                u"\$schema": str(SCHEMAS["service"]),
                u"accessPoint": u"%s://%s:%d/" % (http_str, socket.getfqdn(), int(self.options["port"])),
                u"name": u"ms_" + socket.gethostname(),
                u"status": u"ON",
                u"serviceType": u"ps:tools:ms",
                u"ttl": 600,
                u"runningOn": {
                    u"href": u"%s/nodes/%s" % (self.options["unis"]["ms_url"], socket.gethostname()),
                    u"rel": u"full"
                },
                u"properties": {
                    u"configurations": {
                        u"default_collection_size": 10000,
                        u"max_collection_size": 20000
                    },
                    u"summary": {
                        u"metadata": []
                    }
                }
            }

            if settings.AUTH_UUID:
                service['properties'].update({"geni": {"slice_uuid": settings.AUTH_UUID}})

            if socket.getfqdn() in self.options['unis']['ms_url']:
                asyncio.ensure_future(self.db["services"].insert_one(service))
            else:
                service_url = self.options["unis"]["ms_url"]+'/services'
                print(self.options['unis'])

                http_client = AsyncHTTPClient()

                content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
                resp =  await http_client.fetch(service_url,
                                               method="POST",
                                               body=json.dumps(service),
                                               validate_cert=False,
                                               client_cert=settings.MS_CLIENT_CERT,
                                               client_key=settings.MS_CLIENT_KEY,
                                               headers={
                                                   "Content-Type": content_type,
                                                   "Cache-Control": "no-cache",
                                                   "Accept": MIME['PSJSON'],
                                                   "Connection": "close"})
                self.registered(resp)

        
    def __init__(self):
        self.cookie_secret="S19283u182u3j12j3k12n3u12i3nu12i3n12ui3"
        self._depth = 1 if bool(self.options["lookup"]) else 0
        self._db = None
        self._ppi_classes = []

        host = socket.getfqdn()
        for url in settings.SELF_LOOKUP_URLS:
            try:
                res = requests.get(url)
                res.raise_for_status()
                host = res.text
            except requests.exception.ConnectionError: pass
        ref = "http{}://{}:{}".format('s' if self.options['unis_ssl']['enable'] else '',
                                      host, self.options['port'])

        self.options['unis']['url'] = self._options['unis']['url'] or ref
        self.options['unis']['ms_url'] = self._options['unis']['ms_url'] or ref

        # import and initialize pre/post content processing modules
        for pp in settings.PP_MODULES:
            mod = __import__(pp[0], fromlist=pp[1])
            c = getattr(mod, pp[1])
            if issubclass(c, PPI):
                if not self.options["auth"]["enabled"] and c.pp_type is PPI.PP_TYPES[PPI.PP_AUTH]:
                    pass
                else:
                    self._ppi_classes.append(c())
            else:
                self._log.error("Not a valid PPI class: {name}".format(name = c.__name__))

        # Setup hierarchy
        tornado.ioloop.IOLoop.current().add_callback(self._aggregate_manifests)
        if self.options["unis"]["root_urls"]:
            self._report_to_root()

        tornado.web.Application.__init__(self, [], default_host="localhost", **settings.APP_SETTINGS)

    @property
    def db(self):
        if not getattr(self, '_db', None):
            db_config = { "host": self.options["unis"]["db_host"], "port": int(self.options["unis"]["db_port"]) }
            while True:
                try:
                    conn = motor.motor_tornado.MotorClient(**db_config)
                    break
                except Exception as exp:
                    self._log.error("Failed to connect to the MongoDB service - {e}".format(e = exp))
                    if not self.options["soft-start"]:
                        sys.exit()
                    time.sleep(int(self.options["soft-start-pollrate"]))
            self._db = conn[self.options.get("dbname", self.options["unis"]["db_name"])]
        return self._db

def run():
    ssl_opts = None
    app = PeriscopeApplication()

    app.log.info('periscope.start')
    settings.app = app
    
    if app.options["unis_ssl"]["enable"]:
        ssl_opts = settings.SSL_OPTIONS

    http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_opts)

    http_server.listen(int(app.options["port"]))

    loop = tornado.ioloop.IOLoop.instance()
    asyncio.ensure_future(app.initialize())
    loop.start()
    app.log.info("periscope.end")

def main():
    tmpOptions = docopt.docopt(__doc__)    
    run()
        
    
if __name__ == "__main__":
    main()
