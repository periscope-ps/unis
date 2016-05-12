#----------------------------------------------------------------------
# Copyright (c) 2011-2014 Raytheon BBN Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
#----------------------------------------------------------------------

# Class to manage a set of ABAC credentials, certificates and prove queries

from ConfigParser import ConfigParser
import optparse
import os
import subprocess
import sys
import tempfile
import ABAC
from chapi_log import *

# Generate an ABACManager config file
# [Principals]
# name=certfile
# ...
# [Keys]
# name=keyfile
#
# Return name of config file and any tempfiles created in this process
def create_abac_manager_config_file(id_cert_files, id_certs, id_key_files, \
                                        raw_assertions):
    tempfiles = []
    # Format
    # [Principals]
    # The principals ("ME" and any in ID dictionary)
    # [Keys]
    # The keys ("ME")
    # [AssertionFiles]
    (fd, config_filename) = tempfile.mkstemp()
    tempfiles.append(config_filename)

    os.close(fd)
    file = open(config_filename, 'w')
    file.write('[Principals]\n')
    for id_name, id_cert_file in id_cert_files.items():
        file.write('%s=%s\n' % (id_name, id_cert_file))
    for id_name, id_cert in id_certs.items():
        (id_fd, id_filename) = tempfile.mkstemp()
        tempfiles.append(id_filename)
        os.close(id_fd)
        id_file = open(id_filename, 'w')
        id_file.write(id_cert)
        id_file.close()
        file.write('%s=%s\n' % (id_name, id_filename))

    file.write('[Keys]\n')
    for id_key_name, id_key_file in id_key_files.items():
        file.write('%s=%s\n' % (id_key_name, id_key_file))

    file.write('[AssertionFiles]\n')
    for raw_assertion in raw_assertions:
        (raw_fd, raw_filename) = tempfile.mkstemp()
        tempfiles.append(raw_filename)
        os.close(raw_fd)
        raw_file = open(raw_filename, 'w')
        raw_file.write(raw_assertion)
        raw_file.close()
        file.write('%s=None\n' % raw_filename)

    file.close()

    return config_filename, tempfiles

# Run a subprocess and grab and return contents of standard output
def grab_output_from_subprocess(args):
    proc  = subprocess.Popen(args, stdout=subprocess.PIPE)
    result = ''
    chunk = proc.stdout.read()
    while chunk:
        result = result + chunk
        chunk = proc.stdout.read()
    return result

# Run a subprocess and execute and grab results of ABAC query evaluation
def execute_abac_query(query, id_certs, raw_assertions = []):
    config_filename, tempfiles = \
        create_abac_manager_config_file({}, id_certs, {}, raw_assertions)

    # Make the query call, pull result from stdout
    chapi_home = os.getenv('CHAPIHOME')
    chapi_tools = os.path.join(chapi_home, 'tools')
    args = ['python', os.path.join(chapi_tools, 'ABACManager.py'),
            '--config=%s' % config_filename,
            '--query=%s' % query]
    chapi_debug("ABAC", "Exec ABAC Query ARGS = %s" % " ".join(args))
    result = grab_output_from_subprocess(args)

    result_parts = result.split('\n')

    ok = result_parts[0].find('Succeeded') >= 0
    proof = "\n".join(result_parts[1:])
    
    # Delete the tempfiles
    for tfile in tempfiles:
        os.unlink(tfile)

    return ok, proof



# Generate an ABAC credential of a given assertion signed by "ME"
# with a set of id_certs (a dictionary of {name : cert}
# Run this as a separate process to avoid memory corruption
def generate_abac_credential(assertion, me_cert, me_key, id_certs):
    # Create config file
    id_cert_files = {'ME' : me_cert}
    id_key_files = {'ME' : me_key}
    config_filename, tempfiles = \
        create_abac_manager_config_file(id_cert_files, id_certs, id_key_files, [])

    # Make the call, pull result from stdout
    chapi_home = os.getenv('CHAPIHOME')
    chapi_tools = os.path.join(chapi_home, 'tools')
    args = ['python', os.path.join(chapi_tools, 'ABACManager.py'), 
                                   '--config=%s' % config_filename, 
                                   '--credential=%s' % assertion]
    cred = grab_output_from_subprocess(args)

    # Delete the tempfiles
    for tfile in tempfiles:
        os.unlink(tfile)

    return cred


class ABACManager:

    # Constants
    ten_years = 10*365*24*3600

    # Constructor 
    # Optional arguments:
    #    certs_by_name : A dictionary of principal_name => cert
    #    cert_files_by_name : A dictionary of principal_name => cert_filename
    #    key_files_by_name: A dictionary of principal_name => private_key_filename
    #    assertions :  A list of assertions as ABAC statements (X.Y<-Z e.g.)
    #    raw_assertions : A list of signed XML versions of ABAC statements
    #    assertion_files : A list of files contianing signed XML versions of ABAC statements    
    #    options : List of command-line provided optional values
    def __init__(self, certs_by_name={}, cert_files_by_name={}, \
                     key_files_by_name={}, \
                     assertions=[], raw_assertions=[], assertion_files=[],  \
                     options=None, manage_context=True):

        # For turning on/off integration with ABAC (for memory leak testing)
        self._manage_context = manage_context

        # For verbose debug output
        self._verbose = False

        # List of all ABAC principals (IDs) by name
        self._ids_by_name = {}

        # List of all files created from dumping certs or raw assertions
        self._created_filenames = []

        # The ABAC context object
        self._ctxt = ABAC.Context()

        # All certs provided as raw cert objects
        self._certs = []

        # All cert files indexed by principal name
        self._cert_files = {}

        # All key files indexed by principal name
        self._key_files ={}

        # All raw assertions (as ABAC expressions)
        self._assertions = []

        # All assertion files
        self._assertion_files = []

        # Process all the cert files
        for principal_name  in cert_files_by_name.keys():
            cert_file = cert_files_by_name[principal_name]
            principal = self.register_id(principal_name, cert_file)

        # Process all the raw certs
        for principal_name in certs_by_name.keys():
            cert = certs_by_name[principal_name]
            cert_file = self._dump_to_file(cert)
            principal = self.register_id(principal_name, cert_file)

        # Process the private keys
        for principal_name in key_files_by_name.keys():
            key_file = key_files_by_name[principal_name]
            self.register_key(principal_name,  key_file)

        # Process all assertions
        for assertion in assertions:
            self.register_assertion(assertion)

        # Process all raw_assertions
        for raw_assertion in raw_assertions:
            raw_assertion_file = self._dump_to_file(raw_assertion)
#            print "Loading raw assertion file " + raw_assertion_file
            self.register_assertion_file(raw_assertion_file)

        # Process all assertion files
        for assertion_file in assertion_files:
            self.register_assertion_file(assertion_file)


        # Save command-line options
        self._options = options

        # And process if provided
        if self._options:
            self.init_from_options()

        # *** Hack Testing
        self._all_assertions = []
        self._all_links = {} # ABAC links : where can I get to from X (All Y st. Y<-X)

    def init_from_options(self):

        # If a config file is provided, read it into the ABACManager
        if self._options.config:
            cp = ConfigParser()
            cp.optionxform=str
            cp.read(self._options.config)

            for name in cp.options('Principals'):
                cert_file = cp.get('Principals', name)
                self.register_id(name, cert_file)

            for name in cp.options('Keys'):
                key_file = cp.get('Keys', name)
                self.register_key(name, key_file)

            if 'Assertions' in cp.sections():
                for assertion in cp.options('Assertions'):
                    self.register_assertion(assertion)

            if 'AssertionFiles' in cp.sections():
                for assertion_file in cp.options("AssertionFiles"):
                    self.register_assertion_file(assertion_file)

        # Use all the other command-line options to override/augment 
        # the values in the ABCManager

        # Add new principal ID's / keys
        if self._options.id:
            for id_filename in options.id:
                parts = id_filename.split(':')
                id_name = parts[0].strip()
                id_cert_file = None
                if len(parts) > 1:
                    id_cert_file = parts[1].strip()
                    self.register_id(id_name, id_cert_file)
                    
                id_key_file = None
                if len(parts) > 2:
                    id_key_file = parts[2].strip()
                    self.register_key(name, id_key_file)

        # Register assertion files provided by command line
        if self._options.assertion_file:
            for assertion_file in self._options.assertion_file:
                self.register_assertion_file(assertion_file)

        # Grab pure ABAC assertions from commandline
        if self._options.assertion:
            for assertion in self._options.assertion:
                self.register_assertion(assertion)


#     # Certs and cert_files are dictioanries of name=> cert/cert_file
#     # Assertions are a list of RT0 statements 
#     #    X.Y<-Z 
#     #    X.Y<-Z.W
#     # or RT1_lite statements (translated into RT0)
#     #    X.Y(S)<-Z(T)
#     #    X.Y(S)<-Z.W(T)
#     # 
#     # Throw an exception if any assertion refers 
#     #to any object not in a provided cert/file
#     def __init__(self, certs = {}, cert_files = {}, key_files = {},
#                      assertions = [], raw_assertions = [], assertion_files = []):
#         self._certs = certs
#         self._cert_files = cert_files # Indexed by principal name
#         self._key_files = key_files # Indexed by principal name
#         self._assertions = assertions
#         self._assertion_files = assertion_files


#         # dump all the certs into temp cert files and register
#         for name in self._certs.keys():
#             cert = self._certs[name]
#             cert_filename = self._dump_to_file(cert)
#             self.register_id(iname, cert_filename)

#         # Add all cert_files provided
#         for name in self._cert_files.keys():
#             cert_filename = self._cert_files[name]
#             self.register_id(name, cert_filename)
#             # Generate self-signed cert if no cert file provided
#             if cert_filename is None:
#                 id = ABAC.ID(name, self.ten_years)
#             else:
#                 id = ABAC.ID(cert_filename)
#                 # If there is a key associated with this principal, load it
#                 if self._key_files.has_key(name):
#                     key_filename = self._key_files[name]
#                     if key_filename is not None:
#                         id.load_privkey(key_filename)
#             self.register_id(id, name)


#         # Parse and create all the assertions. 
#         for assertion in assertions:
#             self.register_assertion(assertion)

#         # Dump all raw_assertions (signed XML documents containing assertions)
#         for raw_assertion in raw_assertions:
#             raw_assertion_file = self._dump_to_file(raw_assertion)
# #            print "Loading raw assertion file " + raw_assertion_file
#             self._ctxt.load_attribute_file(raw_assertion_file)

#         # Register assertions from files
#         for assertion_file in assertion_files:
# #            print "Loading assertion file " + assertion_file
#             self._ctxt.load_attribute_file(assertion_file)

    def run(self):
        if self._options.query:
            ok, proof = self.query(self._options.query)
            if ok:
                print "Succeeded"
            else:
                print "Failed"
            print "\n".join(self.pretty_print_proof(proof))
        else:
            assertion = self.register_assertion(self._options.credential)
            self._dump_assertion(assertion, self._options.outfile)

    # Traverse tree of ABAC expression finding path leading from 'from_expr' to 'to_expr'
    # *** Hack
    def find_path(self, from_expr, to_expr):
        if from_expr not in self._all_links: return False
        if to_expr in self._all_links[from_expr]: return True
        for link in self._all_links[from_expr]: 
            if self.find_path(link, to_expr):
                return True
        return False

    # Does given target have given role?
    # I.e. can we prove query statement Q (X.role<-target)
    # Return ok, proof
    def query(self, query_expression):

        # *** Hack ***
        # Sorry you gotta parse the expressions and go head-to-tail...
        if not self._manage_context:
            parts = query_expression.split('<-')
            lhs = parts[0]
            rhs = parts[1]
            response = self.find_path(rhs, lhs)
            return response, None

        query_expression = str(query_expression) # Avoid unicode
        query_expression_parts = query_expression.split("<-")
        if len(query_expression_parts) != 2:
            raise Exception("Illegal query expression : " + query_expression)
        query_lhs = query_expression_parts[0].strip()
        query_lhs_parts = query_lhs.split(".")
        if len(query_lhs_parts) != 2:
            raise Exception("Illegal query expression : " + query_expression)
        signer = query_lhs_parts[0].strip()
        signer_keyid = self._resolve_principal(signer).keyid()
        role_name = query_lhs_parts[1].strip()
        role = self._resolve_role(role_name)
        query_rhs = query_expression_parts[1].strip()
        target_name = query_rhs
        target = self._resolve_principal(target_name)
        resolved_query_expression = "%s.%s" % (signer_keyid, role)
        ok, proof = self._ctxt.query(resolved_query_expression, target.keyid())
        return ok, proof

    # Delete all the tempfiles create
    def __del__(self):
        del self._ctxt
        for created_filename in self._created_filenames:
            os.remove(created_filename)

    # Register a new ID with the manager, loading into lookup table and context
    def register_id(self, name, cert_file):
        # *** Hack ***
        if not self._manage_context:
            return

        if cert_file == '' or cert_file == 'None':
            cert_file = None
        if cert_file:
            id = ABAC.ID(cert_file)
        else:
            id = ABAC.ID(name, self.ten_years)

        if self._verbose:
            chapi_audit_and_log('ABAC', "Registering ID: " + name + " " + str(cert_file))

        if self._ids_by_name.has_key(name):
            raise Exception("ABACManager: name doubley defined " + name)
        self._ids_by_name[name] = id
        self._ctxt.load_id_chunk(id.cert_chunk()) 

    # Load a private key with a principal
    def register_key(self, name, key_file):
        # *** Hack ***
        if not self._manage_context:
            return

        if key_file and key_file != '' and key_file != 'None':
            id = self._ids_by_name[name]
            id.load_privkey(key_file)
            if self._verbose:
                chapi_audit_and_log('ABAC', "Registering key " + name + " " + key_file)


    # Register a new assertion with the manager
    # Parse the expression and resolve the pieces 
    # into RT1_line/RT0 roles and principal keyids
    # Generate exception if a principal is referenced but not registered
    def register_assertion(self, assertion):

        if self._verbose:
            chapi_audit_and_log('ABAC', "Registering assertion  " + assertion)

        # *** Hack ***
        if not self._manage_context:
            self._all_assertions.append(assertion)
            parts = assertion.split('<-')
            subject_role= parts[0]
            principal = parts[1]
            if principal not in self._all_links: self._all_links[principal] = []
            self._all_links[principal].append(subject_role)
            return # *** HACK

        assertion = str(assertion) # Avoid unicode
        assertion_pieces = assertion.split("<-")
        if len(assertion_pieces) != 2:
            raise Exception("Ill-formed assertion: need exactly 1 <- : " \
                                + assertion)
        lhs = assertion_pieces[0].strip()
        rhs = assertion_pieces[1].strip()
        lhs_pieces = lhs.split('.')
        if len(lhs_pieces) != 2:
            raise Exception("Ill-formed assertion LHS: need exactly 1 . : " \
                                + lhs)
        subject = self._resolve_principal(lhs_pieces[0])
        role = self._resolve_role(lhs_pieces[1])
        lhs_pieces = lhs.split('.')

        P = ABAC.Attribute(subject, role, self.ten_years)

        rhs_pieces = rhs.split('.')
        if len(rhs_pieces) >= 1:
            principal_name = rhs_pieces[0].strip()
            object = self._resolve_principal(principal_name)

        if len(rhs_pieces) == 1:
            P.principal(object.keyid())
        elif len(rhs_pieces) == 2:
            role_name = rhs_pieces[1].strip()
            role = self._resolve_role(role_name)
            P.role(object.keyid(), role)
        elif len(rhs_pieces) == 3:
            # Linking role
            role1 = rhs_pieces[1].strip()
            role2 = rhs_pieces[2].strip()
            linking_role_left = self._resolve_role(role1)
            linking_role_right = self._resolve_role(role2)
            P.linking_role(object.keyid(), linking_role_left,linking_role_right)
        else:
            raise Exception("Ill-formed assertion RHS: need < 2 . : " + rhs)

        P.bake()
        self._ctxt.load_attribute_chunk(P.cert_chunk())

        self._assertions.append(assertion)
        return P

    def register_assertion_file(self, assertion_file):
        if self._verbose:
            chapi_audit_and_log('ABAC', "Registering assertion file " + assertion_file)
        self._assertion_files.append(assertion_file)
        if self._manage_context:
            self._ctxt.load_attribute_file(assertion_file) 

    # return list of user-readable credentials in proof chain
    def pretty_print_proof(self, proof):
        proof_texts = \
            ["%s<-%s" % \
                 (self._transform_string(elt.head().string()), \
                      self._transform_string(elt.tail().string())) \
                 for elt in proof]
        return proof_texts

    # Some internal helper functions


    # Dump a cert or credential to a file, returning filename
    def _dump_to_file(self, contents):
        (fd, filename) = tempfile.mkstemp()
        os.close(fd)
        file = open(filename, 'w')
        file.write(contents)
        file.close()
        self._created_filenames.append(filename)
        return filename

    # Dump an assertion to stdout or a file, 
    # depending on whether outfile_name is set
    def _dump_assertion(self, assertion, outfile_name):
        outfile = sys.stdout
        if outfile_name:
            try:
                outfile = open(outfile_name, 'w')
            except Exception:
                print "Can't open outfile " + options.outfile
                sys.exit(-1)
        assertion.write(outfile)
        if outfile_name:
            outfile.close()


    # Lookup principal by name and return
    # Raise exception if not found
    def _resolve_principal(self, name):
        if self._ids_by_name.has_key(name):
            return self._ids_by_name[name]
        else:
            raise Exception("Unregistered principal: " + name)

    # Resolve a role string into RT1_lite syntax
    # I.e. 
    #    R => R (where R is a simple non-parenthesized string)
    #    R(S) => R_S.keyid() where S is the name of  principal
    def _resolve_role(self, role):
        has_lpar = role.find("(")
        has_rpar = role.find(")")
        if has_lpar < 0and has_rpar < 0:
            return role
        elif has_lpar >- 0 and has_rpar >= 0 and has_lpar < has_rpar:
            role_parts = role.split('(')
            role_name = role_parts[0].strip()
            object_parts = role_parts[1].split(')')
            object_name = object_parts[0].strip()
            object = self._resolve_principal(object_name)
            return "%s_%s" % (role_name, object.keyid())
        else:
            raise Exception("Ill-formed role: " + role)

    # Replace keyids with string names in string
    def _transform_string(self, string):
        for id_name in self._ids_by_name.keys():
            id = self._ids_by_name[id_name]
            id_keyid = id.keyid()
            string = string.replace(id_keyid, id_name)
        return string


def main(argv=sys.argv):
    parser = optparse.OptionParser(description='Produce an ABAC Assertion')
    parser.add_option("--assertion", 
                      help="ABAC-style assertion",
                      action = 'append',
                      default=[])
    parser.add_option("--assertion_file", 
                      help="file containing ABAC assertion",
                      default = [])
    parser.add_option("--id", action='append', 
                      help="Identifier name (self-signed case) or " + 
                      "name:cert_file (externally signed case")
    parser.add_option("--credential", 
                      help="Expression of ABAC statement for which to generate signed credential")
    parser.add_option("--query", help="Query expression to evaluate")
    parser.add_option('--outfile',  
                      help="name of file to put signed XML contents of credential (default=stdout)")
    parser.add_option('--config', 
                      help="Name of config file with Principals/Keys/Assertions/AssertionFiles sections", 
                      default = None)

    (options, args) = parser.parse_args(argv)

    # We need either a query or credential expression
    if not options.query and not options.credential:
        parser.print_help()
        sys.exit(-1)

    manager = ABACManager(options=options)
    manager._verbose = True
    manager.run()

if __name__ == "__main__":

    main()
    sys.exit(0)





    
                          


    
