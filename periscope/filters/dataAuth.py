# =============================================================================
#  periscope-ps (unis)
#
#  Copyright (c) 2012-2016, Trustees of Indiana University,
#  All rights reserved.
#
#  This software may be modified and distributed under the terms of the BSD
#  license.  See the COPYING file for details.
#
#  This software was created at the Indiana University Center for Research in
#  Extreme Scale Technologies (CREST).
# =============================================================================
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
        cert = Handler.get_argument("cert",None)
        self.log.info("Trying to log in using cert ")
        if cert:
            attList = self.getAllowedAttributes(cert)
            attListStr = ",".join(attList)
            self.log.info("Logging in with attList "+ attListStr)
            req.arguments[argName] = attListStr
            Handler.set_secure_cookie(cookie_name,attListStr)
            return obj
        else:
            """ Do Nothing """
            return obj
    
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
        nllog.DoesLogging.__init__(self)
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
        self.log.info("Initializing data Auth Filter for record level authorization")
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
            return [{ str(AuthField) : AuthDefault }]
        else:
            """ Get a list of attributes for this certificate """
            return [{ str(AuthField) : { "$in" : str(attList).split(",") }}]

from periscope.handlers import SSEHandler
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
        attlist = self.request.arguments[argName]
        if attlist == None:
            self.write({ "loggedIn": False})
        else:
            self.write({ "loggedIn": True})
