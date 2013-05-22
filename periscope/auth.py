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
from M2Crypto import X509
from datetime import datetime

import ABAC
from sfa.trust.credential import Credential as GENICredential

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
        self.ctx.load_directory(self.ABAC_STORE_DIR)
        
        #out = self.ctx.credentials()
        #for x in out:
            #print "credential: %s <- %s" % (x.head().string(), x.tail().string())
            #print "issuer: \n%s" % x.issuer_cert()

    def bootstrap_slice_credential(self, cert, geni_slice_cred):
        # given the slice credential we can create the principal if it doesn't 
        # exist already, and then add the necessary admin permissions for that
        # slice uuid/urn or domain.
        cred = GENICredential(string=geni_slice_cred)
        
        # now load the cert from the client SSL context)
        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
            self.ctx.load_id_chunk(cert)
        except Exception, e:
            raise AbacError("Could not read user cert: %s" % e)

        # make sure the requesting cert matches the credential owner
        try:
            req_cert = cred.get_gid_caller().save_to_string()
            #(cert,sep,rest) = req_cert.partition("-----END CERTIFICATE-----")
            req_id = ABAC.ID_chunk(req_cert)
        except Exception, e:
            raise AbacError("Could not read user cert: %s" % e)

        if (req_id.keyid() != user.keyid()):
            raise AbacError("Client cert does not match credential owner!")
        
        # Validity could be something else, here we're taking the slice certificate's
        # expiration date (not the credential's). Since the exp date and the role is
        # tied to the UUID of the slice (and not the URN which is reusable), it shouldn't
        # matter if this is longer than the lifetime of the slice.
        expiration = cred.get_expiration()
        now = datetime.now(expiration.tzinfo)
        td = expiration - now
        validity = int(td.seconds + td.days * 24 * 3600)

        if (validity <= 0):
            raise AbacError("Slice credential has expired")

        # This assumes the credential is valid (you can call cred.verify
        # with the CA roots, i.e. genica.bundle, to do it yourself).
        slice_uuid = cred.get_gid_object().get_uuid()
        slice_urn = cred.get_gid_object().get_urn()
        owner_urn = cred.get_gid_caller().get_urn()
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
        cert_filename = user.keyid() + self.PRIN_FILE_SUFFIX
        user.write_cert_file(os.path.join(self.ABAC_STORE_DIR, cert_filename))

        # create the initial role (UNIS.rUA <- client)
        UA_role = self.USER_ADMIN_ROLE_PREFIX + slice_uuid
        attr = ABAC.Attribute(self.server_id, UA_role, validity)
        attr.principal(user.keyid())
        attr.bake()
        self.ctx.load_attribute_chunk(attr.cert_chunk())
        
        # save
        attr_filename = UA_role + self.ATTR_FILE_SUFFIX
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


    def add_credential(self, cert, cred):
        # Users can post credentials, usually delegating a given
        # permission to a second principal.

        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)

        try:
            tmpctx = ABAC.Context()
            tmpctx.load_id_chunk(cert)
            tmpctx.load_attribute_chunk(cred)            
            creds = tmpctx.credentials()

            if not len(creds):
                raise AbacError("Error loading credential with given client cert")
            
            #cred_issuer = ABAC.ID_chunk(creds[0].issuer_cert())
            #if user.keyid() != cred_issuer.keyid():
            #    raise AbacError("Client cert does not match credential issuer!")
            
            self.ctx.load_id_chunk(cert)
            self.ctx.load_attribute_chunk(cred)            

            # save new attribute and identity to file
            user.write_cert_file(os.path.join(self.ABAC_STORE_DIR, user.keyid() + self.PRIN_FILE_SUFFIX))
            attr_filename = user.keyid() + "_has_" + creds[0].head().role_name() + self.ATTR_FILE_SUFFIX
            f = open(os.path.join(self.ABAC_STORE_DIR, attr_filename), 'w')
            f.write(cred)
            f.close()            
        except Exception, e:
            raise AbacError("Could not load attribute cert: %s" % e)


    def query(self, cert, slice_uuid, req=None):
        try:
            cert = ssl.DER_cert_to_PEM_cert(cert)
            user = ABAC.ID_chunk(cert)
        except Exception, e:
            raise AbacError("Could not load user cert: %s" % e)
        
        #out = self.ctx.credentials()
        #for x in out:
        #    print "%s <- %s" % (x.head().string(), x.tail().string())

        role_str = self.server_id.keyid() + "." + str(self.SLICE_ADMIN_ROLE_PREFIX + slice_uuid)
        (success, credentials) = self.ctx.query(role_str, user.keyid())

        #print ">>>>", success
        #for c in credentials:
        #    print "%s <- %s" % (c.head().string(), c.tail().string())

        return success
