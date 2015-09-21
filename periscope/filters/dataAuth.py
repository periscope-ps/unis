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
AuthDefault = DB_AUTH['auth_default']
AuthField = DB_AUTH['auth_field']
cookie_name = "attlist"
argName = AuthField
#time = 24 * 3600 * 365 * 20

class AbacError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)
    
class DataAuth(PPI, nllog.DoesLogging):
    pp_type = PPI.PP_TYPES[PPI.PP_AUTH]
    def pre_get(self,obj, app=None, req=None,Handler=None):
        self.log.info("Doing Pre get to get the attList ")
        # attlist = Handler.get_secure_cookie(cookie_name)
        # req.arguments[argName] = None      
        return obj
    
    def pre_post(self,obj, app=None, req=None,Handler=None):
        """ If cert is provided - then login """
        try:            
            pkey = Handler.get_argument("userPublicKey",None)
            cert = Handler.get_argument("userCert",None)
            if cert and pkey:
                self.log.info("Logging in with attList ")
                attList = self.getAllowedAttributes(pkey,cert)
                attListStr = ",".join(attList)
                self.log.info("Logging in with attList "+ attListStr)
                req.arguments[argName] = attListStr
                # Handler.set_secure_cookie(cookie_name,attListStr)
                return obj
            else:
                """ Do Nothing """
                return obj
        except Exception,msg:
            self.log.info("Error in pre-post"+ str(msg))
    
    def post_get(self,obj, app=None, req=None):        
        return obj
    
    def post_post(self,obj, app=None, req=None):
        return obj
    
    def process_query(self,obj, app=None, req=None,Handler=None):
        # cert = open(settings.SSL_OPTIONS['certfile']).read()
        attList = Handler.get_secure_cookie(cookie_name)        
        self.log.info("Attlist is "+ str(attList))
        return self.add_secfilter_toquery(attList)
    
    def __init__(self, server_cert = settings.SSL_OPTIONS['certfile'],
                 server_key = settings.SSL_OPTIONS['keyfile'],
                 store = settings.AUTH_STORE_DIR, db_layer=None):
        # do a few sanity checks
        assert os.path.isfile(server_cert)
        assert os.path.isdir(store)
        server_cert = "/opt/cred/unis_ID.pem"
        server_key = "/opt/cred/unis_private.pem"
        nllog.DoesLogging.__init__(self)
        # the DB interface for auth info"
        self.auth_mem = []
        
        # a few constants
        self.ABAC_STORE_DIR = "/opt/cred"
        
        # setup the ABAC context
        self.ctx = ABAC.Context()
        self.server_id = ABAC.ID(server_cert)
        self.server_id.load_privkey(server_key)
        self.ctx.load_id_file(server_cert)

        # Load local attribute and principal store (*_attr.der and *_ID.der).
        # If storing this on mongo, you will still need to write them to tmp
        # files to use the libabac routines (as far as I can tell).
        self.ctx.load_directory(self.ABAC_STORE_DIR)
        self.log.info("Initializing data Auth Filter for record level authorization")
        #out = self.ctx.credentials()
        #for x in out:
            #print "credential: %s <- %s" % (x.head().string(), x.tail().string())
            #print "issuer: \n%s" % x.issuer_cert()
            
            
    def getAllowedAttributes(self,pkey,cert):
        """ Get all allowed attributes for the cert """
        #cert = ABAC.ID_chunk(str(cert))
        try:
            context = ABAC.Context()
            context.load_directory(self.ABAC_STORE_DIR)
            context.load_attribute_chunk(str(cert))
            user = ABAC.ID_chunk(str(pkey))
            self.log.info("User ID "+user.keyid())
            attrList = []
            for i in AttributeList:
                role_str = self.server_id.keyid() + "." + str(i)
                ok,query = context.query(role_str, user.keyid())
                if ok:
                    attrList.append(i)
                else:
                    self.log.info("Query for "+i+ " failed")
            return attrList
        except Exception,msg:
            self.log.info("Error in getAllowed attributes"+ str(msg))
            return []

    def add_secfilter_toquery(self,attList=None):
        if attList == None:
            """Select a default filter token"""
            return [{ str(AuthField) : AuthDefault }]
        else:
            """ Get a list of attributes for this certificate """
            return [{ "$or" : [{str(AuthField) : { "$in" : str(attList).split(",") }}, {str(AuthField) : AuthDefault}]}]

from periscope.handlers.ssehandler import SSEHandler
# The authentication module
class UserCredHandler(SSEHandler, nllog.DoesLogging):
    def get (self,res_id= None,*args):
        super(UserCredHandler,self).get(*args)
        """Just send the login status """
        attlist = self.get_secure_cookie(cookie_name)
        if attlist == None:
            self.write({ "loggedIn": False})
        else:
            self.write({ "loggedIn": True})
            
    def post(self, res_id=None,*args):
        if getattr(self.application, '_ppi_classes', None):
            try:
                for pp in self.application._ppi_classes:
                    pp.pre_post(None, self.application, self.request,Handler=self)
            except Exception, msg:                
                self.send_error(400, message=msg)
                return
                
        """ Just send the login status """
        if self.request.arguments.has_key(argName):
            attlist = self.request.arguments[argName]
            self.set_secure_cookie(cookie_name,str(attlist))
            self.write({ "loggedIn": True, "attlist" : str(attlist)})
        else:
            self.write({ "loggedIn": False})
