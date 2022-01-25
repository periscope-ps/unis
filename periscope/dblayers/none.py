import copy, re
from collections import defaultdict
from uuid import uuid4

class Collection(object):
    def __init__(self, name):
        self._v = []
        self.name = name

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
                    '$lte': lambda x,y: y <= x }
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

    async def insert_one(self, document): self._insert(document)
    async def insert_many(self, documents):
        for d in documents: self._insert(d)

    async def update_many(self, query, document):
        for v in filter(self._filter(query), self._v):
            v.update(document)

    async def find_one_and_update(self, query, document, upsert=True, **kwargs):
        try:
            v = next(filter(self._filter(query), self._v))
            v.update(document)
        except StopIteration:
            if upsert:
                self._v.append(document)

    async def delete_many(self, query):
        print(f"DELETE_MANY [{self.name}]: {self._v}")
        print(f"delete [{name}]: {query}")
        todo = []
        f = self._filter(query)
        for i, v in enumerate(self._v):
            if f(v): todo.append(i)
        for idx in reversed(todo):
            self._v.pop(idx)

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
    def __init__(self, *args, **kwargs):
        self._cols = {}

    async def create_collection(self, name, size=0, capped=False, **kwargs):
        self._cols[name] = CappedCollection(name, size) if capped else Collection(name)

    def __getitem__(self, k):
        if k not in self._cols:
            self._cols[k] = Collection(k)
        return self._cols[k]

class Client(object):
    def __init__(self, *args, **kwargs):
        self._args, self._kwargs, self._dbs = args, kwargs, {}

    def __getitem__(self, k):
        if k not in self._dbs:
            self._dbs[k] = Database(*self._args, **self._kwargs)
        return self._dbs[k]
