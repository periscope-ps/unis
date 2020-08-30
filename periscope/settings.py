#!/usr/bin/env python
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

"""
General Periscope Settings.
"""
import ssl
import logging
import logging.handlers
import os
import falcon_jsonify
import sys
from pymongo import MongoClient
from periscope.db import DBLayer

LIST_OPTIONS = ["unis.root_urls", "unis.communities"]
SELF_LOOKUP_URLS = ["http://ident.me"]


dbcfg = {
    'host': 'localhost', # or external server address
    'port': 27017,
    'username': os.environ.get('MONGO_USER'),
    'password': os.environ.get('MONGO_PASS'),
}


middleware = [
    falcon_jsonify.Middleware(help_messages=True),
]


######################################################################
# Setting up path names.
######################################################################
PERISCOPE_ROOT = os.path.expandvars("$PERISCOPE_ROOT")
if PERISCOPE_ROOT == "$PERISCOPE_ROOT":
    PERISCOPE_ROOT = os.path.expanduser("~/.periscope")

SCHEMA_CACHE_DIR = os.path.join(PERISCOPE_ROOT, ".cache")

GCF_PATH = "/opt/gcf/src/"
sys.path.append(os.path.dirname(GCF_PATH))

AUTH_STORE_DIR = os.path.join(os.path.dirname(__file__), "abac")

######################################################################
# Configuration options
######################################################################
DEFAULT_CONFIG = {
    "unis_ssl": {
        "enable": False,
    },
    "unis": {
        "url": "",
        "summary_collection_period": 60 * 60,
        "root_urls": [],
        "communities": [],
        "summary_size": 10,
        "use_ms": True,
        "ms_url": "",
        "db_host": "127.0.0.1",
        "db_port": 27017,
        "db_name": "unis_db"
    },
    "auth": {
        "enabled": False
    },
    "port": "8888",
    "log": None,
    "log-level": "INFO"
}




######################################################################
# Tornado settings.
######################################################################

#ENABLE_SSL = False
SSL_OPTIONS = {
    'certfile': os.path.join(PERISCOPE_ROOT, "ssl/server.pem"),
    'keyfile': os.path.join(PERISCOPE_ROOT, "ssl/server.key"),
    'cert_reqs': ssl.CERT_REQUIRED,
    'ca_certs': os.path.join(PERISCOPE_ROOT, "ssl/genica.bundle")
}

CLIENT_SSL_OPTIONS = {
    'certfile': "/usr/local/etc/certs/ms_cert.pem",
    'keyfile': "/usr/local/etc/certs/ms_key.pem"
}

######################################################################
# Measurement Store settings.
######################################################################
MS_CLIENT_CERT = "/usr/local/etc/certs/ms_cert.pem"
MS_CLIENT_KEY = "/usr/local/etc/certs/ms_key.pem"
GEMINI_NODE_INFO = None


######################################################################
# Periscope Application settings.
######################################################################
# Enable application wide debugging options
DEBUG = False

# Time to wait before reconnecting in seconds
REGISTER_RETRY_PERIOD = 10

APP_SETTINGS = {
    'cookie_secret': "43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    'template_path': os.path.join(os.path.dirname(__file__), "templates/"),
    'static_path': os.path.join(os.path.dirname(__file__), "static/"),
    'xsrf_cookies': False,
    'autoescape': "xhtml_escape",
    'debug': DEBUG,
}

######################################################################
# Mongo Database settings
######################################################################
DB_AUTH = {
    'auth_field' : "secToken",
    'auth_default' : None,
    'attrib_list' : ("landsat","unauth"),
}

######################################################################
# Netlogger settings
######################################################################
LOGGER_NAMESPACE = "periscope"

_log = None
def config_logger(namespace=LOGGER_NAMESPACE, level = None, filename = None):
    tmpLog = logging.getLogger(LOGGER_NAMESPACE)
    tmpLog.propagate = False

    if filename:
        add_filehandler(tmpLog, filename)
    else:
        handler = logging.StreamHandler(sys.stdout)
        #handler.setFormatter(LogFormatter("%(message)s"))
        tmpLog.addHandler(handler)

    if level == "WARN":
        tmpLog.setLevel(logging.WARNING)
    elif level == "ERROR":
        tmpLog.setLevel(logging.ERROR)
    elif level == "DEBUG":
        tmpLog.setLevel(logging.DEBUG)
        #if not filename:
        #    enable_pretty_logging()
    elif level == "CONSOLE":
        tmpLog.setLevel(25)
    else:
        tmpLog.setLevel(logging.INFO)
        
    return tmpLog

def add_filehandler(log, logfile):
    log.handlers = []
    
    try:
        fileHandler = logging.handlers.RotatingFileHandler(logfile, maxBytes = 500000, backupCount = 5)
        fileHandler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(fileHandler)
    except AttributeError as exp:
        log.error("Could not attach File Logger: {exp}".format(exp = exp))

def get_logger(namespace=LOGGER_NAMESPACE, level = None, filename = None):
    """Return logger object"""
    # Test if netlloger is initialized
    global _log
    if not _log:
        _log = config_logger(namespace, level, filename)
    return _log

def get_db_layer(collection_name, id_field_name,
                     timestamp_field_name, is_capped_collection, capped_collection_size):
        
        db = MongoClient('localhost', 27017).unis_db
        
        if collection_name == None:
            return None
        # Add capped collection if needed
        if is_capped_collection:
            db.create_collection(collection_name,
                                 capped      = True,
                                 size        = capped_collection_size,
                                 autoIndexId = False)
        
        # Ensure indexes
        if id_field_name != timestamp_field_name:
            db[collection_name].create_index([ (id_field_name, 1), (timestamp_field_name, -1)],
                                             unique = True)
            db[collection_name].create_index([ (timestamp_field_name, 1)],
                                             unique = False)
        
        # Create Layer
        db_layer = DBLayer(db,
                           collection_name,
                           is_capped_collection,
                           id_field_name,
                           timestamp_field_name)
        
        return db_layer

######################################################################
# NetworkResource Handlers settings
######################################################################
MIME = {
    'HTML': 'text/html',
    'JSON': 'application/json',
    'PLAIN': 'text/plain',
    'SSE': 'text/event-stream',
    'PSJSON': 'application/perfsonar+json',
    'PSBSON': 'application/perfsonar+bson',
    'PSXML': 'application/perfsonar+xml',
}

#SCHEMA_HOST = 'localhost'
SCHEMA_HOST = 'unis.crest.iu.edu'

_schema = "http://{host}/schema/{directory}/{name}"
SCHEMAS = {
    'manifest':        _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "manifest#"),
    'networkresource': _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "networkresource#"),
    'node':            _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "node#"),
    'domain':          _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "domain#"),
    'port':            _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "port#"),
    'link':            _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "link#"),
    'path':            _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "path#"),
    'network':         _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "network#"),
    'topology':        _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "topology#"),
    'service':         _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "service#"),
    'metadata':        _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "metadata#"),
    'data':            _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "data#"),
    'datum':           _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "datum#"),
    'measurement':     _schema.format(host = SCHEMA_HOST, directory = "20160630", name = "measurement#"),
    'exnode':          _schema.format(host = SCHEMA_HOST, directory = "exnode/6", name = "exnode#"),
    'extent':          _schema.format(host = SCHEMA_HOST, directory = "exnode/6", name = "extent#"),
}

# Default settings that apply to almost all network resources
# This is used to make writing `Resources` easier.
default_resource_settings= {
    "base_url": "", # For additional URL extension, e.g. /mynetwork/unis will make /ports like /mynetwork/unis/ports
    "handler_class": "NetworkResourceHandler", # The HTTP Request Handler class
    "is_capped_collection": False,
    "capped_collection_size": 0,
    "id_field_name": "id",
    "timestamp_field_name": "ts",
    "allow_get": True,
    "allow_post": True,
    "allow_put": True,
    "allow_delete": True,
    "accepted_mime": [MIME['SSE'], MIME['PSJSON'], MIME['PSBSON']],
    "content_types_mime": [MIME['SSE'], MIME['PSJSON']]
}

links = default_resource_settings.copy()
links.update({
            "name": "links",
            "uri_template": "/links", # The regex used to match the handler in URI
            "model_class": "periscope.models.Link", # The name of the database collection
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]}, # JSON Schema fot this resource
        })

link = default_resource_settings.copy()
link.update(
        {
            "name": "link",
            "uri_template": "/links/{res_id}",
            "model_class": "periscope.models.Link",
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]},
        })

login = default_resource_settings.copy()
login.update(
        {
            "name": "login",
            "uri_template": "/login",
            # "model_class": "periscope.models.Port",
            # "collection_name": "ports",
            # "schema": {MIME['PSJSON']: SCHEMAS["port"]},
        })

ports = default_resource_settings.copy()
ports.update(
        {
            "name": "ports",
            "uri_template": "/ports",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        })

port = default_resource_settings.copy()
port.update(
        {
            "name": "port",
            "uri_template": "/ports/{res_id}",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        })
        
nodes = default_resource_settings.copy()
nodes.update(
        {
            "name": "nodes",
            "uri_template": "/nodes",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        })
        
node = default_resource_settings.copy()
node.update(
        {
            "name": "node",
            "uri_template": "/nodes/{res_id}",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        })
        
services = default_resource_settings.copy()
services.update(
        {
            "name": "services",
            "uri_template": "/services",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })
        
service = default_resource_settings.copy()
service.update(
        {
            "name": "service",
            "uri_template": "/services/{res_id}",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })
        
getSchema = dict( \
        {
            "name": "getSchema",
            "uri_template": "/getSchema",
            "base_url":"",
            "handler_class": "SchemaHandler",
        }.items()
)
getParent = dict( \
        {
            "name": "getFolder",
            "uri_template": "/getFolder",
            "base_url":"",
            "handler_class": "FolderHandler",
        }.items()
)
paths = default_resource_settings.copy()
paths.update(
        {
            "name": "paths",
            "uri_template": "/paths",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        })
        
path = default_resource_settings.copy()
path.update(
        {
            "name": "path",
            "uri_template": "/paths/{res_id}",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        })
        
networks = default_resource_settings.copy()
networks.update(
        {
            "name": "networks",
            "uri_template": "/networks",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        })
        
network = default_resource_settings.copy()
network.update(
        {
            "name": "network",
            "uri_template": "/networks/{res_id}",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        })
        
domains = default_resource_settings.copy()
domains.update(
        {
            "name": "domains",
            "uri_template": "/domains",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        })
        
domain = default_resource_settings.copy()
domain.update(
        {
            "name": "domain",
            "uri_template": "/domains/{res_id}",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        })
        
topologies = default_resource_settings.copy()
topologies.update(
        {
            "name": "topologies",
            "uri_template": "/topologies",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        })
        
topology = default_resource_settings.copy()
topology.update(
        {
            "name": "topology",
            "uri_template": "/topologies/{res_id}",
            "handler_class": "CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        })

metadatas = default_resource_settings.copy()
metadatas.update(
        {
            "name": "metadatas",
            "uri_template": "/metadata", 
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        })
        
metadata = default_resource_settings.copy()
metadata.update(
        {
            "name": "metadata",
            "uri_template": "/metadata/{res_id}",
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        })

events = default_resource_settings.copy()
events.update(
        {
            "name": "events",
            "uri_template": "/events", 
            "handler_class" : "EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": "events_cache",
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        })

event = default_resource_settings.copy()
event.update(
        {
            "name": "event",
            "uri_template": "/events/{res_id}",
            "handler_class" : "EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": None,
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        })

datas = default_resource_settings.copy()
datas.update(
        {
            "name": "datas",
            "uri_template": "/data", 
            "handler_class" : "DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        })

data = default_resource_settings.copy()
data.update(
        {
            "name": "data",
            "uri_template": "/data/{res_id}",
            "handler_class" : "DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        })

measurements = default_resource_settings.copy()
measurements.update(
        {
            "name": "measurements",
            "uri_template": "/measurements",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        })
        
measurement = default_resource_settings.copy()
measurement.update(
        {
            "name": "measurement",
            "uri_template": "/measurements/{res_id}",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        })

extents = default_resource_settings.copy()
extents.update(
         {
             "name"                   : "extents",
             "uri_template"           : "/extents",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         })
         
extent = default_resource_settings.copy()
extent.update(
         {
             "name"                   : "extent",
             "uri_template"           : "/extents/{res_id}",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         })

exnodes = default_resource_settings.copy()
exnodes.update(
         {
             "name"                   : "exnodes",
             "uri_template"           : "/exnodes",
             "handler_class"          : "ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         })
         
exnode = default_resource_settings.copy()
exnode.update(
         {
             "name"                   : "exnode",
             "uri_template"           : "/exnodes/{res_id}",
             "handler_class"          : "ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         })

reg_settings = default_resource_settings.copy()
reg_settings.update(
        {
            "name": "register",
            "uri_template": "/register",
            "model_class": "periscope.models.Service",
            "handler_class": "RegisterHandler",
            "collection_name": "register",
            "allow_get": False, "allow_delete": False, "allow_put": False,
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })


itemSubscription = {
    "base_url"      : "",
    "name"          : "itemSubscription",
    "uri_template"  : "/subscribe/{resource_type}/{resource_id})",
    "handler_class" : "SubscriptionHandler"
}

catSubscription = {
    "base_url"      : "",
    "name"          : "categorySubscription",
    "uri_template"  : "/subscribe/{resource_type})",
    "handler_class" : "SubscriptionHandler"
}

querySubscription = {
    "base_url"      : "",
    "name"          : "querySubscription",
    "uri_template"  : "/subscribe",
    "handler_class" : "SubscriptionHandler"
}

collections = {
    "links": link,
    "ports": port,
    "nodes": node,
    "services": service,
    "paths": path,
    "networks": network,
    "domains": domain,
    "topologies": topology,
    "measurements": measurement,
}

topologies["collections"] = collections
topology["collections"] = collections
domains["collections"] = collections
domain["collections"] = collections
networks["collections"] = collections
network["collections"] = collections

Resources = {
    "links": links,
    "link": link,
    "ports": ports,
    "port": port,
    "nodes": nodes,
    "node": node,
    "services": services,
    "service": service,
    "paths": paths,
    "path": path,
    "networks": networks,
    "network": network,
    "domains": domains,
    "domain": domain,
    "topologies": topologies,
    "topology": topology,
    "metadatas": metadatas,
    "metadata": metadata,
    "events" : events,
    "event" : event,
    "data" : data,
    "datas" : datas,
    "measurements": measurements,
    "measurement" : measurement,
    "exnodes"     : exnodes,
    "exnode"      : exnode,
    "extents"     : extents,
    "extent"      : extent,
}

Subscriptions = {
    "itemSubscription"  : itemSubscription,
    "catSubscription"   : catSubscription,
    "querySubscription" : querySubscription,
}


main_handler_settings = {
    "resources": ["links", "ports", "nodes", "services", "paths",
                  "networks", "domains", "topologies", "events", "datas", "metadatas", "measurements", "exnodes", "extents"],
    "name": "main",
    "base_url": "",
    "uri_template": "/",
    "handler_class": "MainHandler",
}
about_handler_settings = {
    "resources": [],
    "name": "about",
    "base_url": "",
    "uri_template": "/about",
    "handler_class": "AboutHandler"
}

######################################################################
# PRE/POST content processing module definitions.
######################################################################
PP_MODULES=[]
#if (ENABLE_AUTH): 
#    PP_MODULES.append(('filters.dataAuth','DataAuth')) #[('#gemini', 'Gemini')]

# Settings for the GEMINI-specific authentication handlers
auth_user_settings= {
    "base_url": "",
    "handler_class": "gemini.AuthUserCredHandler",
    "name": "cred_geniuser",
    "uri_template": "/credentials/geniuser",
    "schema": [MIME['PLAIN']]
}

auth_slice_settings= {
    "base_url": "",
    "handler_class": "gemini.AuthSliceCredHandler",
    "name": "cred_genislice",
    "uri_template": "/credentials/genislice",
    "schema": [MIME['PLAIN']]
}
auth_login_settings= {
    "base_url": "",
    "handler_class": "filters.dataAuth.UserCredHandler",
    "name": "authenticate_user",
    "uri_template": "/login",
    "schema": [MIME['PLAIN']]
}
AuthResources = {
    "cred_login" : auth_login_settings,
    "cred_geniuser": auth_user_settings,
    "cred_genislice": auth_slice_settings
}
    

if GEMINI_NODE_INFO is not None:
    logger = get_logger()
    nconf = {}
    with open(GEMINI_NODE_INFO, 'r') as cfile:
        for line in cfile:
            name, var = line.partition("=")[::2]
            nconf[name.strip()] = str(var).rstrip()

        try:
            AUTH_UUID = nconf['auth_uuid']
        except Exception as e:
            AUTH_UUID = None
            logger.warning("read_settings", msg="Could not find auth_uuid in node configuration")
else:
    AUTH_UUID = None

if DEFAULT_CONFIG["unis_ssl"]["enable"]:
    try:
        from M2Crypto import X509
        SERVER_CERT_FINGERPRINT = X509.load_cert(SSL_OPTIONS['certfile'], X509.FORMAT_PEM).get_fingerprint('sha1')
    except Exception as e:
        SERVER_CERT_FINGERPRINT = ''
        logger = get_logger()
        logger.warning("read_settings", msg="Could not open SSL CERTFILE: %s" % e)
