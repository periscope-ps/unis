from unis.handlers.abc import Handler
from unis.handlers.collection import CollectionHandler
from unis.handlers.relation import RelationHandler

class AboutHandler(Handler):
    def __init__(self, hdls, config, db):
        super().__init__(None, "about", config, ["GET"], db)
        self._refs = [h._path.split('/')[0] for h in hdls if isinstance(h, (CollectionHandler, RelationHandler))]

    def on_get(self, req, resp):
        #TODO
        super().on_get(req, resp)

    def on_get_col(self, req, resp):
        #TODO
        super().on_get(req, resp)

    def get_routes(self, as_template=True):
        return [(f"/about", "")] + [(f"/about/{v}", "col") for v in self._refs]
