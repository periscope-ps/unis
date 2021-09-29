import falcon, time

from bson.objectid import ObjectId

from mundus import model
from mundus.handlers.collection import CollectionHandler
from mundus.settings import RELATION_SCHEMA

class RelationHandler(CollectionHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schemas = [model.get(RELATION_SCHEMA, self._conf['cache'])]

    def on_get_single(self, req, resp, id):
        args = self._parse_query(req.query_string)
        user = self._db.get_user(self.auth.validate(req.auth, self._conf))
        records = self._db.find_one(f={**{self.id: id}, **args['filter']},
                                    proj=args['projection'],
                                    loc=self.get_uri(req),
                                    user=user)
        try: resp.media = records[0]
        except IndexError: resp.media = []
        resp.status = falcon.HTTP_200

    def on_get_subject(self, req, resp, col, id):
        records = self._db.left_join("subject", col, id, **self._get_args(req))
        resp.media = records
        resp.status = falcon.HTTP_200

    def on_get_target(self, req, resp, col, id):
        records = self._db.left_join("target", col, id, **self._get_args(req))
        resp.media = records
        resp.status = falcon.HTTP_200

    def get_routes(self, as_template=True):
        n = self._path.split('/')[0]
        templates = [(f"/{{col}}/{{id}}/{n}/subject", "subject"),
                     (f"/{{col}}/{{id}}/{n}/target", "target"),
                     (f"/{n}/{{id}}", "single")
        ]
        return [(f"/{n}", "")] + (templates if as_template else [])
