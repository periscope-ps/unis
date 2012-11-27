import tornado.web
from netlogger import nllog
from pp_interface import PP_INTERFACE as PPI

import settings
from settings import MIME
from settings import SCHEMAS

class Gemini(PPI):

    def pre_get(self, obj, app=None, req=None):
        return []

    def post_get(self, obj, app=None, req=None):
        return obj

    def process_query(self, obj, app=None, req=None):
        auth = app._auth
        cert = req.get_ssl_certificate(binary_form=True)
        
        for a in auth.auth_mem:
            print a

        new_obj = {'properties.geni.slice_uuid': {'$exists': True}}
        obj.append(new_obj)

        print obj
        return obj


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
