"""
Main Periscope Application
"""
import ssl
import asyncmongo
import pymongo
import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import functools
import socket
from tornado.options import define
from tornado.options import options

from tornado.httpclient import AsyncHTTPClient

# before this import 'periscope' path name is NOT as defined!
import settings
from settings import MIME
from settings import SCHEMAS
from periscope.handlers import NetworkResourceHandler
from periscope.handlers import CollectionHandler
from periscope.handlers import MainHandler
from periscope.handlers import SubscriptionHandler
from periscope.db import DBLayer
from periscope.utils import load_class
from periscope.pp_interface import PP_INTERFACE as PPI

# default port
define("port", default=8888, help="run on the given port", type=int)
define("address", default="0.0.0.0", help="default binding IP address", type=str)


class PeriscopeApplication(tornado.web.Application):
    """Defines Periscope Application."""

    def get_db_layer(self, collection_name, id_field_name,
            timestamp_field_name, is_capped_collection, capped_collection_size):
        """
        Creates DBLayer instance.
        """

        if collection_name == None:
            return None
        
        # Initialize the capped collection, if necessary!
        if is_capped_collection and \
                collection_name not in self.sync_db.collection_names():
            self.sync_db.create_collection(collection_name,
                            capped=True,
                            size=capped_collection_size,
                            autoIndexId=False)
        
        # Make indexes if the collection is not capped
        if id_field_name != timestamp_field_name:
            self.sync_db[collection_name].ensure_index([
                    (id_field_name, 1),
                    (timestamp_field_name, -1)
                ],
                unique=True)            
        
        # Prepare the DBLayer
        db_layer = DBLayer(self.async_db,
            collection_name,
            is_capped_collection,
            id_field_name,
            timestamp_field_name
        )
        
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
        # Load classes
        if type(handler_class) in [str, unicode]:
            handler_class = load_class(handler_class)
        if type(model_class) in [str, unicode]:
            model_class = load_class(model_class)
        
        # Prepare the DBlayer
        # Prepare the DBlayer
        db_layer = self.get_db_layer(collection_name,
                        id_field_name, timestamp_field_name,
                        is_capped_collection, capped_collection_size)
        
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
                    **kwargs
                ),
                name=name
            )
        )
        return handler
    
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

    def _make_subscription_handler(self, name, pattern, base_url, handler_class):
        if type(handler_class) in [str, unicode]:
            handler_class = load_class(handler_class)
        subscription_handler = (tornado.web.URLSpec(base_url + pattern, handler_class, name=name))
        return subscription_handler

    def MS_registered(self,response):
        if response.error:
            print "Couldn't start MS: ERROR", response.error, response.body
            import sys
            sys.exit()
        else:
            body=json.loads(response.body)

    def make_auth_handler(self, name, pattern, base_url, handler_class, schema):
        if type(handler_class) in [str, unicode]:
            handler_class = load_class(handler_class)
        handler = ( tornado.web.URLSpec(base_url + pattern, handler_class, name=name) )
        return handler
        
    def __init__(self):
        self._async_db = None
        self._sync_db = None
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
                                         #self.get_db_layer("authNZ", "uuid", "ts", False, None))
                                         self.sync_db["authNZ"])

            for auth in settings.AuthResources:
                handlers.append(self.make_auth_handler(**settings.AuthResources[auth]))
        
        for res in settings.Resources:
            handlers.append(self.make_resource_handler(**settings.Resources[res]))

        for sub in settings.Subscriptions:
            handlers.append(self._make_subscription_handler(**settings.Subscriptions[sub]))
        handlers.append(self._make_getSchema_handler(**settings.getSchema))
        handlers.append(self._make_main_handler(**settings.main_handler_settings))
        
        tornado.web.Application.__init__(self, handlers,
                    default_host="localhost", **settings.APP_SETTINGS)
        
        
        if settings.MS_ENABLE :
            import time
            if settings.ENABLE_SSL:
                http_str = "https"
            else:
                http_str = "http"
            callback = functools.partial(self.MS_registered)
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
                self.sync_db["services"].insert(service)
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
    def async_db(self):
        """Returns a reference to asyncmongo DB connection."""
        if not getattr(self, '_async_db', None):
            self._async_db = asyncmongo.Client(**settings.ASYNC_DB)
        return self._async_db

    @property
    def sync_db(self):
        """Returns a reference to pymongo DB connection."""
        if not getattr(self, '_sync_db', None):
            conn = pymongo.Connection(**settings.SYNC_DB)
            self._sync_db = conn[settings.DB_NAME]
        return self._sync_db


def main():
    """Run periscope"""
    ssl_opts = None
    logger = settings.get_logger()
    logger.info('periscope.start')
    loop = tornado.ioloop.IOLoop.instance()
    # parse command line options
    tornado.options.parse_command_line()
    app = PeriscopeApplication()

    if settings.ENABLE_SSL:
        ssl_opts = settings.SSL_OPTIONS
    
    http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_opts)
    #http_server.listen(options.port, address=options.address)
    http_server.listen(options.port)

    loop.start()
    logger.info('periscope.end')


if __name__ == "__main__":
    main()
