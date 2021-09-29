
class DataHandler(object):
    def __init__(self, schemas, path, conf, allow, db, auth):
        self.schemas = []

    def on_get(self, req, resp, id):
        raise NotImplemented()

    def on_post(self, req, resp, id):
        raise NotImplemented()

    def get_routes(self, as_template=True):
        return [("/data/{id}", "")] if as_template else []
