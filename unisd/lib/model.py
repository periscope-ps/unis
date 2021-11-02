import copy, json, jsonschema, os, requests

from unis import utils
from unis.settings import SCHEMA_INDEX
from unis.config import ConfigError

_CACHE, _REFS = {}, {}
log = utils.getLogger("model")
def _get_remote(s, path=None):
    log.info(f"Requesting remote schema '{s}'")
    schema = None
    try:
        r = requests.get(s)
        r.raise_for_status()
        schema = r.json()
        _CACHE[schema['$id']] = _REFS[schema['$id']] = schema
        if path is not None:
            path = os.path.join(path, schema['$id'].replace('/', ''))
            with open(path, 'w') as f:
                json.dump(schema, f)
    except requests.ConnectionError:
        log.warn(f"Unable to retrieve schema '{s}' from source")
    except json.JSONDecodeError:
        log.warn(f"Unable to parse schema file '{s}' from source")
    return schema

def validate(record, schema):
    resolver = jsonschema.RefResolver(schema['$id'], schema, store=_REFS)
    try: jsonschema.validate(record, schema, resolver=resolver)
    except jsonschema.RefResolutionError as exp:
        log.error(f"Failed to retrieve remote schema '{schema['$id']}'")
        raise jsonschema.ValidationError from exp

def get(uri, path=None):
    """
    Get a schema by id.  (Performs remote query if schema is no
    available locally)
    """
    return _REFS.get(uri, None) or _get_remote(uri, path)

def get_links(schema, path):
    """
    :param schema: A JSON schema
    :type schema: dict

    :return: List of links
    :rtype: list[dict]

    Takes a schema and expands all instances of 'allof' found in
    the schema and returns a list of links associated with
    the schema.  This may require remote calls, but the internal
    and local caches will be used when possible.
    """
    _get = lambda x: _REFS.get(x['$ref'], None) or _get_remote(x['$ref'], path)
    log.info(f"Creating link list for '{schema['$id']}'")
    parents = [schema] + [_get(v) for v in schema.get("allOf", [])]
    links, seen = {}, []
    while parents:
        p = parents.pop()
        if p['$id'] not in seen:
            log.debug(f"  +- Looking for links in '{p['$id']}'")
            seen.append(p['$id'])
            parents += [_get(v) for v in p.get("allOf", [])]
            for l in p.get('links', []):
                log.debug(f"  |- Link found for '{l['href']}'")
                links[l['href']] = l
    return list(links.values())

def cache(path, index):
    """
    :param path: Path to the local schema cache
    :type path: string

    :param index: List of requested schema the server exposes
    :type index: list[str]

    :return: List of JSON schemas
    :rtype: list[dict]

    Generates and returns an internal cache of schema for each
    model used by the server.
    """
    log.info("Constructing schema cache...")
    if _CACHE:
        log.debug("Cache exists, using internal models")
        return _CACHE
    os.makedirs(path, exist_ok=True)
    for n in os.listdir(path):
        fp = os.path.join(path, n)
        with open(fp, 'r') as f:
            if os.path.isfile(fp):
                try:
                    log.debug(f"  Loading model '{fp}'")
                    schema = json.load(f)
                    log.debug(f"    +- '{schema['$id']}'")
                    log.debug("    |- Adding to references")
                    _REFS[schema['$id']] = schema
                    if schema['$id'] in index:
                        log.debug("    |- Adding to cache")
                        _CACHE[schema['$id']] = schema
                except json.JSONDecodeError:
                    log.warn(f"Unable to parse schema file '{fp}'")
    for s in index:
        if s not in _CACHE:
            log.debug(f"  Cache miss on '{s}'")
            _get_remote(s, path)
    return _CACHE
