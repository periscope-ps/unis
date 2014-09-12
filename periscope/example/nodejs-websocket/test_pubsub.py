import os
from subprocess import call


#node = '{"name": "user-os.indiana.edu","selfRef": "http://dev.incntre.iu.edu:8888/nodes/53f6c75ee77989013a00042b","urn": "urn:ogf:network:domain=indiana.edu:node=user-os:","ts": 1408681822244543,"id": "53f6c75ee77989013a00042b" }'
#service = '{"status": "ON","serviceType": "ps:tools:blipp","description": "BLiPP running on a GENI slice","selfRef": "http://dev.incntre.iu.edu:8888/services/53f6c75ee77989013a00042d","runningOn": {"href": "http://dev.incntre.iu.edu:8888/nodes/53f6c75ee77989013a00042a","rel": "full"},"ts": 1408682084796541,"id": "53f6c75ee77989013a00042d","location": {"institution": "GEMINI"},"ttl": 100000,"properties": {"summary": {"metadata": [ ]},"configurations": {"ssl_key": "/usr/local/etc/certs/mp_key.pem","ssl_cert": "/usr/local/etc/certs/mp_cert.pem","ssl_cafile": "","unis_url": "http://dev.incntre.iu.edu:8888","probe_defaults": {"schedule_params": {"every": 10},"reporting_tolerance": 10,"collection_schedule": "builtins.simple","collection_size": 10000000,"ms_url": "http://dev.incntre.iu.edu:8888","collection_ttl": 1500000,"reporting_params": 8},"use_ssl": "false","unis_poll_interval": 300}},"name": "blipp"}'
measurement = '{ "id": "3", "type": "iperf", "configuration": { "reporting_params": 1, "name": "socket test"}, "eventTypes": ["test1", "test2"] }'


#print "\033[31mPublishing \033[36m3\033[31m to nodes\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", node, "http://localhost:8888/nodes"])

#print "\033[35mPublishing id \033[36m4\033[35m to services\033[0m"
#call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", service, "http://localhost:8888/services"])
#
##print "\033[34mPublishing id \033[36m2\033[34m to measurements\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", measurement, "http://localhost:8888/measurements"])
