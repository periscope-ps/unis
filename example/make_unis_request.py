#!/usr/bin/python

import os
import sys

def make_genislice_req(sf_cred, slice_cred):
    slice_req = """<?xml version="1.0" encoding="utf-8"?>
<unis-credentials>
  <slice-credential>%s</slice-credential>
  <sf-credential>%s</sf-credential>
</unis-credentials>"""
    return slice_req % (slice_cred, sf_cred)

def make_geniuser_req(sf_cred, role, pcert):
    slice_req = """<?xml version="1.0" encoding="utf-8"?>
<unis-credentials>
  <role>%s</role>
  <subject-cert>%s</subject-cert>
  <sf-credential>%s</sf-credential>
</unis-credentials>"""
    return slice_req % (role, pcert, sf_cred)

def read_file(fname):
    f = open(fname, 'r')
    return f.read()

def main():
    import optparse
    
    usage = "%prog [options]"
    desc = "Make UNIS speaks-for requests"
    
    parser = optparse.OptionParser(usage=usage, description=desc)
    parser.add_option("-t", "--type", dest="rtype", default="slice", help="Make a 'slice' or 'user' request")
    parser.add_option("-c", "--cred", dest="cred", default=None, help="Slice credential")
    parser.add_option("-s", "--sf_cred", dest="sf_cred", default=None, help="Speaks-for credential")
    parser.add_option("-r", "--role", dest="role", default=None, help="Role to assign")
    parser.add_option("-p", "--proxy", dest="pcert", default=None, help="Proxy certificate")
    opts, args = parser.parse_args(sys.argv[1:])
    
    if (opts.rtype=='slice' and opts.sf_cred and opts.cred):
        try:
            sf_cred = read_file(opts.sf_cred)
            cred = read_file(opts.cred)
        except Exception, e:
            print "Could not open file: %s" % e
            exit(1)
        print make_genislice_req(sf_cred, cred)
    elif (opts.rtype=='user' and opts.sf_cred and opts.role and opts.pcert):
        try:
            sf_cred = read_file(opts.sf_cred)
            pcert = read_file(opts.pcert)
        except Exception, e:
            print "Could not open file: %s" % e
            exit(1)
        print make_geniuser_req(sf_cred, opts.role, pcert)
    else:
        print "invalid arguments"
                  
if __name__ == "__main__":
    main()

