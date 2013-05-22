import uuid
from M2Crypto import X509
import tornado.web
import traceback
import time
from netlogger import nllog

import settings
from settings import MIME
from settings import SCHEMAS
from periscope.pp_interface import PP_Error
from periscope.pp_interface import PP_INTERFACE as PPI

class Gemini(PPI):

    pp_type = PPI.PP_TYPES[PPI.PP_AUTH]

    def pre_get(self, obj, app=None, req=None):
        return obj

    def post_get(self, obj, app=None, req=None):
        return obj

    def pre_post(self, obj, app=None, req=None):
        if self.__is_server(req):
            return obj

        uuid = None
        uuids = self.__get_allowed_uuids(app, req)

        ## allow any "authenticated" user
        #if not len(uuids):
        #    raise PP_Error("GEMINI: no registered slices for user")

        if not isinstance(obj, list):
            t_obj = [obj]
        else:
            t_obj = obj

        for o in t_obj:
            try:
                uuid = self.__get_uuid(o)
            except Exception:
                raise
            if uuid is None:
                pass
            elif uuid not in uuids:
                raise PP_Error("GEMINI: one or more network objects is not allowed for user")

        return obj

    def post_post(self, obj, app=None, req=None):
        return obj

    def process_query(self, obj, app=None, req=None):
        if self.__is_server(req):
            return obj

        # some exceptions, data and events need to be secured differently
        if req.uri.split('/')[1] in ['events', 'data']:
            return obj

        uuids = self.__get_allowed_uuids(app, req)

        ## allow any "authenticated" user
        #if not len(uuids):
        #    raise PP_Error("GEMINI: no registered slices for user")

        if len(uuids):
            new_q = []
            for u in uuids:
                new_q.append({'properties.geni.slice_uuid': u})
                new_q.append({'parameters.geni.slice_uuid': u})
                new_q.append({'properties.geni.slice_uuid': {'$exists': False},
                              'parameters.geni.slice_uuid': {'$exists': False}})
            obj.append({"$or": new_q})
        else:
            # return non-GENI UUID marked objects
            obj.append({'properties.geni.slice_uuid': {'$exists': False},
                        'parameters.geni.slice_uuid': {'$exists': False}})

        return obj

    def __is_server(self, req):
        cert = req.get_ssl_certificate(binary_form=True)
        x509 = X509.load_cert_string(cert, X509.FORMAT_DER)
        if x509.get_fingerprint('sha1') == settings.SERVER_CERT_FINGERPRINT:
            return True
        else:
            return False

    def __get_uuid(self, obj):
        try:
            return obj['properties']['geni']['slice_uuid']
        except:
            pass

        try:
            return obj['parameters']['geni']['slice_uuid']
        except:
            pass

        # Allow objects with no UUIDs
        #raise PP_Error("GEMINI: no slice_uuid in one or more network objects")
        return None

    def __get_allowed_uuids(self, app, req):
        auth = app._auth
        cert = req.get_ssl_certificate(binary_form=True)
        now = int(time.time() * 1000000)

        uuids = []
        for a in auth.auth_mem:
            if int(a['valid_until']) <= int(now):
                auth.auth_mem.remove(a)
            if auth.query(cert, a['_id']) is True:
                uuids.append(str(uuid.UUID(a['_id'])))

        return uuids


class AuthUserCredHandler(tornado.web.RequestHandler, nllog.DoesLogging):

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
        if self.request.body:
            auth = self.application._auth
            try:
                cert = self.request.get_ssl_certificate(binary_form=True)
                auth.add_credential(cert, self.request.body)
            except Exception, msg:
                self.send_error(400, message=msg)
                return
        else:
            self.send_error(400, message="Message body is empty!")
    

class AuthSliceCredHandler(tornado.web.RequestHandler, nllog.DoesLogging):

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
