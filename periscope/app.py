'''
Usage:
  periscoped [options]

Options:
  -l FILE --log=FILE           File to store log information
  -d LEVEL --log-level=LEVEL   Select log verbosity [TRACE, DEBUG, CONSOLE]
  -c FILE --config-file=FILE   File with extra configurations [default: /etc/periscope/unis.cfg]
  -p PORT --port=PORT          Run on PORT [default: 8888]
  -D --daemonize               Run UNIS as a daemon
  -r --lookup                  Run UNIS as a lookup service
'''

import motor
import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import functools
import socket
import daemon
import docopt
import ConfigParser
import logging
from netlogger import nllog

from tornado import gen

from tornado.httpclient import AsyncHTTPClient

import settings
from settings import MIME
from settings import SCHEMAS
from periscope.db import DBLayer
from periscope.utils import load_class
from periscope.models import Manifest, ObjectDict
from periscope.pp_interface import PP_INTERFACE as PPI
from periscope.handlers.delegationhandler import DelegationHandler



class PeriscopeApplication(tornado.web.Application):
    @property
    def log(self):
        if not hasattr(self, "_log"):
            self._log = settings.get_logger()
        return self._log
    
    @property
    def options(self):
        if not hasattr(self, "_options"):
            class DefaultDict(dict):
                def get(self, k, default=None):
                    val = super(DefaultDict, self).get(k, default)
                    return val or default
            
            self._options = DefaultDict()
            tmpOptions = docopt.docopt(__doc__)
            for key, option in tmpOptions.items():
                self._options[key.lstrip("--")] = option
            
            tmpConfig = ConfigParser.RawConfigParser()
            tmpConfig.read(self._options["config-file"])
            
            for section in tmpConfig.sections():
                if section in self._options:
                    raise ValueError("Duplicate value in configuration, sections must be unique - {section}".format(section = section))
                else:
                    self._options[section] = {}
                    for key, option in tmpConfig.items(section):
                        self._options[section][key] = option
        return self._options
    
    
    def get_db_layer(self, collection_name, id_field_name,
                     timestamp_field_name, is_capped_collection, capped_collection_size):
        
        
        if collection_name == None:
            return None
        # Add capped collection if needed
        if is_capped_collection:
            self.db.create_collection(collection_name,
                                      capped      = True,
                                      size        = capped_collection_size,
                                      autoIndexId = False)
        
        # Ensure indexes
        if id_field_name != timestamp_field_name:
            self.db[collection_name].ensure_index([ (id_field_name, 1), (timestamp_field_name, -1)],
                                                  unique = True)
            self.db[collection_name].ensure_index([ (timestamp_field_name, -1)],
                                                  unique = True)
        
        # Create Layer
        db_layer = DBLayer(self.db,
                           collection_name,
                           is_capped_collection,
                           id_field_name,
                           timestamp_field_name)
        
        return db_layer
    
    
    def make_resource_handler(self, name,
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
        db_layer = self.get_db_layer(collection_name, id_field_name, timestamp_field_name, is_capped_collection, capped_collection_size)            
        
        # Load classes
        if type(handler_class) in [str, unicode]:
            handler_class = load_class(handler_class)
        if type(model_class) in [str, unicode]:
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
    
    def _make_getparent_handler(self,name,pattern,base_url,handler_class):
        db_layer = self.get_db_layer("exnodes", "id", "ts", False, 0)
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
        if type(handler_class) in [str, unicode]:
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

    @gen.coroutine
    def _report_to_root(self):
        manifests = []
        cursor = self.db["manifests"].find({ "\\$shard": False}, {"_id": False })
        
        while (yield cursor.fetch_next):
            manifests.append(ObjectDict._from_mongo(cursor.next_object()))
            
        import time
        if settings.ENABLE_SSL:
            http_str = "https"
        else:
            http_str = "http"
            
        callback = functools.partial(self.registered, fatal = False)
        service = {
            u"id": u"unis_" + socket.gethostname(),
            u"ts": int(time.time() * 1e6),
            u"\$schema": unicode(SCHEMAS["service"]),
            u"accessPoint": settings.UNIS_URL,
            u"name": u"unis_" + socket.gethostname(),
            u"status": u"ON",
            u"serviceType": u"ps:tools:unis",
            u"ttl": settings.SUMMARY_COLLECTION_PERIOD,
            u"runningOn": {
                u"href": u"%s/nodes/%s" % (settings.UNIS_URL, socket.gethostname()),
                u"rel": u"full"
            },
            u"properties": {
                u"summary": manifests
            }
        }
        
        for lookup in settings.LOOKUP_URLS:
            service_url = lookup + '/register'
            http_client = AsyncHTTPClient()
            
            content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
            http_client.fetch(service_url,
                              method="POST",
                              body=json.dumps(service),
                              headers = {
                                  "Content-Type": content_type,
                                  "Cache-Control": "no-cache",
                                  "Accept": MIME['PSJSON'],
                                  "Connection": "close"},
                              callback=callback)
            
            
    def registered(self, response, fatal = True):
        if response.error:
            self.log.error("Couldn't connect to Client: ERROR {e}  {b}".format(e = response.error, b = response.body))
            if fatal:
                import sys
                sys.exit()
        else:
            body=json.loads(response.body)
            
    def make_simple_handler(self, name, pattern, base_url, handler_class, **kwargs):
        if type(handler_class) in [str, unicode]:
            handler_class = load_class(handler_class)
        handler = ( tornado.web.URLSpec(base_url + pattern, handler_class, dict(**kwargs), name=name) )
        return handler
    
    @gen.coroutine
    def _aggregate_manifests(self):
        def _trim_fields(resource, fields):
            resource.pop("_id", None)
            return resource
        
        def add_key(key, value, manifest):
            if key not in ["ts", "id", "_id", "\\$shard", "\\$collection"]:
                try:
                    prev = manifest["properties"][key] if key in manifest["properties"] else []
                    oldPrev = prev
                    if value == "*" or len(value) + len(prev) > settings.MAX_SUMMARY_SIZE:
                        prev = "*"
                    elif len(value) > 0 and type(value[0]) == dict:
                        prev += value
                    else:
                        prev = list(set(prev) | set(value))
                    manifest["properties"][key] = prev
                except Exception as exp:
                    self.log.error("Bad value in shard - {exp}".format(exp = exp))
                    
        collections = set()
        for key, collection in settings.Resources.items():
            if collection["collection_name"]:
                collections.add(collection["collection_name"])
            
        for collection in collections:
            newManifest = { "$shard": False, "$collection": collection, "properties": {} }
            modified    = False
            shards      = self.db["manifests"].find({ "\\$shard": True, "\\$collection": collection }, {'_id': False, "\\$shard": False, "\\$collection": False })
            manifest    = yield self.db["manifests"].find_one({ "\\$shard": False, "\\$collection": collection })
            
            while (yield shards.fetch_next):
                modified = True
                shard = shards.next_object()
                for key, value in shard["properties"].items():
                    add_key(key, value, newManifest)
                    
            if manifest:
                for key, value in manifest["properties"].items():
                    add_key(key, value, newManifest)
                    
            tmpManifest = dict(Manifest(newManifest)._to_mongoiter())
            if not manifest:
                yield self.db["manifests"].insert(tmpManifest)
            else:
                tmpManifest["id"] = manifest["id"]
                yield self.db["manifests"].update({ "\\$collection": collection }, tmpManifest)
        
        yield self.db["manifests"].remove({ "\\$shard": True })
        if settings.LOOKUP_URLS:
            self._report_to_root()
        
    def __init__(self):
        self.cookie_secret="S19283u182u3j12j3k12n3u12i3nu12i3n12ui3"
        self._db = None
        self._ppi_classes = []
        handlers = []
        
        # import and initialize pre/post content processing modules
        for pp in settings.PP_MODULES:
            mod = __import__(pp[0], fromlist=pp[1])
            c = getattr(mod, pp[1])
            if issubclass(c, PPI):
                if not settings.ENABLE_AUTH and c.pp_type is PPI.PP_TYPES[PPI.PP_AUTH]:
                    pass
                else:
                    self._ppi_classes.append(c())
            else:
                self.log.error("Not a valid PPI class: {name}".format(name = c.__name__))
                
        if settings.ENABLE_AUTH:
            from periscope.auth import ABACAuthService
            
            self._auth = ABACAuthService(settings.SSL_OPTIONS['certfile'],
                                         settings.SSL_OPTIONS['keyfile'],
                                         settings.AUTH_STORE_DIR,
                                         self.get_db_layer("authNZ",
                                                           "id", "ts", False, 0))
            for auth in settings.AuthResources:
                handlers.append(self.make_simple_handler(**settings.AuthResources[auth]))
        
        for res in settings.Resources:
            if bool(self.options["lookup"]):
                settings.Resources[res]["handler_class"] = "periscope.handlers.delegationhandler.DelegationHandler"
                settings.Resources[res]["allow_delete"] = False
                settings.Resources[res]["allow_put"] = False
                settings.Resources[res]["allow_post"] = False

            handlers.append(self.make_resource_handler(**settings.Resources[res]))
            
        for sub in settings.Subscriptions:
            handlers.append(self.make_simple_handler(**settings.Subscriptions[sub]))
        handlers.append(self._make_getSchema_handler(**settings.getSchema))
        handlers.append(self._make_main_handler(**settings.main_handler_settings))
        handlers.append(self._make_getparent_handler(**settings.getParent))
        
        # Setup hierarchy
        tornado.ioloop.PeriodicCallback(self._aggregate_manifests, settings.SUMMARY_COLLECTION_PERIOD * 1000).start()
        if bool(self.options["lookup"]):
            handlers.append(self.make_resource_handler(**settings.reg_settings))
        if settings.LOOKUP_URLS:
            self._report_to_root()
            
        tornado.web.Application.__init__(self, handlers,
            default_host="localhost", **settings.APP_SETTINGS)
        
        if settings.MS_ENABLE and not bool(self.options["lookup"]):
            import time
            if settings.ENABLE_SSL:
                http_str = "https"
            else:
                http_str = "http"
            callback = functools.partial(self.registered)
            service = {
                u"id": u"ms_" + socket.gethostname(),
                u"ts": int(time.time() * 1e6),
                u"\$schema": unicode(SCHEMAS["service"]),
                u"accessPoint": u"%s://%s:%d/" % (http_str, socket.getfqdn(), int(self.options["port"])),
                u"name": u"ms_" + socket.gethostname(),
                u"status": u"ON",
                u"serviceType": u"ps:tools:ms",
                u"ttl": 600,
                #u"description": u"sample MS service",
                u"runningOn": {
                    u"href": u"%s/nodes/%s" % (settings.UNIS_URL, socket.gethostname()),
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
            
            if 'localhost' in settings.UNIS_URL or "127.0.0.1" in settings.UNIS_URL:
                self.db["services"].insert(service)
            else:
                service_url = settings.UNIS_URL+'/services'
                
                http_client = AsyncHTTPClient()
                
                content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
                http_client.fetch(service_url,
                                  method="POST",
                                  body=json.dumps(service),
                                  validate_cert=False,
                                  client_cert=settings.MS_CLIENT_CERT,
                                  client_key=settings.MS_CLIENT_KEY,
                                  headers={
                                      "Content-Type": content_type,
                                      "Cache-Control": "no-cache",
                                      "Accept": MIME['PSJSON'],
                                      "Connection": "close"},
                                  callback=callback)
    
    @property
    def db(self):
        if not getattr(self, '_db', None):
            self._db = motor.MotorClient(**settings.DB_CONFIG)[self.options.get("dbname", settings.DB_NAME)]
            
        return self._db

def get_log_handles(log):
    handles = []
    for handle in log.handlers:
        handles.append(handle.stream)
    if log.parent:
        handles += get_log_handles(log.parent)
    return handles
    
def run():
    ssl_opts = None
    app = PeriscopeApplication()
    app.log.info('periscope.start')
    settings.app = app
    
    if settings.ENABLE_SSL:
        ssl_opts = settings.SSL_OPTIONS
        
    http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_opts)
    
    http_server.listen(int(app.options["port"]))
    
    loop = tornado.ioloop.IOLoop.instance()
    loop.start()
    app.log.info("periscope.end")
    
    
def main():
    tmpOptions = docopt.docopt(__doc__)
    log = settings.get_logger(level = tmpOptions["--log-level"], filename = tmpOptions["--log"])
    
    if tmpOptions["--daemonize"]:
        with daemon.DaemonContext(files_preserve = get_log_handles(log)):
            run()
    else:
        tornado.log.enable_pretty_logging()
        run()
        
    
if __name__ == "__main__":
    main()
