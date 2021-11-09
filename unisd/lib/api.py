import falcon, pymongo, requests, threading, time

from getpass import getpass
from urllib.parse import urlparse
from lace import logging

from unis import utils, model, handlers
from unis.config import MultiConfig
from unis.middleware import ContentTypeNegotiator, BSONHandler
from unis.settings import CMD_DEFAULTS, CONF_FILE_VAR, CONF_FILE_PATH, IPLOOKUP_SERVICE, SCHEMA_INDEX

log = utils.getLogger("app")
def _query_remote(host):
    try:
        res = requests.get(IPLOOKUP_SERVICE)
        res.raise_for_status()
        return res.text
    except requests.exception.ConnectionError as exp:
        log.error("Could not contact external IP lookup")
        raise

def _build_schema_index(schema):
    if schema is not None:
        try:
            with open(schema, 'r') as f:
                return f.read().split('\n')
        except OSError:
            log.warn(f"Failed to read schema file '{schema}'")
    return SCHEMA_INDEX

    
def _update_parents(config):
    #  TODO Generate service record
    log = utils.getLogger("app")
    remote_record = {}
    while config['reg']['parent']:
        for i in enumerate(config['reg']['parent']):
            h = config['reg']['parent'][i]
            try: v = config['reg']['pub'][i]
            except IndexError: v = None
            try:
                request.post(h, data=remote_record, verify=v)
            except requests.ConnectionError:
                log.warn(f"Failed to connect to upstream parent '{h}'")
        time.sleep(config['reg']['period'])

def _create_handlers(app, config, db, auth):
    hmap = {
        'self': handlers.ResourceHandler,
        'collection': handlers.CollectionHandler,
        'data': handlers.DataHandler
    }
    insts, hdls = [], {}
    for _, schema in model.cache(config['cache'], config['schema']).values():
        for link in model.get_links(schema, config['cache']):
            ref = urlparse(link['href']).path.strip('/').split('/')
            if len(ref) > 4:
                log.warn(f"Invalid path in schema link definition - {link['href']}")
                continue
            ref = ref[2] if len(ref) == 4 else ref[0]
            ty = hmap.get(link['rel'], handlers.RelationHandler)
            if (ty, ref) not in hdls:
                hdls[(ty, ref)] = [[schema],
                                   set(link.get("targetHints", []).get("allow", []))]
            else:
                hdls[(ty, ref)][0].append(schema)
                hdls[(ty, ref)][1] |= set(link.get("targetHints", []).get("allow", []))
    for (HDL, p), (s, a) in hdls.items():
        hdl = HDL(s, p, config, allow=list(a), db=db, auth=auth)
        log.debug(f"Creating '{HDL.__name__}' for '{p}'")
        insts.append(hdl)
        for r,s in hdl.get_routes():
            yield (r,s), hdl

    info = {
        "schema_load_miss": sum([not v for v,_ in model.cache(config['cache'], config['schema']).values()])
    }
    ah = handlers.AboutHandler(insts, config, info=info, db=db)
    for r,s in ah.get_routes():
        yield (r,s), ah
    yield ("/", None), handlers.RootHandler(insts, config, db=db)

def build(config=None):
    if config is None:
        conf = MultiConfig(CMD_DEFAULTS, filevar=CONF_FILE_VAR, defaultpath=CONF_FILE_PATH)
        conf.add_loglevel(logging.TRACE_OBJECTS)
        conf.add_loglevel(logging.TRACE_PUBLIC)
        conf.add_loglevel(logging.TRACE_ALL)
        config = conf.from_file(include_logging=True)
    log.info("Building application")
    config['refhost'] = _query_remote(config['host']) if config['lookupip'] else None
    config['schema'] = _build_schema_index(config['schema'])
    app = falcon.App(middleware=ContentTypeNegotiator())

    media = {
        "application/bson": BSONHandler()
    }
    app.req_options.media_handlers.update(media)
    app.resp_options.media_handlers.update(media)

    args = {k: config['db'][k] for k in ["host", "port", "username", "password"]}
    print(args)
    if config['db']['login']:
        args['username'] = input("DB Username: ")
        args['password'] = getpass("DB Password: ")

    db = pymongo.MongoClient(**args)[config['db']['name']]
    auth = utils.load_module(config['auth']['engine'])
    handlers = _create_handlers(app, config, db, auth)

    threading.Thread(target=_update_parents, args=(config,), daemon=True).start()

    for p in config['plugin']:
        try:
            try:
                P = utils.load_module(p)(app)
                for _,h in handlers:
                    h.add_plugin(P)
            except AttributeError:
                log.warn(f"Invalid plugin type, cannot initialize")
        except (ImportError, AttributeError):
            log.warn(f"Failed to import plugin '{p}'")
    for (p,s),h in handlers:
        app.add_route(p, h, suffix=s)
    return app
