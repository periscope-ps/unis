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
import requests
import json

# Third-party imports
import bson
if hasattr(bson, 'dumps'):
    # standalone bson
    bson_encode = bson.dumps
    bson_decode = bson.loads
else:
    # pymongo's bson
    bson_encode = bson.BSON.encode
    bson_decode = bson.decode_all
    
    
headers={'content-type':
             'application/perfsonar+bson profile=http://unis.incntre.iu.edu/schema/20140214/data#',
         'accept':"*/*"}


data = [{"mid": "1234",
         "data": [
            {"ts": 143234212.3242,
             "_sample": 4,
             "sum_v": 3432532.342,
             "min_v": 1231241,
             "max_v": 3523523,
             "count": 39102}
            ]
         }]

jsreq = json.dumps(data)
bsreq = bson_encode(data[0])

try:
    r = requests.post("http://localhost/data", data=bsreq, headers=headers)
except Exception as e:
    print e

if r.status_code >= 400:
    print r.status_code, r.text
else:
    print r.status_code
