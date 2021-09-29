import falcon, jsonschema, time

from bson.objectid import ObjectId

from mundus.handlers.abc import Handler

class CollectionHandler(Handler):
    def _get_args(self, req):
        args = self._parse_query(req.query_string)
        return {
            "f": args['filter'],
            "proj": args['projection'],
            "sort": args['sort'],
            "skip": args['skip'],
            "limit": args['limit'],
            "loc": self.get_uri(req),
            "user": self._db.get_user(self.auth.validate(req.auth, self._conf))
        }

    def _normalize_record(self, r):
        r[self.id] = r.get(self.id, str(ObjectId()))
        r[self.timestamp] = int(time.time() * 1000000)
        r[":type"] = r.get(":type", self.schemas[0]['$id'])
        return r

    def on_get(self, req, resp):
        records = self._db.find(**self._get_args(req))
        resp.media = records
        resp.status = falcon.HTTP_200

    def on_post(self, req, resp):
        data = req.media
        user = self.auth.validate(req.auth, self._conf)
        if not isinstance(data, list): data = [data]

        for i, r in enumerate(data):
            r = self._normalize_record(r)
            if not self._valid(r):
                msg = "Invalid record matches no schema"
                raise falcon.HTTPUnprocessableEntity(msg)

            sb = self._check_access(r[self.id], user, 'w')
            if not sb:
                raise falcon.HTTPForbidden()
            sb.update({'v': r, 'status': 'good'})
            for p in self._plugins:
                if hasattr(p, "pre_post"): p.pre_post(r, self._conf)

            try:
                del r['selfRef']
            except KeyError: pass
            data[i] = sb

        self._db.insert(data, self.get_uri(req))
        [self.publish("POST", r['v']) for r in data]
        resp.media = [r['v'] for r in data]
        resp.status = falcon.HTTP_200

    def get_routes(self, as_template=True):
        name = self._path.split('/')[0]
        return [(f"/{name}", "")]
