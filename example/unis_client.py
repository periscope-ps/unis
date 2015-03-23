#!/usr/bin/python

'''
Created on Oct 2, 2012

@author: ezkissel
'''

import os
import sys
import argparse
import httplib
from urlparse import urlparse    

def main(argv=None):

    usage_desc = "usage: unis_client.py <URL> <action> <certfile> <keyfile> [file]"

    parser = argparse.ArgumentParser(description='process args', usage=usage_desc, epilog='foo bar help')
    parser.add_argument('URL')
    parser.add_argument('action')
    parser.add_argument('certfile')
    parser.add_argument('keyfile')
    parser.add_argument('sendfile', nargs='?')

    args = parser.parse_args()
    f = None

    if args.sendfile != None:
        try:
            f = open(args.sendfile, 'r')
        except IOError, msg:
            print 'could not open file: ' + msg.strerror
            return

    o = urlparse(args.URL)
    
    print o.query
    conn = httplib.HTTPSConnection(o.hostname, o.port, args.keyfile, args.certfile)

    if args.action in ("GET"):
        conn.request(args.action, o.path+'?'+o.query, f)
    elif args.action in ("POST"):
        conn.request(args.action, o.path, f)
    else:
        print "Unknown action: %s" % args.action
        return

    r = conn.getresponse()
    data = r.read()
    
    print "\nServer Response: %d %s" % (r.status, r.reason)

    print "Response data (%d bytes):" % len(data)
    print "================================================================================"
    print data
    print "================================================================================"
    
    
if __name__ == '__main__':
    sys.exit(main())
