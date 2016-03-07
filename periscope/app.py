"""
Main Periscope Application
"""
import ssl
import motor
import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import functools
import socket
from tornado.options import define
from tornado.options import options
from tornado import gen

from tornado.httpclient import AsyncHTTPClient

# before this import 'periscope' path name is NOT as defined!
import settings
from settings import MIME
from settings import SCHEMAS
from periscope.db import DBLayer
from periscope.utils import load_class
from periscope.models import Manifest, ObjectDict
from periscope.pp_interface import PP_INTERFACE as PPI
from periscope.handlers.delegationhandler import DelegationHandler
from periscope.handlers import subscriptionmanager

# default port
define("port", default=8888, help="run on the given port", type=int)
define("address", default="0.0.0.0", help="default binding IP address", type=str)
define("dbname", default=settings.DB_NAME, help="store data to a specific database", type=str)
define("lookup", default=False, type=bool, help="run as a lookup instance")


class PeriscopeApplication(tornado.web.Application):
    """Defines Periscope Application."""
    
    def get_db_layer(self, collection_name, id_field_name,
                     timestamp_field_name, is_capped_collection, capped_collection_size):
        
        """
        Creates DBLayer instance.
        """
        
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
        """
        Creates HTTP Request handler.
        
        Parameters:
        
        name: the name of the URL handler to be used with reverse_url.
        
        pattern: For example "/ports$" or "/ports/(?P<res_id>[^\/]*)$".
            The final URL of the resource is `base_url` + `pattern`.
        
        base_url: see pattern
        
        handler_class: The class handling this request.
            Must inherit `tornado.web.RequestHanlder`
        
        model_class: Database model class for this resource (if any).
        
        collection_name: The name of the database collection storing this resource.
        
        schema: Schemas fot this resource in the form: "{MIME_TYPE: SCHEMA}"
        
        is_capped_collection: If true the database collection is capped.
        
        capped_collection_size: The size of the capped collection (if applicable)
        
        id_field_name: name of the identifier field
        
        timestamp_field_name: name of the timestampe field
        
        allow_get: allow HTTP GET (True or False)
        
        allow_post: allow HTTP POST (True or False)
        
        allow_put: allow HTTP PUT (True or False)
        
        allow_delete: allow HTTP DELETE (True or False)
        
        accepted_mime: list of accepted MIME types
        
        content_types_mime: List of Content types that can be returned to the user
        
        kwargs: additional handler specific arguments
        """
        
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
        
        service_url = settings.LOOKUP_URL + '/register'
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
            print "Couldn't connect to Client: ERROR", response.error, response.body
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
                    print("Bad value in shard - {exp}".format(exp = exp))
                    
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
        self._report_to_root()
        
    def __init__(self):
        self._subscriptions = subscriptionmanager.GetManager()
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
                print "Not a valid PPI class: %s" % c.__name__
                
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
            if options.lookup:
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
        if options.lookup:
            handlers.append(self.make_resource_handler(**settings.reg_settings))
        if settings.LOOKUP_URL:
            self._report_to_root()
            
        tornado.web.Application.__init__(self, handlers,
            default_host="localhost", **settings.APP_SETTINGS)
        
        if settings.MS_ENABLE and not options.lookup:
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
                u"accessPoint": u"%s://%s:%d/" % (http_str, socket.getfqdn(), options.port),
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
            self._db = motor.MotorClient(**settings.DB_CONFIG)[options.dbname]
            
        return self._db
    
    
def main():
    """Run periscope"""
    ssl_opts = None
    logger = settings.get_logger()
    logger.info('periscope.start')
    loop = tornado.ioloop.IOLoop.instance()
    # parse command line options
    tornado.options.parse_command_line()
    app = PeriscopeApplication()
    settings.app = app
    
    if settings.ENABLE_SSL:
        ssl_opts = settings.SSL_OPTIONS
        
    http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_opts)
    #http_server.listen(options.port, address=options.address)
    http_server.listen(options.port)
    
    loop.start()
    logger.info('periscope.end')
    
    
if __name__ == "__main__":
    main()
