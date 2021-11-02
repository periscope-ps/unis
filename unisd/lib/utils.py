import importlib, logging

_log_namespace = [
    "unisd",
    "unisd.app",
    "unisd.config",
    "unisd.db",
    "unisd.root",
    "unisd.model",
    "unisd.handler"
]

def getLogger(ns):
    if not ns.startswith("unisd"): ns = "unisd." + ns
    if ns not in _log_namespace:
        raise KeyError(f"'{ns}' is not a known logger namespace.")
    return logging.getLogger(ns)

def list_loggers():
    for n in _log_namespace:
        print(n)
def load_module(path):
    path = path.split(".")
    module = importlib.import_module(".".join(path[:-1]))
    return getattr(module, path[-1])
