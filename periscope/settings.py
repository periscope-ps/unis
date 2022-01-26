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
import sys
from tornado.log import LogFormatter, enable_pretty_logging
from periscope.config import Argument

LIST_OPTIONS = ["unis.root_urls", "unis.communities"]
SELF_LOOKUP_URLS = [] #["http://ident.me"]

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
SSL_ENABLED=False

CONFIG_TEMPLATE = [
    Argument("-H", "--host", "", str, "Override automatice hostname generation"),
    Argument("-i", "--interface", "0.0.0.0", str, "Interface to bind port to"),
    Argument("-p", "--port", "8888", int, "Port to attach service to"),
    Argument("-s", "--softstart.enable", False, bool, "Poll backend port for connection when set, defaults to fail-fast"),
    Argument(None, "--softstart.pollrate", 5, int, "Rate for polling in seconds during soft start"),
    Argument(None, "--ssl.enable", SSL_ENABLED, bool, "Enable ssl connections"),
    Argument(None, "--ssl.cert", os.path.join(PERISCOPE_ROOT, "ssl/server.pem"), str, "Certificate file"),
    Argument(None, "--ssl.key", os.path.join(PERISCOPE_ROOT, "ssl/server.key"), str, "Keyfile for ssl"),
    Argument(None, "--ssl.cert_reqs", ssl.CERT_REQUIRED, bool, "Certificates required"),
    Argument(None, "--ssl.ca_certs", os.path.join(PERISCOPE_ROOT, "ssl/genica.bundle"), str, "Certificate bundle file"),
    Argument("-r", "--lookup", False, bool, "Change operation mode to parent directory server"),
    Argument("-D", "--db.engine", "motor.motor_tornado.MotorClient", str, "Define the interface module for the backend data store"),
    Argument(None, "--db.host", "127.0.0.1", str, "Hostname for the backend database"),
    Argument(None, "--db.port", 27017, int, "Port for the backend database"),
    Argument(None, "--db.name", "unis_db", str, "Name for the backend databas"),
    Argument("-M", "--ms.disable", True, bool, "Disable measurement store functionality"),
    Argument(None, "--ms.path", "", str, "Path to measurement store"),
    Argument(None, "--register.period", 3600, int, "Period of update to upstream"),
    Argument(None, "--register.paths", [], list, "Address(es) of upstream directory server(s)"),
    Argument("-C", "--register.communities", [], list, "Labels of communities data registers to"),
    Argument("-L", "--register.limitsize", 10, int, "Maximum number of records to report verbatim before aggregation"),
]

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

links = default_resource_settings.copy()
links.update({
            "name": "links",
            "pattern": "/links$", # The regex used to match the handler in URI
            "model_class": "periscope.models.Link", # The name of the database collection
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]}, # JSON Schema fot this resource
        })

link = default_resource_settings.copy()
link.update(
        {
            "name": "link",
            "pattern": "/links/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Link",
            "collection_name": "links",
            "schema": {MIME['PSJSON']: SCHEMAS["link"], MIME['PSBSON']: SCHEMAS["link"]},
        })

login = default_resource_settings.copy()
login.update(
        {
            "name": "login",
            "pattern": "/login$",
            # "model_class": "periscope.models.Port",
            # "collection_name": "ports",
            # "schema": {MIME['PSJSON']: SCHEMAS["port"]},
        })

ports = default_resource_settings.copy()
ports.update(
        {
            "name": "ports",
            "pattern": "/ports$",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        })

port = default_resource_settings.copy()
port.update(
        {
            "name": "port",
            "pattern": "/ports/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Port",
            "collection_name": "ports",
            "schema": {MIME['PSJSON']: SCHEMAS["port"], MIME['PSBSON']: SCHEMAS["port"]},
        })
        
nodes = default_resource_settings.copy()
nodes.update(
        {
            "name": "nodes",
            "pattern": "/nodes$",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        })
        
node = default_resource_settings.copy()
node.update(
        {
            "name": "node",
            "pattern": "/nodes/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Node",
            "collection_name": "nodes",
            "schema": {MIME['PSJSON']: SCHEMAS["node"], MIME['PSBSON']: SCHEMAS["node"]},
        })
        
services = default_resource_settings.copy()
services.update(
        {
            "name": "services",
            "pattern": "/services$",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })
        
service = default_resource_settings.copy()
service.update(
        {
            "name": "service",
            "pattern": "/services/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Service",
            "collection_name": "services",
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })
        
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
paths = default_resource_settings.copy()
paths.update(
        {
            "name": "paths",
            "pattern": "/paths$",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        })
        
path = default_resource_settings.copy()
path.update(
        {
            "name": "path",
            "pattern": "/paths/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Path",
            "collection_name": "paths",
            "schema": {MIME['PSJSON']: SCHEMAS["path"], MIME['PSBSON']: SCHEMAS["path"]},
        })
        
networks = default_resource_settings.copy()
networks.update(
        {
            "name": "networks",
            "pattern": "/networks$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        })
        
network = default_resource_settings.copy()
network.update(
        {
            "name": "network",
            "pattern": "/networks/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Network",
            "collection_name": "networks",
            "schema": {MIME['PSJSON']: SCHEMAS["network"], MIME['PSBSON']: SCHEMAS["network"]},
            "collections": {},
        })
        
domains = default_resource_settings.copy()
domains.update(
        {
            "name": "domains",
            "pattern": "/domains$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        })
        
domain = default_resource_settings.copy()
domain.update(
        {
            "name": "domain",
            "pattern": "/domains/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Domain",
            "collection_name": "domains",
            "schema": {MIME['PSJSON']: SCHEMAS["domain"], MIME['PSBSON']: SCHEMAS["domain"]},
            "collections": {},
        })
        
topologies = default_resource_settings.copy()
topologies.update(
        {
            "name": "topologies",
            "pattern": "/topologies$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        })
        
topology = default_resource_settings.copy()
topology.update(
        {
            "name": "topology",
            "pattern": "/topologies/(?P<res_id>[^\/]*)$",
            "handler_class": "periscope.handlers.CollectionHandler",
            "model_class": "periscope.models.Topology",
            "collection_name": "topologies",
            "schema": {MIME['PSJSON']: SCHEMAS["topology"], MIME['PSBSON']: SCHEMAS["topology"]},
            "collections": {},
        })

metadatas = default_resource_settings.copy()
metadatas.update(
        {
            "name": "metadatas",
            "pattern": "/metadata$", 
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        })
        
metadata = default_resource_settings.copy()
metadata.update(
        {
            "name": "metadata",
            "pattern": "/metadata/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Metadata",
            "collection_name": "metadata",
            "schema": {MIME['PSJSON']: SCHEMAS["metadata"], MIME['PSBSON']: SCHEMAS["metadata"]},
        })

events = default_resource_settings.copy()
events.update(
        {
            "name": "events",
            "pattern": "/events$", 
            "handler_class" : "periscope.handlers.EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": "events_cache",
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        })

event = default_resource_settings.copy()
event.update(
        {
            "name": "event",
            "pattern": "/events/(?P<res_id>[^\/]*)$",
            "handler_class" : "periscope.handlers.EventsHandler",
            "model_class": "periscope.models.Event",
            "collection_name": None,
            "schema": {MIME['PSJSON']: SCHEMAS["datum"], MIME['PSBSON']: SCHEMAS["datum"]},
        })

datas = default_resource_settings.copy()
datas.update(
        {
            "name": "datas",
            "pattern": "/data$", 
            "handler_class" : "periscope.handlers.DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        })

data = default_resource_settings.copy()
data.update(
        {
            "name": "data",
            "pattern": "/data/(?P<res_id>[^\/]*)$",
            "handler_class" : "periscope.handlers.DataHandler",
            "model_class": "periscope.models.Data",
            "collection_name": "data",
            "schema": {MIME['PSJSON']: SCHEMAS["data"], MIME['PSBSON']: SCHEMAS["data"]},
        })

measurements = default_resource_settings.copy()
measurements.update(
        {
            "name": "measurements",
            "pattern": "/measurements$",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        })
        
measurement = default_resource_settings.copy()
measurement.update(
        {
            "name": "measurement",
            "pattern": "/measurements/(?P<res_id>[^\/]*)$",
            "model_class": "periscope.models.Measurement",
            "collection_name": "measurements",
            "schema": {MIME['PSJSON']: SCHEMAS["measurement"], MIME['PSBSON']: SCHEMAS["measurement"]},
        })

extents = default_resource_settings.copy()
extents.update(
         {
             "name"                   : "extents",
             "pattern"                : "/extents$",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         })
         
extent = default_resource_settings.copy()
extent.update(
         {
             "name"                   : "extent",
             "pattern"                : "/extents/(?P<res_id>[^\/]*)$",
             "model_class"            : "periscope.models.Extent",
             "collection_name"        : "extents",
             "schema": {MIME['PSJSON']: SCHEMAS["extent"], MIME['PSBSON']: SCHEMAS["extent"]}
         })

exnodes = default_resource_settings.copy()
exnodes.update(
         {
             "name"                   : "exnodes",
             "pattern"                : "/exnodes$",
             "handler_class"          : "periscope.handlers.ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         })
         
exnode = default_resource_settings.copy()
exnode.update(
         {
             "name"                   : "exnode",
             "pattern"                : "/exnodes/(?P<res_id>[^\/]*)$",
             "handler_class"          : "periscope.handlers.ExnodeHandler",
             "model_class"            : "periscope.models.Exnode",
             "collection_name"        : "exnodes",
             "schema": {MIME['PSJSON']: SCHEMAS["exnode"], MIME['PSBSON']: SCHEMAS["exnode"]},
             "collections": { "extents": extent }
         })

reg_settings = default_resource_settings.copy()
reg_settings.update(
        {
            "name": "register",
            "pattern": "/register$",
            "model_class": "periscope.models.Service",
            "handler_class": "periscope.handlers.RegisterHandler",
            "collection_name": "register",
            "allow_get": False, "allow_delete": False, "allow_put": False,
            "schema": {MIME['PSJSON']: SCHEMAS["service"], MIME['PSBSON']: SCHEMAS["service"]},
        })


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
    logger = logging.getLogger("unis")
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

if SSL_ENABLED:
    try:
        from M2Crypto import X509
        SERVER_CERT_FINGERPRINT = X509.load_cert(SSL_OPTIONS['certfile'], X509.FORMAT_PEM).get_fingerprint('sha1')
    except Exception as e:
        SERVER_CERT_FINGERPRINT = ''
        logger = logging.getLogger("unis")
        logger.warning("read_settings", msg="Could not open SSL CERTFILE: %s" % e)
