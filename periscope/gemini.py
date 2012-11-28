import uuid
import tornado.web
from netlogger import nllog

import settings
from settings import MIME
from settings import SCHEMAS
from periscope.pp_interface import PP_Error
from periscope.pp_interface import PP_INTERFACE as PPI

class Gemini(PPI):

    def pre_get(self, obj, app=None, req=None):
        return obj

    def post_get(self, obj, app=None, req=None):
        return obj

    def pre_post(self, obj, app=None, req=None):
        # (EK) HACK: check and allow requests from the server itself
        # make this more secure by checking key hash
        cert = req.get_ssl_certificate(binary_form=False)
        for item in cert['subject']:
            for (key,value) in item:
                if key == "commonName" and value == "server":
                    return obj

        uuids = self.__get_allowed_uuids(app, req)
        if not len(uuids):
            raise PP_Error("GEMINI: no registered slices for user")

        if not isinstance(obj, list):
            t_obj = [obj]
        else:
            t_obj = obj

        for o in t_obj:
            try:
                o['properties']['geni']['slice_uuid']
            except Exception:
                raise PP_Error("GEMINI: no slice_uuid in one or more network objects")
            if o['properties']['geni']['slice_uuid'] not in uuids:
                raise PP_Error("GEMINI: one or more network objects is not allowed for user")

        return obj

    def post_post(self, obj, app=None, req=None):
        return obj

    def process_query(self, obj, app=None, req=None):
        uuids = self.__get_allowed_uuids(app, req)
        if not len(uuids):
            raise PP_Error("GEMINI: no registered slices for user")

        new_q = []
        for u in uuids:
            new_q.append({'properties.geni.slice_uuid': u})
        # return non-GENI slice stuff as well (well, objects without UUID anyway)
        #new_q.append({'properties.geni.slice_uuid': {'$exists': False}}
        new_q = {"$or": new_q}
        obj.append(new_q)
        return obj

    def __get_allowed_uuids(self, app, req):
        auth = app._auth
        cert = req.get_ssl_certificate(binary_form=True)

        uuids = []
        for a in auth.auth_mem:
            if auth.query(cert, a['_id']) is True:
                uuids.append(str(uuid.UUID(a['_id'])))

        return uuids


class AuthCredHandler(tornado.web.RequestHandler, nllog.DoesLogging):

    def write_error(self, status_code, **kwargs):
        if self.settings.get("debug") and "exc_info" in kwargs:
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            content_type =  MIME['PSJSON']
            self.set_header("Content-Type", content_type)
            result = "{"
            for key in kwargs:
                result += '"%s": "%s",' % (key, kwargs[key])
            result = result.rstrip(",") + "}\n"
            self.write(result)
            self.finish()

    def post(self, res_id=None):
        # add checks
        cert = self.request.get_ssl_certificate(binary_form=True)
        
        auth = self.application._auth
        auth.add_credential(cert, self.request.body)
    

class AuthRegisterSliceHandler(tornado.web.RequestHandler, nllog.DoesLogging):

    def write_error(self, status_code, **kwargs):
        if self.settings.get("debug") and "exc_info" in kwargs:
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            content_type =  MIME['PSJSON']
            self.set_header("Content-Type", content_type)
            result = "{"
            for key in kwargs:
                result += '"%s": "%s",' % (key, kwargs[key])
            result = result.rstrip(",") + "}\n"
            self.write(result)
            self.finish()

    def post(self, res_id=None):
        # add checks
        if self.request.body:
            auth = self.application._auth
            try:
                cert = self.request.get_ssl_certificate(binary_form=True)
                auth.bootstrap_slice_credential(cert, self.request.body)
            except Exception, msg:
                self.send_error(400, message=msg)
                return
        else:
            self.send_error(400, message="Message body is empty!")
            return
