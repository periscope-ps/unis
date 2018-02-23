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
import os
import sys
from netlogger import nllog
from tornado.log import LogFormatter, enable_pretty_logging

LIST_OPTIONS = ["unis.root_urls"]

######################################################################
# Setting up path names.
######################################################################
PERISCOPE_ROOT = os.path.dirname(os.path.abspath(__file__)) + os.sep
sys.path.append(os.path.dirname(os.path.dirname(PERISCOPE_ROOT)))
SCHEMA_CACHE_DIR = "/var/lib/periscope/.cache"

GCF_PATH = "/opt/gcf/src/"
sys.path.append(os.path.dirname(GCF_PATH))

AUTH_STORE_DIR = os.path.join(os.path.dirname(__file__), "abac")

JSON_SCHEMAS_ROOT = PERISCOPE_ROOT + "/schemas"
UNIS_SCHEMAS_USE_LOCAL = False

######################################################################
# Configuration options
######################################################################
DEFAULT_CONFIG = {
    "unis_ssl": {
        "enable": False,
    },
    "unis": {
        "url": "http://localhost:8888",
        "summary_collection_period": 60 * 60,
        "root_urls": [],
        "summary_size": 10,
        "use_ms": True,
        "ms_url": "http://localhost:8888",
        "db_host": "127.0.0.1",
        "db_port": 27017,
        "db_name": "unis_db"
    },
    "auth": {
        "enabled": False
    }
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
NETLOGGER_NAMESPACE = "periscope"

_log = None
def config_logger(namespace=NETLOGGER_NAMESPACE, level = None, filename = None):
    tmpLog = nllog.get_logger(namespace)
    tmpLog.propagate = False
    nllog.PROJECT_NAMESPACE = namespace

    if filename:
        add_filehandler(tmpLog, filename)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(LogFormatter("%(message)s"))
        tmpLog.addHandler(handler)

    if level == "WARN":
        tmpLog.setLevel(logging.WARN)
    elif level == "TRACE":
        tmpLog.setLevel(nllog.TRACE)
    elif level == "DEBUG":
        tmpLog.setLevel(logging.DEBUG)
        if not filename:
            enable_pretty_logging()
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

def get_logger(namespace=NETLOGGER_NAMESPACE, level = None, filename = None):
    """Return logger object"""
    # Test if netlloger is initialized
    global _log
    if nllog.PROJECT_NAMESPACE != namespace or not _log:
        _log = config_logger(namespace, level, filename)
    return _log

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
    "handler_class": "periscope.handlers.NetworkResourceHandler", # The HTTP Request Handler class
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

links = dict(default_resource_settings.items() + \
        {
            "name": "links",
            "pattern": "/links$", # The regex used to match the handler in URI
            "model_class": "periscope.models.Link", # The name of the database collection
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]}, # JSON Schema fot this resource
        }.items()
)
link = dict(default_resource_settings.items() + \
        {
            "name": "link",
            "pattern": "/links/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Link",
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]},
        }.items()
)

login = dict(default_resource_settings.items() + \
        {
            "name": "login",
            "pattern": "/login$",
            # "model_class": "periscope.models.Port",
            # "collection_name": "ports",
            # "schema": {MIME['PSJSON']: SCHEMAS["port"]},
        }.items()
)

ports = dict(default_resource_settings.items() + \
        {
            "name": "ports",
            "pattern": "/ports$",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        }.items()
)
port = dict(default_resource_settings.items() + \
        {
            "name": "port",
            "pattern": "/ports/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        }.items()
)
nodes = dict(default_resource_settings.items() + \
        {
            "name": "nodes",
            "pattern": "/nodes$",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        }.items()
)
node = dict(default_resource_settings.items() + \
        {
            "name": "node",
            "pattern": "/nodes/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        }.items()
)
services = dict(default_resource_settings.items() + \
        {
            "name": "services",
            "pattern": "/services$",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        }.items()
)
service = dict(default_resource_settings.items() + \
        {
            "name": "service",
            "pattern": "/services/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        }.items()
)
getSchema = dict( \
        {
            "name": "getSchema",
            "pattern": "/getSchema$",
            "base_url":"",
            "handler_class": "periscope.handlers.SchemaHandler",
        }.items()
)
getParent = dict( \
        {
            "name": "getFolder",
            "pattern": "/getFolder$",
            "base_url":"",
            "handler_class": "periscope.handlers.FolderHandler",
        }.items()
)
paths = dict(default_resource_settings.items() + \
        {
            "name": "paths",
            "pattern": "/paths$",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        }.items()
)
path = dict(default_resource_settings.items() + \
        {
            "name": "path",
            "pattern": "/paths/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        }.items()
)
networks = dict(default_resource_settings.items() + \
        {
            "name": "networks",
            "pattern": "/networks$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        }.items()
)
network = dict(default_resource_settings.items() + \
        {
            "name": "network",
            "pattern": "/networks/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        }.items()
)
domains = dict(default_resource_settings.items() + \
        {
            "name": "domains",
            "pattern": "/domains$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        }.items()
)
domain = dict(default_resource_settings.items() + \
        {
            "name": "domain",
            "pattern": "/domains/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        }.items()
)
topologies = dict(default_resource_settings.items() + \
        {
            "name": "topologies",
            "pattern": "/topologies$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        }.items()
)
topology = dict(default_resource_settings.items() + \
        {
            "name": "topology",
            "pattern": "/topologies/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        }.items()
)

metadatas = dict(default_resource_settings.items() + \
        {
            "name": "metadatas",
            "pattern": "/metadata$", 
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        }.items()
)
metadata = dict(default_resource_settings.items() + \
        {
            "name": "metadata",
            "pattern": "/metadata/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        }.items()
)

events = dict(default_resource_settings.items() + \
        {
            "name": "events",
            "pattern": "/events$", 
            "handler_class" : "periscope.handlers.EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": "events_cache",
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        }.items()
)

event = dict(default_resource_settings.items() + \
        {
            "name": "event",
            "pattern": "/events/(?P<res_id>[^\/]*)$",
            "handler_class" : "periscope.handlers.EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": None,
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        }.items()
)

datas = dict(default_resource_settings.items() + \
        {
            "name": "datas",
            "pattern": "/data$", 
            "handler_class" : "periscope.handlers.DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        }.items()
)

data = dict(default_resource_settings.items() + \
        {
            "name": "data",
            "pattern": "/data/(?P<res_id>[^\/]*)$",
            "handler_class" : "periscope.handlers.DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        }.items()
)

measurements = dict(default_resource_settings.items() + \
        {
            "name": "measurements",
            "pattern": "/measurements$",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        }.items()
)
measurement = dict(default_resource_settings.items() + \
        {
            "name": "measurement",
            "pattern": "/measurements/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        }.items()
)

extents = dict(default_resource_settings.items() + \
         {
             "name"                   : "extents",
             "pattern"                : "/extents$",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         }.items()
)
extent = dict(default_resource_settings.items() + \
         {
             "name"                   : "extent",
             "pattern"                : "/extents/(?P<res_id>[^\/]*)$",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         }.items()
)

exnodes = dict(default_resource_settings.items() + \
         {
             "name"                   : "exnodes",
             "pattern"                : "/exnodes$",
             "handler_class"          : "periscope.handlers.ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         }.items()
)
exnode = dict(default_resource_settings.items() + \
         {
             "name"                   : "exnode",
             "pattern"                : "/exnodes/(?P<res_id>[^\/]*)$",
             "handler_class"          : "periscope.handlers.ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         }.items()
)

reg_settings = dict(default_resource_settings.items() + \
        {
            "name": "register",
            "pattern": "/register$",
            "model_class": "periscope.models.Service",
            "handler_class": "periscope.handlers.RegisterHandler",
            "collection_name": "register",
            "allow_get": False, "allow_delete": False, "allow_put": False,
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        }.items()
)


itemSubscription = {
    "base_url"      : "",
    "name"          : "itemSubscription",
    "pattern"       : "/subscribe/(?P<resource_type>[^\/]*)/(?P<resource_id>[^\/]*)$",
    "handler_class" : "periscope.handlers.SubscriptionHandler"
}

catSubscription = {
    "base_url"      : "",
    "name"          : "categorySubscription",
    "pattern"       : "/subscribe/(?P<resource_type>[^\/]*)$",
    "handler_class" : "periscope.handlers.SubscriptionHandler"
}

querySubscription = {
    "base_url"      : "",
    "name"          : "querySubscription",
    "pattern"       : "/subscribe",
    "handler_class" : "periscope.handlers.SubscriptionHandler"
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
    "pattern": "/$",
    "handler_class": "periscope.handlers.MainHandler",
}
about_handler_settings = {
    "resources": [],
    "name": "about",
    "base_url": "",
    "pattern": "/about$",
    "handler_class": "periscope.handlers.AboutHandler"
}

######################################################################
# PRE/POST content processing module definitions.
######################################################################
PP_MODULES=[]
#if (ENABLE_AUTH): 
#    PP_MODULES.append(('periscope.filters.dataAuth','DataAuth')) #[('periscope.#gemini', 'Gemini')]

# Settings for the GEMINI-specific authentication handlers
auth_user_settings= {
    "base_url": "",
    "handler_class": "periscope.gemini.AuthUserCredHandler",
    "name": "cred_geniuser",
    "pattern": "/credentials/geniuser",
    "schema": [MIME['PLAIN']]
}

auth_slice_settings= {
    "base_url": "",
    "handler_class": "periscope.gemini.AuthSliceCredHandler",
    "name": "cred_genislice",
    "pattern": "/credentials/genislice",
    "schema": [MIME['PLAIN']]
}
auth_login_settings= {
    "base_url": "",
    "handler_class": "periscope.filters.dataAuth.UserCredHandler",
    "name": "authenticate_user",
    "pattern": "/login",
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
            logger.warn("read_settings", msg="Could not find auth_uuid in node configuration")
else:
    AUTH_UUID = None

try:
    from M2Crypto import X509
    SERVER_CERT_FINGERPRINT = X509.load_cert(SSL_OPTIONS['certfile'], X509.FORMAT_PEM).get_fingerprint('sha1')
except Exception as e:
    SERVER_CERT_FINGERPRINT = ''
    logger = get_logger()
    logger.warn("read_settings", msg="Could not open SSL CERTFILE: %s" % e)
