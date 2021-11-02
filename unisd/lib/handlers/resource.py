import falcon, time

from unis.db import DBLayer, AccessError
from unis.handlers.abc import Handler

class ResourceHandler(Handler):
    def _get_args(self, rid, req, args=None):
        if args is None:
            args = self._parse_query(req.query_string)
        return {
            "f": {**{self.id: rid}, **args['filter']},
            "proj": args['projection'],
            "loc": self.get_uri(req),
            "user": self._db.get_user(self.auth.validate(req.auth, self._conf))
        }

    def on_get(self, req, resp, id):
        records = self._db.find_one(**self._get_args(id, req))
        try: resp.media = records[0]
        except IndexError: resp.media = []
        resp.status = falcon.HTTP_200

    def on_get_hist(self, req, resp, id):
        query = self._parse_query(req.query_string)
        args = {**self._get_args(id, req, query), "history": True, "limit": query['limit']}
        resp.media = self._db.find_one(**args) or []
        resp.status = falcon.HTTP_200

    def on_put(self, req, resp, id):
        data = req.media
        if data[self.id] != id:
            raise falcon.HTTPUnprocessableEntity("Record ID does not match reference")
        data[self.timestamp] = int(time.time() * 1000000)
        args = self._get_args(id, req)
        sb = self._check_access(id, args['user'], 'w')
        if not sb:
            raise falcon.HTTPForbidden()
        try:
            record = self._db.find_one(**args)[0]
        except (AccessError, IndexError):
            raise falcon.HTTPNotFound("Record does not exist")
        record.update(data)
        if not self._valid(record):
            raise falcon.HTTPUnprocessableEntity("Cannot update record - Invalid json")
        try: self._db.update(id, data, self.get_uri(req))
        except AccessError:
            raise falcon.HTTPNotFound("Record does not exist")
        self.publish("PUT", record)
        resp.media = record
        resp.status = falcon.HTTP_200

    def on_delete(self, req, resp, id):
        user = self.auth.validate(req.auth, self._conf)
        sb = self._check_access(id, user, 'w')
        if not sb:
            raise falcon.HTTPForbidden()
        try: self._db.delete(id)
        except AccessError:
            raise falcon.HTTPNotFound("Record does not exist")
        self.publish("DELETE", {'selfRef': f"{self.get_uri(req)}{id}"})
        resp.status = falcon.HTTP_204

    def get_routes(self, as_template=True):
        n = self._path.split('/')[0]
        if as_template:
            return [(f"/{n}/{{id}}", ""), (f"/{n}/{{id}}/history", "hist")]
        return []
