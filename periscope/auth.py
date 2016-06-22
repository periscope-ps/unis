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
Authentication service based on ABAC
"""
import socket
import ssl
import os
import shutil
import time
import uuid
import hashlib
import settings
import dateutil.parser
from lxml import etree
from M2Crypto import X509
from datetime import datetime

import ABAC
from sfa.trust.gid import GID
from sfa.trust.credential import Credential as GENICredential
from sfa.trust.abac_credential import ABACCredential
from settings import DB_AUTH

AttributeList = DB_AUTH['attrib_list']
#time = 24 * 3600 * 365 * 20

class AbacError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class ABACAuthService:
    
    def __init__(self, server_cert, server_key, store, db_layer=None):
        # do a few sanity checks
        assert os.path.isfile(server_cert)
        assert os.path.isdir(store)
        # the DB interface for auth info"
        self.db = db_layer
        self.auth_mem = []

        if self.db is not None:
            res = self.db.find()
            for r in res:
                self.auth_mem.append(r)
                # clear out old slices...

        # a few constants
        self.ABAC_STORE_DIR = store
        self.ATTR_FILE_SUFFIX = "_attr.xml"
        self.PRIN_FILE_SUFFIX = "_ID.pem"

        # hardcode some basic roles for now
        self.SLICE_ADMIN_ROLE_PREFIX = "slice_admin_for_"
        self.USER_ADMIN_ROLE_PREFIX = "admin_user_for_"
        self.ADMIN_ARE_SLICE_ADMINS = "ua_are_sa_for_"

        # setup the ABAC context
        self.ctx = ABAC.Context()
        self.server_id = ABAC.ID(server_cert)
        self.server_id.load_privkey(server_key)
        self.ctx.load_id_file(server_cert)

        # Load local attribute and principal store (*_attr.der and *_ID.der).
        # If storing this on mongo, you will still need to write them to tmp
        # files to use the libabac routines (as far as I can tell).
        self.ctx.load_directory(settings.AUTH_STORE_DIR)
        
        #out = self.ctx.credentials()
        #for x in out:
            #print "credential: %s <- %s" % (x.head().string(), x.tail().string())
            #print "issuer: \n%s" % x.issuer_cert()

    def handle_sf_cred(self, user, xml_cred):
        try:
            # XX: libabac segfaults on the GENI abac creds for some reason
            # XX: will use ABACCredential instead
            #tmpctx = ABAC.Context()
            #tmpctx.load_id_chunk(user.cert_chunk())
            #ret = tmpctx.load_attribute_chunk(xml_cred)
            #if ret < 0:
            #    raise AbacError("Could not read the speaks-for cert given client cert")

            sf_cred = ABACCredential(string=xml_cred)
            # also can't verify abac creds...sigh
            #sf_cred.verify(trusted_certs=[settings.SSL_OPTIONS['ca_certs']])
            #print sf_cred.dump_string()

            sf_cert = sf_cred.get_signature().get_issuer_gid().save_to_string()
            sf_user = ABAC.ID_chunk(sf_cert)
            sf_req = sf_cred.get_tails()[0]
        except Exception, e:
            raise AbacError("Could not read the speaks-for cert: %s" % e)
        
        if (str(sf_req) != str(user.keyid())):
            raise AbacError("Client cert does not match speaks-for credential user!")
        
        return sf_user

    def bootstrap_slice_credential(self, cert, xml_creds):
        slice_cred = None
        sf_cred = None
        puser = None

        root = etree.XML(xml_creds)
        if root.tag == "unis-credentials":        
            test = root.find("slice-credential")
            if test is not None:
                slice_cred = etree.tostring(test.find("signed-credential"), xml_declaration=True, encoding="UTF-8")
            else:
                raise AbacError("Could not find slice credential")
            test = root.find("sf-credential")
            if test is not None:
                sf_cred = etree.tostring(test.find("signed-credential"), xml_declaration=True, encoding="UTF-8")
            else:
                raise AbacError("Could not find speaks-for credential")
        else:
            slice_cred = xml_creds

        try:
            slice_cred = GENICredential(string=slice_cred)
            # can't just give it a bundle, need to split out each cert into its own file, argh!
            #slice_cred.verify(trusted_certs=[settings.SSL_OPTIONS['ca_certs']])
        except Exception, e:
            raise AbacError("Could not verify slice credential: %s" % e)

        # now load the cert from the client SSL context)
        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not read user cert: %s" % e)

        # make sure the requesting cert matches the credential owner
        try:
            req_cert = slice_cred.get_gid_caller().save_to_string()
            req_id = ABAC.ID_chunk(req_cert)
        except Exception, e:
            raise AbacError("Could not read user cert: %s" % e)

        if (sf_cred):
            puser = self.handle_sf_cred(user, sf_cred)
            if (puser.keyid() != req_id.keyid()):
                raise AbacError("Credential owner does not match user we're speaking for!")
        else:
            if (req_id.keyid() != user.keyid()):
                raise AbacError("Client cert does not match credential owner!")
            puser = user

        # Validity could be something else, here we're taking the slice certificate's
        # expiration date (not the credential's). Since the exp date and the role is
        # tied to the UUID of the slice (and not the URN which is reusable), it shouldn't
        # matter if this is longer than the lifetime of the slice.
        expiration = slice_cred.get_expiration()
        now = datetime.now(expiration.tzinfo)
        td = expiration - now
        validity = int(td.seconds + td.days * 24 * 3600)
        if (validity <= 0):
            raise AbacError("Slice credential has expired")

        # We have reached a point where we can safely load identities
        # The abac context shouldn't need the client cert if a S-F cred is presented
        self.ctx.load_id_chunk(puser.cert_chunk())
        
        # This assumes the credential is valid (you can call cred.verify
        # with the CA roots, i.e. genica.bundle, to do it yourself).
        slice_uuid = slice_cred.get_gid_object().get_uuid()
        slice_urn = slice_cred.get_gid_object().get_urn()
        owner_urn = slice_cred.get_gid_caller().get_urn()
        if not slice_uuid:
            slice_uuid = hashlib.md5(slice_urn).hexdigest()
            slice_uuid = uuid.UUID(slice_uuid).hex
        else:
            slice_uuid = uuid.UUID(int=slice_uuid).hex

        timestamp = int(time.time() * 1000000)
        uuid_query = {"_id": slice_uuid}
        res = self.db.find(uuid_query)
        if res.count() == 0:
            uuid_query = {"_id": slice_uuid,
                          "target_urn": slice_urn,
                          "owner_urn": owner_urn,
                          "owner_keyid": user.keyid(),
                          "ts": str(timestamp),
                          "valid_until": str(timestamp+(validity*1000000))
                          }
            self.db.insert(uuid_query)
            self.auth_mem.append(uuid_query)
        else:
            # slice already registered
            pass

        # save the user cert from credential to keystore
        cert_filename = puser.keyid() + self.PRIN_FILE_SUFFIX
        puser.write_cert_file(os.path.join(self.ABAC_STORE_DIR, cert_filename))

        # create the initial role (UNIS.rUA <- client)
        UA_role = self.USER_ADMIN_ROLE_PREFIX + slice_uuid
        attr = ABAC.Attribute(self.server_id, UA_role, validity)
        attr.principal(puser.keyid())
        attr.bake()
        self.ctx.load_attribute_chunk(attr.cert_chunk())

        # save
        attr_filename = UA_role + "_" + puser.keyid() + self.ATTR_FILE_SUFFIX
        attr.write_file(os.path.join(self.ABAC_STORE_DIR, attr_filename))
        
        # create linked role (UNIS.rSA <- UNIS.rUA.rSA)
        SA_role = self.SLICE_ADMIN_ROLE_PREFIX + slice_uuid
        attr = ABAC.Attribute(self.server_id, SA_role, validity)
        #attr.principal(self.server_id.keyid())
        attr.linking_role(self.server_id.keyid(), UA_role, SA_role)
        attr.bake()
        self.ctx.load_attribute_chunk(attr.cert_chunk())

        # save
        attr_filename = SA_role + self.ATTR_FILE_SUFFIX
        attr.write_file(os.path.join(self.ABAC_STORE_DIR, attr_filename))

        # all users are slice admins (UNIS.rSA <- UNIS.rUA)
        attr = ABAC.Attribute(self.server_id, SA_role, validity)
        #attr.principal(self.server_id.keyid())
        attr.role(self.server_id.keyid(), UA_role)
        attr.bake()
        self.ctx.load_attribute_chunk(attr.cert_chunk())
        
        # save
        attr_filename = self.ADMIN_ARE_SLICE_ADMINS + slice_uuid + self.ATTR_FILE_SUFFIX
        attr.write_file(os.path.join(self.ABAC_STORE_DIR, attr_filename))
        
        return
    
    def getAllowedAttributes(self,cert):
        """ Get all allowed attributes for the cert """
        #cert = ABAC.ID_chunk(str(cert))
        attrList = []
        for i in AttributeList:
            ok,query = self.query_attr(cert,i)
            if ok:
                attrList.append(i)
                
        return attrList
        
    def add_credential(self, cert, body):
        # Users can post credentials, usually delegating a given
        # permission to a second principal.
        cred = None
        sf_cred = None
        pcert = None
        role = None

        root = etree.XML(body)
        if root.tag == "unis-credentials":        
            test = root.find("role")
            if test is not None:
                role = test.text
            else:
                raise AbacError("Could not find role element")
            test = root.find("subject-cert")
            if test is not None:
                pcert = test.text
            else:
                raise AbacError("Could not find subject certificate (i.e., proxy cert)")
            test = root.find("sf-credential")
            if test is not None:
                sf_cred = etree.tostring(test.find("signed-credential"), xml_declaration=True, encoding="UTF-8")
            else:
                raise AbacError("Could not find speaks-for credential")
        else:
            cred = body
        
        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)

        if role and pcert and sf_cred:
            # check that role is one we want to add to our abac store
            if not role.startswith(self.SLICE_ADMIN_ROLE_PREFIX):
                raise AbacError("Requested role '%s' is not allowed" % role)

            suser = self.handle_sf_cred(user, sf_cred)
            # make sure who we're speaking for can actually access
            # the slice we're adding a role for
            slice_uuid = role.replace(self.SLICE_ADMIN_ROLE_PREFIX, "")
            ret = self.query_role(suser.cert_chunk(), slice_uuid, cert_format="PEM")
            if not ret:
                raise AbacError("Speaks-for user does not have access to requested slice")

            try:
                puser = ABAC.ID_chunk(pcert)
            except Exception, e:
                raise AbacError("Could not load proxy cert identity: %s" % e)
            
            co = GID(string=pcert)
            expiration = dateutil.parser.parse(co.cert.get_notAfter())
            now = datetime.now(expiration.tzinfo)
            td = expiration - now
            validity = int(td.seconds + td.days * 24 * 3600)
            if (validity <= 0):
                raise AbacError("Proxy cert has expired")

            attr = ABAC.Attribute(self.server_id, role, validity)
            attr.principal(puser.keyid())
            attr.bake()
            self.ctx.load_attribute_chunk(attr.cert_chunk())
            
            # save
            attr_filename = role + "_" + puser.keyid() + self.ATTR_FILE_SUFFIX
            attr.write_file(os.path.join(self.ABAC_STORE_DIR, attr_filename))
        elif cred:
            try:
                tmpctx = ABAC.Context()
                tmpctx.load_id_chunk(cert)
                ret = tmpctx.load_attribute_chunk(cred)          
                creds = tmpctx.credentials()
                if not len(creds):
                    raise AbacError("Error loading credential with given client cert")
            
                self.ctx.load_id_chunk(cert)
                self.ctx.load_attribute_chunk(cred)

                # save new attribute and identity to file
                user.write_cert_file(os.path.join(self.ABAC_STORE_DIR, user.keyid() + self.PRIN_FILE_SUFFIX))
                attr_filename = creds[0].head().role_name() + "_" + user.keyid() + self.ATTR_FILE_SUFFIX
                f = open(os.path.join(self.ABAC_STORE_DIR, attr_filename), 'w')
                f.write(cred)
                f.close()            
            except Exception, e:
                raise AbacError("Could not load attribute cert: %s" % e)
        else:
            raise AbacError("Unrecognized request")

    def query_attr(self, cert, attr,cert_format=None):
        cert2 = str(cert)
        try:
            if cert_format == "DER":                
                cert2 = ssl.DER_cert_to_PEM_cert(cert2)
            # Expects a PEM format cert always
            user = ABAC.ID_chunk(cert2)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)
    
        #out = self.ctx.credentials()
        #for x in out:
        #    print "%s <- %s" % (x.head().string(), x.tail().string())
        role_str = self.server_id.keyid() + "." + str(attr)
        (success, credentials) = self.ctx.query(role_str, user.keyid())

        #print ">>>>", success
        #for c in credentials:
        #    print "%s <- %s" % (c.head().string(), c.tail().string())

        return success,credentials
    ## Query attribute
    def query_role(self, cert, slice_uuid, req=None, cert_format="DER",attr = None):
        if attr == None:
            attr = self.SLICE_ADMIN_ROLE_PREFIX + slice_uuid
        try:
            if cert_format == "DER":                
                cert = ssl.DER_cert_to_PEM_cert(cert)
            # Expects a PEM format cert always
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)

        #out = self.ctx.credentials()
        #for x in out:
        #    print "%s <- %s" % (x.head().string(), x.tail().string())
        role_str = self.server_id.keyid() + "." + str(attr)
        (success, credentials) = self.ctx.query(role_str, user.keyid())

        #print ">>>>", success
        #for c in credentials:
        #    print "%s <- %s" % (c.head().string(), c.tail().string())

        return success
    
    def query(self, cert):
        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)

        now = int(time.time() * 1000000)
        uuids = []

        for a in self.auth_mem[:]:
            if int(a['valid_until']) <= int(now):
                self.auth_mem.remove(a)
                continue
            role_str = self.server_id.keyid() + "." + str(self.SLICE_ADMIN_ROLE_PREFIX + a['_id'])
            (success, credentials) = self.ctx.query(role_str, user.keyid())
            if success:
                uuids.append(str(uuid.UUID(a['_id'])))

        return uuids
