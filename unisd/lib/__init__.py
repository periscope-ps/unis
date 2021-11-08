import argparse

from lace import logging
from wsgiref import simple_server

from unis import api, config, model, utils
from unis.settings import CMD_DEFAULTS, CONF_FILE_VAR, CONF_FILE_PATH
from unis.version import __version__

description="""
RESTful daemon for creating, accessing, and modifying unis records.  unisd adopts the unis data model
and exposes relationships as described in linked schema.
"""

def _build_command():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface",
                        help="Bind interface for listening to incoming connections.")
    parser.add_argument("-p", "--port", type=int,
                        help="TCP port for incoming connections.")
    parser.add_argument("-P", "--plugin", action="append",
                        help='Add a unis plugin (Ex. "unis.plugins.authorization" '
                        'must inherit from unis.plugin.Plugin)')
    parser.add_argument("-s", "--schema",
                        help="Path to an index file containing a JSON list of model URIs.")
    parser.add_argument("--cache", help="Path to model cache directory")
    parser.add_argument("--nopub", action="store_true",
                        help="Disable publication/subscription events for agent.")
    parser.add_argument("--lookupip", action="store_true",
                        help='Request external facing IP address for record '
                        'reference generation')
    parser.add_argument("-V", "--version", default=False, action="store_true",
                        help="Display software version")

    reg = parser.add_argument_group('Registration')
    reg.add_argument("-R", "--reg.community", action="append",
                     help="Add unis collection to a community.")
    reg.add_argument("-r", "--reg.parent", action="append",
                     help="Add an upstream parent to register records.")
    reg.add_argument("-U", "--reg.pub", action="append",
                     help="Add a public key for connecting to an upstream parent.")
    reg.add_argument("-u", "--reg.period", type=int,
                     help="Set the time between checkin with root instances.")
    reg.add_argument("-t", "--reg.threshold", type=int,
                     help="Maximum number of record values to include in manifests "
                     "before aggregating.")

    auth = parser.add_argument_group('Authentication/Authorization')
    auth.add_argument("--auth.engine",
                      help="Python path to the module used to handle authorization.")

    col = parser.add_argument_group('Collections')
    col.add_argument("--col.auth", type=int,
                     help="Set default authorization level for all collections in octal "
                     "read-write-execute form.")
    col.add_argument("--col.authfor", action="append",
                     help="Set authorization level for a collection in <colname>:<auth> "
                     "notation, see --col.auth for more.")

    db = parser.add_argument_group('Database')
    db.add_argument("-d", "--db.host", help="Set database host.")
    db.add_argument("-D", "--db.port", type=int, help="Set database port.")
    db.add_argument("-n", "--db.name", help="Set database name.")
    db.add_argument("--db.username", help="Set database user.")
    db.add_argument("--db.password", help="Set database password.")
    db.add_argument("-I", "--db.login", action="store_true",
                    help="Log into database interactively at startup.")

    return parser

##############################################################################################

def main():
    conf = config.MultiConfig(CMD_DEFAULTS, description, filevar=CONF_FILE_VAR,
                              defaultpath=CONF_FILE_PATH)
    conf.add_loglevel(logging.TRACE_OBJECTS)
    conf.add_loglevel(logging.TRACE_PUBLIC)
    conf.add_loglevel(logging.TRACE_ALL)
    args = conf.from_parser(_build_command(), include_logging=True)
    if args['version']:
        print(f"unisd v{__version__}")
        return
    log = utils.getLogger("config")
    log.info("Starting unisd...")
    log.debug("--Configuration--")
    conf.display(log)

    app = api.build(args)
    try:
        simple_server.make_server(args['interface'], args['port'], app).serve_forever()
    except Exception as exp:
        log.error(exp)
        if args['verbose'] > 1:
            import traceback
            traceback.print_exc()
