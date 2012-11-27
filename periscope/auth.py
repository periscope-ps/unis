"""
Authentication service based on ABAC
"""
import socket
import ssl
import os
import shutil
import time
import uuid
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
        self.ATTR_FILE_SUFFIX = "_attr.der"
        self.PRIN_FILE_SUFFIX = "_ID.pem"

        # hardcode some basic roles for now
        self.SLICE_ADMIN_ROLE_PREFIX = "slice_admin_for_"
        self.USER_ADMIN_ROLE_PREFIX = "admin_user_for_"
        self.ADMIN_ARE_SLICE_ADMINS = "ua_are_sa_for_"

        # setup the ABAC context
        self.ctx = ABAC.Context()
        self.server_id = ABAC.ID(server_cert)
        self.server_id.id_load_privkey_file(server_key)            
        self.ctx.load_id(self.server_id)

        # Load local attribute and principal store (*_attr.der and *_ID.der).
        # If storing this on mongo, you will still need to write them to tmp
        # files to use the libabac routines (as far as I can tell).
        self.ctx.load_directory(self.ABAC_STORE_DIR)

        #out = self.ctx.context_principals()
        #for x in out[1]:
        #    print "principal: %s " % x.string()

        #out = self.ctx.context_credentials()
        #for x in out[1]:
        #print "credential: %s " % x.string()

    def bootstrap_slice_credential(self, cert, geni_slice_cred):
        # given the slice credential we can create the principal if it doesn't 
        # exist already, and then add the necessary admin permissions for that
        # slice uuid/urn or domain.
        cred = GENICredential(string=geni_slice_cred)
        
        # now load the cert from the client SSL context)
        user_id = ABAC.ID_chunk(cert)
        self.ctx.load_id(user_id)

        # make sure the requesting cert matches the credential owner
        der_cert = ssl.PEM_cert_to_DER_cert(cred.get_gid_caller().save_to_string())
        req_id = ABAC.ID_chunk(der_cert)

        if (req_id.id_keyid() != user_id.id_keyid()):
            raise AbacError("Client cert does not match credential owner!")
        
        # Validity could be something else, here we're taking the slice certificate's
        # expiration date (not the credential's). Since the exp date and the role is
        # tied to the UUID of the slice (and not the URN which is reusable), it shouldn't
        # matter if this is longer than the lifetime of the slice.
        expiration = cred.get_expiration()
        now = datetime.now(expiration.tzinfo)
        validity = int((expiration - now).total_seconds())

        if (validity <= 0):
            raise AbacError("Slice credential has expired")

        # This assumes the credential is valid (you can call cred.verify
        # with the CA roots, i.e. genica.bundle, to do it yourself).
        slice_uuid = cred.get_gid_object().get_uuid()
        if not slice_uuid:
            slice_uuid = hashlib.md5(cred.get_gid_object().get_urn()).hexdigest()
            slice_uuid = uuid.UUID(slice_uuid).hex
        else:
            slice_uuid = uuid.UUID(int=slice_uuid).hex

        timestamp = int(time.time() * 1000000)
        uuid_query = {"_id": slice_uuid}
        res = self.db.find(uuid_query)
        if res.count() == 0:
            uuid_query = {"_id": slice_uuid,
                          "ts": str(timestamp),
                          "valid_until": str(timestamp+validity)
                          }
            self.db.insert(uuid_query)
            self.auth_mem.append(uuid_query)
        else:
            raise AbacError("Slice already registered")

        # create the initial role (UNIS.rUA <- client)
        UA_role = self.USER_ADMIN_ROLE_PREFIX + slice_uuid
        head = ABAC.Role(self.server_id.id_keyid(), UA_role)

        # save the user cert from credential to keystore
        user_uuid = cred.get_gid_caller().get_subject()
        cert_filename = user_uuid + self.PRIN_FILE_SUFFIX
        cred.get_gid_caller().save_to_file(os.path.join(self.ABAC_STORE_DIR, cert_filename))

        # now setup the attribute
        attr = ABAC.Attribute(head, validity)
        tail = ABAC.Role(user_id.id_keyid())
        attr.attribute_add_tail(tail);
        attr.attribute_bake()
        self.ctx.load_attribute(attr)

        # save
        attr_filename = UA_role + self.ATTR_FILE_SUFFIX
        attr.attribute_write_cert(os.path.join(self.ABAC_STORE_DIR, attr_filename))

        # create linked role (UNIS.rSA <- UNIS.rUA.rSA)
        SA_role = self.SLICE_ADMIN_ROLE_PREFIX + slice_uuid
        head = ABAC.Role(self.server_id.id_keyid(), SA_role)
        tail = ABAC.Role(self.server_id.id_keyid(), UA_role, SA_role)
        
        # now setup the attribute
        attr = ABAC.Attribute(head, validity)
        attr.attribute_add_tail(tail)
        attr.attribute_bake()
        self.ctx.load_attribute(attr)

        # save
        attr_filename = SA_role + self.ATTR_FILE_SUFFIX
        attr.attribute_write_cert(os.path.join(self.ABAC_STORE_DIR, attr_filename))

        # everyone who's an admin user is a slice admin
        head = ABAC.Role(self.server_id.id_keyid(), SA_role)
        tail = ABAC.Role(self.server_id.id_keyid(), UA_role)
        attr = ABAC.Attribute(head, validity)
        attr.attribute_add_tail(tail)
        attr.attribute_bake()
        self.ctx.load_attribute(attr)
        
        # save         
        attr_filename = self.ADMIN_ARE_SLICE_ADMINS + slice_uuid + self.ATTR_FILE_SUFFIX
        attr.attribute_write_cert(os.path.join(self.ABAC_STORE_DIR, attr_filename))

        #self.ctx.dump_yap_db()

    def add_credential(self, cert, cred):
        # Users can post credentials, usually delegating a given
        # permission to a second principal.

        # (EK): should do some verification before blindly accepting
        user = ABAC.ID_chunk(cert)
        self.ctx.load_id(user)
        
        attr = ABAC.Attribute_chunk(cred)
        self.ctx.load_attribute(attr)

        # save new attribute and identity to file
        user_filename = user.id_keyid() + self.PRIN_FILE_SUFFIX
        user.id_write_cert(os.path.join(self.ABAC_STORE_DIR, user_filename))
        attr_filename = user.id_keyid() + "_has_" + attr.role_head().role_name()  + self.ATTR_FILE_SUFFIX
        attr.attribute_write_cert(os.path.join(self.ABAC_STORE_DIR, attr_filename))

    def query(self, cert, slice_uuid, req=None):
        # Given the request type, check for the appropriate proof.
        # You'll need some way to map between request (post to node,
        # get on domain, etc) to a specific role that needs satisfying.
        
        # The slice uuid and other uuids will probably also need to be
        # derived from the request. The user cert usually comes from the
        # connection framework.

        user_id = ABAC.ID_chunk(cert)
        
        #out = self.ctx.context_principals()
        #for x in out[1]:
        #    print "%s " % x.string()

        role = ABAC.Role(self.server_id.id_keyid(), str(self.SLICE_ADMIN_ROLE_PREFIX + slice_uuid))
        p = ABAC.Role(user_id.id_keyid())

        self.ctx.set_no_partial_proof()
        (success, credentials) = self.ctx.query(role, p)
        #for c in credentials:
        #    print "%s <- %s" % (c.head_string(), c.tail_string())

        return success

