import copy, re, time, os, pathlib, json, logging
from collections import defaultdict
from collections.abc import MutableSequence
from uuid import uuid4
from threading import Thread,RLock

class LockedList(MutableSequence):
    def __init__(self, *args):
        self.lock = RLock()
        self._ls = list(args)

    def __getitem__(self, k):
        with self.lock:
            return self._ls[k]

    def __setitem__(self, k, v):
        with self.lock:
            self._ls[k] = v

    def __delitem__(self, k):
        with self.lock:
            del self._ls[k]

    def __len__(self):
        with self.lock:
            return len(self._ls)

    def insert(self, k, v):
        with self.lock:
            self._ls.insert(k,v)

class Collection(object):
    def __init__(self, name):
        self._v = LockedList()
        self.name = name

    @classmethod
    def load(cls, filepath, name):
        filepath = os.path.join(filepath, name)
        col = Collection(name)
        with col._v.lock:
            with open(filepath) as f:
                for v in json.load(f):
                    try:
                        col._v.append(v)
                    except Exception:
                        logging.getLogger("unis.db").warn(f"Failed to load records for {os.path.join(filepath, col.name)}")
        return col

    async def create_index(self, *args, **kwargs): pass

    def _filter(self, q):
        try: q.pop("\\$status")
        except: pass
        def f(x):
            g = lambda d,f: d[f[0]] if len(f) == 1 else g(d[f[0]], f[1:])
            lop = { '$and': lambda q, ctx: all([r(v, ctx) for v in q]),
                    '$or': lambda q, ctx: any([r(v, ctx) for v in q]),
                    '$not': lambda q, ctx: not r(q, ctx) }
            mop = { '$eq': lambda x,y: re.match(y,x) if isinstance(y, re.Pattern) else x == y,
                    '$ne': lambda x,y: x != y,
                    '$gt': lambda x,y: y > x,
                    '$gte': lambda x,y: y >= x,
                    '$lt': lambda x,y: y < x,
                    '$lte': lambda x,y: y <= x,
                    '$in': lambda x,y: y in x}
            def r(q, ctx=None):
                if not isinstance(q, dict): return mop["$eq"](ctx, q)
                vals = []
                for k,v in q.items():
                    try: vals.append(lop[k](v, ctx))
                    except KeyError:
                        try: vals.append(mop[k](v, ctx))
                        except KeyError:
                            try:
                                vals.append(r(v, g(x, k.split('.'))))
                            except KeyError:
                                return False
                return all(vals)
            return r(q)
        return f

    def find(self, filter=None, projection=None, skip=0, limit=None, sort=None, **kwargs):
        try: _id = projection.pop("_id")
        except (AttributeError, KeyError): _id = 0
        def p(x):
            r = {}
            if not projection:
                r = copy.deepcopy(x)
            elif isinstance(projection, list):
                for k in projection:
                    try: r[k] = copy.deepcopy(x[k])
                    except KeyError: r = {}
            else:
                is_inc = list(projection.values())[0] if projection else False
                if not all([v == is_inc for v in projection.values()]):
                    raise ValueError("Projection may not both include and exclude values")
                r = {} if is_inc else copy.deepcopy(x)
                for k,v in projection.items():
                    try:
                        r.__setitem__(k, copy.deepcopy(x[k])) if is_inc else r.pop(k)
                    except KeyError: pass

            if _id == 1:
                r['_id'] = x['_id']
            else:
                try: r.pop('_id')
                except KeyError: pass
            return r

        def s(ls):
            if sort is not None:
                for k,v in sort:
                    ls = sorted(ls, key=lambda x: x.get(k, None), reverse=(v == -1))
            return ls

        return Cursor(self._v, self._filter(filter), p, s, skip, limit)

    async def find_one(self, *args, **kwargs):
        c = self.find(*args, **kwargs)
        if c.alive:
            return c.next_object()

    def _insert(self, d):
        if "_id" not in d:
            try: d["_id"] = f"{d['id']:d['ts']}"
            except KeyError: d["_id"] = str(uuid4())
        self._v.append(copy.deepcopy(d))
        return d

    async def insert_one(self, document): return self._insert(document)
    async def insert_many(self, documents):
        return [self._insert(d) for d in documents]

    async def update_many(self, query, document):
        result = []
        for v in filter(self._filter(query), self._v):
            if "$set" in document: document = document["$set"]
            v.update(document)
            result.append(v)
        return result

    async def find_one_and_update(self, query, document, upsert=True, **kwargs):
        try:
            v = next(filter(self._filter(query), self._v))
            if "$set" in document: document = document["$set"]
            v.update(document)
        except StopIteration:
            if upsert:
                self._v.append(document)
        return [v]

    async def delete_many(self, query):
        todo,result = [], []
        f = self._filter(query)
        for i, v in enumerate(self._v):
            if f(v): todo.append(i)
        for idx in reversed(todo):
            result.append(self._v.pop(idx))
        return result

    async def count_documents(self, query, skip=0, limit=None):
        v = list(filter(self._filter(query), self._v))
        return max(0, min(len(v) - skip, limit if limit is not None else len(v)))


class CappedCollection(Collection):
    def __init__(self, name, size=0):
        super().__init__(name)

class Cursor(object):
    def __init__(self, c, f, proj, sort, skip, limit):
        self._v = [proj(v) for v in sort(c) if f(v)]
        self.head = skip
        self.tail = len(self._v) if not limit else skip + limit

    @property
    def alive(self):
        return self.head < self.tail

    @property
    def fetch_next(self):
        async def _done():
            return self.alive
        return _done()

    def next_object(self):
        self.head += 1
        return self._v[self.head-1]

    def __aiter__(self):
        return self
    async def __anext__(self):
        if self.alive:
            return self.next_object()
        else:
            raise StopAsyncIteration

class Database(object):
    @classmethod
    def load(cls, filepath, name, *args, **kwargs):
        filepath = os.path.join(filepath, name)
        db = Database(*args, **kwargs)
        pathlib.Path(filepath).mkdir(parents=True, exist_ok=True)
        cols = next(os.walk(filepath))[2]
        for c in cols:
            if c.startswith("__capped__"):
                c, _cls = c.strip("__capped__"), CappedCollection
            else:
                _cls = Collection
            db._cols[c] = _cls.load(filepath, c)
        return db

    def __init__(self, *args, **kwargs):
        self._cols = {}


    async def create_collection(self, name, size=0, capped=False, **kwargs):
        self._cols[name] = CappedCollection(name, size) if capped else Collection(name)

    def __getitem__(self, k):
        if k not in self._cols:
            self._cols[k] = Collection(k)
        return self._cols[k]

class Client(object):
    def __init__(self, *args, snapshot=None, interval=30, **kwargs):
        self._args, self._kwargs, self._dbs = args, kwargs, {}

        if snapshot is not None:
            self._load_db(snapshot)
            t = Thread(target=self._snap, kwargs={'p': snapshot, 's':int(interval)}, daemon=True)
            t.start()

    def _snap(self, p, s):
        log = logging.getLogger("unis.db")
        while True:
            time.sleep(s)
            log.debug("--Snapshot--")
            for n,db in self._dbs.items():
                _p = os.path.join(p, n)
                pathlib.Path(_p).mkdir(parents=True, exist_ok=True)
                for k,c in db._cols.items():
                    with c._v.lock:
                        with open(os.path.join(_p, k), 'w') as f:
                            json.dump(c._v._ls, f)
            log.debug("============")

    def _load_db(self, filepath):
        pathlib.Path(filepath).mkdir(parents=True, exist_ok=True)
        dbs = next(os.walk(filepath))[1]
        for p in dbs:
            self._dbs[p] = Database.load(filepath, p, *self._args, **self._kwargs)

    def __getitem__(self, k):
        if k not in self._dbs:
            self._dbs[k] = Database(*self._args, **self._kwargs)
        return self._dbs[k]
