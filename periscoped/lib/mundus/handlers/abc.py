import falcon, jsonschema

from functools import wraps
from pymongo import MongoClient

from mundus import model
from mundus.auth import none as noauth
from mundus.db import DBLayer
from mundus.settings import ID_FIELD, TS_FIELD
from mundus.utils import getLogger

class Handler(object):
    def __init__(self, schemas:dict, path:str, conf:dict, allow:list, db:MongoClient, id_field:str=None, ts_field:str=None, auth=None):
        self.log = getLogger("handler")
        self.auth = auth or noauth
        self.id, self.timestamp = id_field, ts_field = (id_field or ID_FIELD), (ts_field or TS_FIELD)
        self.allows = allow
        self.schemas, self._path, self._conf = schemas,path,conf
        self._plugins = []
        if self.schemas is None:
            self.schemas = []

        if path is not None:
            col = db[path]
            self._db = DBLayer(col, id_field, ts_field)
            col.create_index([(f"v.{id_field}", 1)])
            col.create_index([(f"v.{ts_field}", -1)])
            col.create_index([(f"v.{id_field}", 1), (f"v.{ts_field}", -1)],
                             unique=True)

    def get_uri(self, req):
        host = req.forwarded_host.split(':')
        if host[0] in ("localhost", "127.0.0.1") and self._conf['refhost']:
            host[0] = self._conf['refhost']
        return f"{req.forwarded_scheme}://{':'.join(host)}/{self._path}/"

    def add_plugin(self, plugin):
        self._plugins.append(plugin)

    def get_type(self, field:str):
        """
        Predicts the expected type of a field based on the schema
        defined for the handler

        :param field: The field name, which can be dot delimited
        :type field: str

        :return: A constructor function which builds an instance from a type
        :rtype: type
        """
        m = { "str": str, "number": float, "integer": int,
              "boolean": lambda x: x != "false", "null": lambda x: None }
        field = field.split('.')
        for d in self.schemas:
            for e in field:
                try:
                    d = d["properties"][e]
                except KeyError:
                    break
            return m.get(d.get("type", "str"), str)
        return str
    
    def _valid(self, record):
        for schema in self.schemas:
            try:
                model.validate(record, schema)
                return True
            except jsonschema.ValidationError as exp:
                self.log.debug(f"Validation error - {exp}")
        return False

    def _check_access(self, rid, username, op):
        user = self._db.get_user(username)
        sb = self._db.get_superblock(rid) or {
            "user": user['id'],
            "group": user['id'],
            "permissions": int(self._conf["col"]["auth"], base=8),
            "status": "good",
        }
        op = 4 if op == "r" else (2 if op == "w" else 1)
        if (((sb['permissions'] & 65 * op) and sb['user'] == user['id']) or 
            ((sb['permissions'] & 8 * op) and sb['group'] in user['groups']) or
            sb['permissions'] & 1 * op):
            return sb
        return False
        
    def _parse_query(self, query:str):
        # FIELD GRAMMAR
        # --------------
        # PARAM :- "limit=" val | "skip=" val | "sort=" SORT | "fields=" ["neg="] CSV | FIELD
        # FIELD :- sym "=" OR_EXPR
        # OR    :- OR_EXPR "|" AND_EXPR | AND_EXPR
        # AND   :- AND_EXPR "," NOT | NOT
        # NOT   :- CMP | "not=" CMP
        # CMP   :- "gt=" val | "ge=" val | "lt=" val | "le=" val | "reg=" val | "exists=" val | val
        # SORT  :- SORT "," SP | SP
        # SP    :- sym "=" ("1" | "-1")
        # CSV   :- CSV "," sym | sym
        def SORT(e):
            f = lambda k,v: (k, pymongo.ASCENDING if v == "1" else pymongo.DECENDING)
            return [f(v.split('=')) for v in e.split(',')]
        def FIELDS(e):
            d = 1
            if e.startswith("neg="): e,d = e[4:], 0
            return {k: d for k in e.split(',')}
        def expr_from_field(f,e):
            def OR(e):
                e = e.rsplit('|', 1)
                return {"$or": [OR(e[0]), AND(e[1])]} if len(e) > 1 else AND(e[0])
            def AND(e):
                e = e.rsplit(',', 1)
                return {"$and": [AND(e[0]), NOT(e[1])]} if len(e) > 1 else NOT(e[0])
            def NOT(e):
                return {"$not": CMP(e[4:])} if e.startswith("not=") else CMP(e)
            def CMP(e):
                m = {'gt=': '$gt', 'ge=': '$gte', 'lt=': '$lt', 'le=': '$lte', 'reg=': '$regex', 'exists=': '$exists'}
                for k,v in m.items():
                    if e.startswith(k):
                        return {v: self.get_type(f)(e[len(k):])}
                return self.get_type(f)(e)
            return OR(e)
        v = {}
        if query:
            op_map = {
                "limit": lambda f,e: int(e),
                "skip": lambda f,e: int(e),
                "sort": lambda f,e: SORT(e),
                "fields": lambda f,e: FIELDS(e),
            }
            self.log.debug(f"Parsing query '{query}'")
            for op in query.split("&"):
                op,e = op.split("=", 1)
                try: v[op] = op_map.get(op, expr_from_field)(op, e)
                except ValueError:
                    self.log.warn(f"Bad query field, cannot parse type '{op}={e}'")
                    raise falcon.HTTPInvalidParam("Could not parse param type", op)
        result = {}
        try: result["limit"] = v.pop("limit")
        except KeyError: result["limit"] = None
        try: result["skip"] = v.pop("skip")
        except KeyError: result["skip"] = 0
        try: result["sort"] = v.pop("sort")
        except KeyError: result["sort"] = [(self.timestamp, -1)]
        try: result["projection"] = v.pop("fields")
        except KeyError: result["projection"] = {}
        result['filter'] = v
        return result

    def on_get(self, req, resp):
        raise NotImplemented()

    def get_routes(self, as_tempate:bool=True):
        """
        Generates a list of routes expected by the handler

        :param as_template: If true, adds template components of the path, otherwise only returns full paths
        :type as_template: bool

        :return: List of routes expected by the handler
        :rtype: list[str]
        """
        raise NotImplemented()

    def publish(self, event, body):
        #TODO
        pass
