import os
import json
from subprocess import call


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
exnode["name"]     = "test_directory2"
exnode["size"]     = 0
exnode["parent"]   = None
exnode["mode"]     = "directory"
exnode["extents"]  = [] #extents

exnode = json.dumps(exnode)

#measurement = '{ "id": "2", "configuration": { "default_collection_size": 10000 }, "eventTypes": ["test1", "test2"] }'

#node = '{ "id": "3" }'

#service = '{ "id": "4", "serviceType": "Test Service" }'



print "\033[34mPublishing id \033[36m26\033[34m to files\033[0m"
print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", exnode, "http://localhost:8888/exnodes"])

#print "\033[34mPublishing id \033[36m2\033[34m to measurements\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", measurement, "http://localhost:8888/measurements"])

#print "\033[31mPublishing \033[36m3\033[31m to nodes\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", node, "http://localhost:8888/nodes"])

#print "\033[35mPublishing id \033[36m4\033[35m to services\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", service, "http://localhost:8888/services"])
