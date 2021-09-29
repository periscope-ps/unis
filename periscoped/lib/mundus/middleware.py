import bson, falcon

MIME_TYPES = [
    ("text", "plain"),
    ("application", "bson"),
    ("application", "json")
]

class BSONHandler(object):
    def __init__(self, dumps=None, loads=None):
        self.dumps = dumps or bson.encode
        self.loads = loads or bson.decode

    def deserialize(self, stream, content_type, content_length):
        try:
            return self.loads(stream.read().decode('utf-8'))
        except ValueError as e:
            raise falcon.HTTPBadRequest(f'Invalid BSON, could not parse body - {e}')

    def serialize(self, media, content_type):
        r = self.dumps(media)
        return r if isinstance(r, bytes) else r.encode('utf-8')

class ContentTypeNegotiator(object):
    def _match(self, ls):
        for a,a_s in ls:
            for b,b_s in MIME_TYPES:
                if a == "*":
                    return f"{a}/{a_s}"
                if a.lower() == b:
                    if a_s.lower() == "*" or a_s.lower() == b_s:
                        return f"{a}/{a_s}"

    def process_resource(self, req, resp, resource, params):
        accepts = [a.split(";")[0].split('/') for a in req.accept.split(',')]
        accepts = self._match(accepts)
        if accepts is None:
            raise falcon.HTTPNotAcceptable("Unsupported content type(s)")
        resp.content_type = accepts

        if req.content_type is None:
            return
        content_type = self._match([req.content_type.split(';')[0].split('/')])
        if content_type is None:
            raise falcon.HTTPUnsupportedMediaType("Unsupported body type")
