import os

def _expandvar(x, default=None):
    v = os.path.expandvars(x)
    return default if v == x else v

CONF_FILE_VAR, CONF_FILE_PATH = "$MUNDUS_CONFIG", "/etc/mundus.conf"
MUNDUS_ROOT = _expandvar("$MUNDUS_ROOT") or os.path.expanduser("~/.mundus")
SSL_PATH = os.path.join(MUNDUS_ROOT, "ssl")

MASTER_SCHEMA_URL = "http://unis.open.sice.indiana.edu/schema/2.0.0"

CMD_DEFAULTS = {
    "interface": "0.0.0.0",
    "port": 8888,
    "plugin": [],
    "schema": None,
    "cache": os.path.join(MUNDUS_ROOT, ".cache"),
    "verbose": 0,
    "logfile": None,
    "lookupip": False,
    "reg": {
        "community": [],
        "parent": [],
        "pub": [],
        "period": 60 * 60,
    },
    "auth": {
        "engine": "mundus.auth.none"
    },
    "db": {
        "port": 27017,
        "host": "127.0.0.1",
        "name": "mundus_db",
        "username": None,
        "password": None,
        "login": False
    },
    "col": {
        "auth": "740",
        "authfor": []
    },
}

IPLOOKUP_SERVICE = "http://ident.me"

SCHEMA_ROOT = "http://unis.open.sice.indiana.edu/schema/2.0.0"
topo = ["networkresource", "link", "node", "computenode", "physicalnode", "port", "service", "switchnode"]
measure = ["measurement", "metadata", "datum"]
data = ["exnode", "allocation", "ibp", "ceph", "rdma"]
SCHEMA_INDEX = []
[SCHEMA_INDEX.append(f"{SCHEMA_ROOT}/entities/topology/{v}") for v in topo]
[SCHEMA_INDEX.append(f"{SCHEMA_ROOT}/entities/measurements/{v}") for v in measure]
[SCHEMA_INDEX.append(f"{SCHEMA_ROOT}/entities/data/{v}") for v in data]

RELATION_SCHEMA = f"{SCHEMA_ROOT}/relationship"

ID_FIELD, TS_FIELD = ":id", ":ts"
