import copy, json, jsonschema, os, requests

from unis import utils
from unis.config import ConfigError
from unis.exceptions import UnisSchemaError

_CACHE, _REFS = {}, {}
log = utils.getLogger("model")
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

def _get_local_cache(path, index):
    os.makedirs(path, exist_ok=True)
    for dname, _, ls in os.walk(path):
        for n in ls:
            fp = os.path.join(dname, n)
            if os.path.isfile(fp):
                with open(fp, 'r') as f:
                    log.debug(f"  Loading model '{fp}'")
                    try: schema = json.load(f)
                    except json.JSONDecodeError:
                        log.warn(f"Unable to parse schema file '{fp}'")
                        raise UnisSchemaError(f"Invalid schema file '{fp}'") from None
                    log.debug(f"    +- '{schema['$id']}'")
                    log.debug("    |- Adding to references")
                    _REFS[schema['$id']] = schema
                    if schema['$id'] in index:
                        log.debug("    |- Adding to cache")
                        yield schema

def _get_remote(s, path):
    def _get(s):
        log.info(f"Requesting remote schema '{s}'")
        try:
            r = requests.get(s)
            r.raise_for_status()
            return r.json()
        except requests.ConnectionError:
            log.warn(f"Unable to retrieve schema '{s}' from source")
            raise UnisSchemaError(f"Unable to retrieve schema '{s}'") from None
        except json.JSONDecodeError:
            log.warn(f"Unable to parse schema file '{s}' from source")
            raise UnisSchemaError(f"Unable to read schema '{s}'") from None
    schema = _get(s)
    _REFS[schema['$id']] = schema
    if path is not None:
        fp = os.path.join(path, schema['$id'].replace('/', ''))
        with open(fp, 'w') as f:
            json.dump(schema, f)

def _get_remote_cache(path, index, cache):
    for s in filter(lambda x: x not in cache, index):
        log.debug(f"  Cache miss on '{s}'")
        yield _get_remote(s, path)

def cache(path, index):
    """
    :param path: Path to the local schema cache
    :type path: string

    :param index: List of requested schema the server exposes
    :type index: list[str]

    :return: List of JSON schemas
    :rtype: dict[str,tuple[bool, dict]]

    Generates and returns an internal cache of schema for each
    model used by the server. Result keys map to the schema
    '$id' field while the value tuple represents the 
    (FOUND_LOCAL, SCHEMA) values.
    """
    log.info("Constructing schema cache...")
    if _CACHE:
        log.debug("Cache exists, using internal models")
        return _CACHE.copy()
    _CACHE.update({v['$id']: (True, v) for v in _get_local_cache(path, index)})
    _CACHE.update({v['$id']: (False, v) for v in _get_remote_cache(path, index, _CACHE)})
    return _CACHE.copy()
