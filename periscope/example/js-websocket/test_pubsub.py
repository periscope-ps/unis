import os
import json
from subprocess import call

PARENT = "55772ebff8c2be1b1686ead7"
ID     = "55772ebff8c2be1b1686ead9"

dumpdir = {}
dumpdir["size"] = 0
dumpdir["created"] = 1426244007
dumpdir["modified"] = 1426244007
dumpdir["name"] = "dump"
dumpdir["parent"]   = None
dumpdir["mode"]     = "directory"
dumpdir["extents"] = []

extents = []

extent1 = {}
extent1["location"] = "ibp://"
extent1["size"]     = 12353
extent1["offest"]   = 2
extent1["mapping"]  = { "read": "stuff", "write": "other+stuff", "manage": "meh" }
extents.append(extent1)

extent2 = {}
extent2["location"] = "ibp://"
extent2["size"]     = 23453
extent2["offset"]   = 12353
extent2["mapping"]  = { "read": "blah2", "write": "further+blah", "manage": "foo" }
extents.append(extent2)

exnode = {}
exnode["created"]  = 14532097173
exnode["modified"] = 14532097173
exnode["name"]     = "test_file"
exnode["size"]     = 0
exnode["parent"]   = None
exnode["mode"]     = "file"
exnode["extents"]  = extents

extra_extent = {}
extra_extent["location"] = "ibp://"
extra_extent["size"] = 314159
extra_extent["offest"] = 885
extra_extent["mapping"] = { "read": "blah2", "write": "further+blah", "manage": "foo" }
extra_extent["parent"] = PARENT


updated_extent = {}
updated_extent["location"] = "UPDATED"
updated_extent["size"]     = 7357
updated_extent["offset"]   = 0
updated_extent["parent"]   = extra_extent["parent"]
updated_extent["id"]       = ID

exnode = json.dumps(exnode)
extra_extent = json.dumps(extra_extent)
updated_extent = json.dumps(updated_extent)
dumpdir = json.dumps(dumpdir)


#measurement = '{ "id": "2", "configuration": { "default_collection_size": 10000 }, "eventTypes": ["test1", "test2"] }'

#node = '{ "id": "3" }'

#service = '{ "id": "4", "serviceType": "Test Service" }'


#print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", exnode, "http://localhost:8888/exnodes"])

#print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", extra_extent, "http://localhost:8888/extents"])

print call(["curl", "-X", "PUT", "-H", "Content-Type: application/perfsonar+json", "--data", updated_extent, "http://localhost:8888/extents/{0}".format(ID)])

#print "\033[34mPublishing id \033[36m2\033[34m to measurements\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", measurement, "http://localhost:8888/measurements"])

#print "\033[31mPublishing \033[36m3\033[31m to nodes\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", node, "http://localhost:8888/nodes"])

#print "\033[35mPublishing id \033[36m4\033[35m to services\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", service, "http://localhost:8888/services"])
