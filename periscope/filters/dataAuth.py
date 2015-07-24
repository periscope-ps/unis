"""
AA service based on ABAC - Using certs to provide record level authorization in db
"""
import socket
import ssl
import os
import time
import tornado.web
from netlogger import nllog
import periscope.settings
import dateutil.parser

import ABAC
import periscope.settings as settings
from periscope.settings import DB_AUTH
from periscope.pp_interface import PP_Error
from periscope.pp_interface import PP_INTERFACE as PPI

AttributeList = DB_AUTH['attrib_list']
#time = 24 * 3600 * 365 * 20

class AbacError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class DataAuth(PPI):
    pp_type = PPI.PP_TYPES[PPI.PP_AUTH]
    
    def pre_get(self,obj, app=None, req=None):
        return obj
    def pre_post(self,obj, app=None, req=None):
        return obj
    
    def post_get(self,obj, app=None, req=None):
        return obj
    
    def post_post(self,obj, app=None, req=None):
        return obj
    
    def process_query(self,obj, app=None, req=None):
        cert = None
        attList = self.getAllowedAttributes(cert)
        if req != None:
            """ Get something from request - Probably a secure token and use it to get its attributes """
            return self.add_secfilter_toquery()
        else:
            return {}

    def __init__(self, server_cert = settings.SSL_OPTIONS['certfile'],
                 server_key = settings.SSL_OPTIONS['keyfile'],
                 store = settings.AUTH_STORE_DIR, db_layer=None):
        # do a few sanity checks
        assert os.path.isfile(server_cert)
        assert os.path.isdir(store)
        # the DB interface for auth info"
        self.auth_mem = []
        
        # a few constants
        self.ABAC_STORE_DIR = store
        
        # setup the ABAC context
        self.ctx = ABAC.Context()
        self.server_id = ABAC.ID(server_cert)
        self.server_id.load_privkey(server_key)
        self.ctx.load_id_file(server_cert)

        # Load local attribute and principal store (*_attr.der and *_ID.der).
        # If storing this on mongo, you will still need to write them to tmp
        # files to use the libabac routines (as far as I can tell).
        self.ctx.load_directory(self.ABAC_STORE_DIR)
        
        #out = self.ctx.credentials()
        #for x in out:
            #print "credential: %s <- %s" % (x.head().string(), x.tail().string())
            #print "issuer: \n%s" % x.issuer_cert()
            
            
    def getAllowedAttributes(self,cert):
        """ Get all allowed attributes for the cert """
        #cert = ABAC.ID_chunk(str(cert))
        attrList = []
        for i in AttributeList:
            ok,query = self.query_attr(cert,i)
            if ok:
                attrList.append(i)
                
        return attrList
        
    def query_attr(self, cert, attr,cert_format=None):
        cert2 = str(cert)
        try:
            if cert_format == "DER":                
                cert2 = ssl.DER_cert_to_PEM_cert(cert2)
            # Expects a PEM format cert always
            user = ABAC.ID_chunk(cert2)
        except Exception, e:
            raise AbacError("Could not load user ccccert: %s" % e)
    
        #out = self.ctx.credentials()
        #for x in out:
        #    print "%s <- %s" % (x.head().string(), x.tail().string())
        role_str = self.server_id.keyid() + "." + str(attr)
        (success, credentials) = self.ctx.query(role_str, user.keyid())

        #print ">>>>", success
        #for c in credentials:
        #    print "%s <- %s" % (c.head().string(), c.tail().string())

        return success,credentials
    
    def add_secfilter_toquery(self,attList=None):
        if attList == None:
            """Select a default filter token"""
            return { str(AuthField) : AuthDefault }
        else:
            """ Get a list of attributes for this certificate """
            return { str(AuthField) : { "$in" : attList }}

# The authentication module
class UserCredHandler(tornado.web.RequestHandler, nllog.DoesLogging):
    cookie_name = "SECURE_TOKEN"
    def get(self):
        if not self.get_cookie(self.cookie_name):
            self.set_cookie(self.cookie_name,"")
            
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
