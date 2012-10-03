'''
Created on Oct 2, 2012

@author: ezkissel
'''

import os
import sys
import httplib
from urlparse import urlparse    

def main(argv=None):

    usage = "usage: client.py <certfile> <keyfile> <sendfile> <URL>"

    if (argv == None):
        argv=sys.argv
        
    if (len(argv) < 5):
        print usage
        return

    _certfile = argv[1]
    _keyfile = argv[2]
    _sendfile = argv[3]
    _URL = sys.argv[4]

    try:
        f = open(_sendfile, 'r')
    except IOError, msg:
        print 'could not open file: ' + msg.strerror
        return

    o = urlparse(_URL)

    conn = httplib.HTTPSConnection(o.hostname, o.port, _keyfile, _certfile)
    conn.request("POST", o.path, f)
 
    r = conn.getresponse()
    
    print r.status, r.reason
    
if __name__ == '__main__':
    sys.exit(main())
