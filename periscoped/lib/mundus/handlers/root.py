import falcon

from mundus import utils
from mundus.handlers.abc import Handler
from mundus.handlers.relation import RelationHandler
from mundus.handlers.collection import CollectionHandler
from mundus.handlers.resource import ResourceHandler
from mundus.settings import RELATION_SCHEMA

tys = {
    CollectionHandler: 'collection',
    ResourceHandler: 'self'
}
log = utils.getLogger("root")
class RootHandler(Handler):
    def __init__(self, hdls, config, db):
        super().__init__(None, None, config, ["GET"], db)
        self._build_desc(hdls)

    def _build_desc(self, hdls):
        log.info("Building server description")
        self._desc = []
        for hdl in hdls:
            ty = tys.get(type(hdl), 'link')
            if ty == 'link': items = [{'$ref': RELATION_SCHEMA}]
            else: items = [{'$ref': s['$id']} for s in hdl.schemas]
            for r,_ in hdl.get_routes(as_template=False):
                self._desc.append({
                    'rel': ty,
                    'href': r,
                    'targetschema': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'oneOf': items
                        }
                    }
                })

    def on_get(self, req, resp):
        opts = self._parse_query(req.query_string)
        f = lambda x: all([x.get(k, "") == v for k,v in opts['filter'].items()])
        proj = lambda x: {k:v for k,v in x.items() if not opts['projection'] or k in opts['projection']}
        result = [proj(v) for v in self._desc if f(v)]
        resp.media = result
        resp.status = falcon.HTTP_200

    def get_routes(self, as_template=True):
        """
        Generates a list of routes expected by the handler

        :param as_template: If true, adds template components of the path, otherwise only returns full paths
        :type as_template: bool

        :return: List tuples containing a route/suffix pair expected by the handler
        :rtype: list[tuple]
        """
        return [("/", "")]
