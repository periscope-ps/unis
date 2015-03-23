#!/usr/bin/python

'''
Created on Oct 2, 2012

@author: ezkissel
'''

import os
import sys
import argparse
import httplib
import json
from urlparse import urlparse    

def main(argv=None):

    parser = argparse.ArgumentParser(description='process args', epilog='foo bar help')
    parser.add_argument('-w', '--follow', const='follow', dest='follow', action='store_const')
    parser.add_argument('-a', '--action', dest='action', nargs='?', default='GET')
    parser.add_argument('-c', '--cert', dest='certfile', nargs='?')
    parser.add_argument('-k', '--key', dest='keyfile', nargs='?')
    parser.add_argument('-f', '--file', dest='sendfile', nargs='?')
    parser.add_argument('-o', '--output', dest='outfile', nargs='?')
    parser.add_argument(dest='url')

    args = parser.parse_args()
    fi = None
    fo = None

    if args.sendfile:
        try:
            fi = open(args.sendfile, 'r')
        except IOError, msg:
            print 'could not open file: ' + msg.strerror
            return

    if args.outfile:
        try:
            fo = open(args.outfile, 'w')
        except IOError, msg:
            print 'could not open file: ' + msg.strerror
            return
    else:
        fo = sys.stdout

    o = urlparse(args.url)
    if args.certfile:
        conn = httplib.HTTPSConnection(o.hostname, o.port, args.keyfile, args.certfile)
    else:
        conn = httplib.HTTPConnection(o.hostname, o.port)

    query = o.path+'?'+o.query
    conn.request(args.action, query, fi)
    r = conn.getresponse()
    data = r.read()

    if r.status != 200:
        topo = data
    else:
        topo = json.loads(data)

    if args.follow and isinstance(topo, dict):
        check_href = ["links", "nodes", "ports"]
        for obj in check_href:
            try:
                oary = []
                for o in topo[obj]:
                    u = urlparse(o["href"])
                    conn.request("GET", u.path, None)
                    r = conn.getresponse()
                    data = r.read()
                    new = json.loads(data)
                    oary.append(new)
                topo[obj] = oary
            except:
                pass

    print "\nServer Response: %d %s" % (r.status, r.reason)

    print "Response data (%d bytes):" % len(data)
    print "================================================================================"
    json.dump(topo, fp=fo, indent=True)
    print "\n================================================================================"
    
    
if __name__ == '__main__':
    sys.exit(main())
