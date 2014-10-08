import os
from subprocess import call

node = '''
{ "$schema" : "http://unis.incntre.iu.edu/schema/20140214/node#",
  "id" : "VM-0.pubsub.ch-geni-net.geni.kettering.edu",
  "name" : "VM-0",
  "ports" : [ { "href" : "https://unis.incntre.iu.edu:8443/ports/geni.kettering.edu_slice_pubsub_interface_VM-0%3Aif0",
        "rel" : "full"
      },
      { "href" : "https://unis.incntre.iu.edu:8443/ports/54148db4377f97513b6c9738",
        "rel" : "full"
      },
      { "href" : "https://unis.incntre.iu.edu:8443/ports/54148db5377f97513b6c973b",
        "rel" : "full"
      },
      { "href" : "https://unis.incntre.iu.edu:8443/ports/54148db5377f97513b6c9740",
        "rel" : "full"
      }
    ],
  "properties" : { "geni" : { "client_id" : "VM-0",
          "component_id" : "urn:publicid:IDN+geni.kettering.edu+node+pc2",
          "component_manager_id" : "urn:publicid:IDN+geni.kettering.edu+authority+cm",
          "exclusive" : false,
          "hosts" : [ { "hostname" : "VM-0.pubsub.ch-geni-net.geni.kettering.edu" } ],
          "slice_urn" : "urn:publicid:IDN+geni.kettering.edu+slice+pubsub",
          "slice_uuid" : "da4d6550-5bc1-4279-b6f7-ba8a8b7f0da7",
          "sliver_id" : "urn:publicid:IDN+geni.kettering.edu+sliver+10150",
          "sliver_type" : { "disk_images" : [ {  } ],
              "name" : "emulab-openvz"
            }
        } },
  "relations" : { "over" : [ { "href" : "urn:publicid:IDN+geni.kettering.edu+node+pc2",
            "rel" : "full"
          } ] },
  "selfRef" : "https://unis.incntre.iu.edu:8443/nodes/VM-0.pubsub.ch-geni-net.geni.kettering.edu",
  "ts" : 1410633142276536,
  "urn" : "urn:publicid:IDN+geni.kettering.edu+slice+pubsub+node+VM-0"
}
'''

service = '''
{ "$schema" : "http://unis.incntre.iu.edu/schema/20140214/service#",
  "description" : "BLiPP Service",
  "id" : "54148d5c377f97513b6c9704",
  "location" : { "institution" : "GEMINI" },
  "name" : "blipp",
  "properties" : { "configurations" : { "probe_defaults" : { "collection_schedule" : "builtins.simple",
              "collection_size" : 100000,
              "collection_ttl" : 1500000,
              "ms_url" : "https://pcvm2-4.geni.kettering.edu:8888",
              "reporting_params" : 8,
              "schedule_params" : { "every" : 2 }
            },
          "ssl_cafile" : "",
          "ssl_cert" : "/usr/local/etc/certs/mp_cert.pem",
          "ssl_key" : "/usr/local/etc/certs/mp_key.pem",
          "unis_poll_interval" : 30,
          "unis_url" : "https://unis.incntre.iu.edu:8443",
          "use_ssl" : true
        },
      "geni" : { "slice_uuid" : "da4d6550-5bc1-4279-b6f7-ba8a8b7f0da7" },
      "summary" : { "metadata" : [  ] }
    },
  "runningOn" : { "href" : "https://unis.incntre.iu.edu:8443/nodes/VM-0.pubsub.ch-geni-net.geni.kettering.edu",
      "rel" : "full"
    },
  "selfRef" : "https://unis.incntre.iu.edu:8443/services/54148d5c377f97513b6c9704",
  "serviceType" : "ps:tools:blipp",
  "status" : "ON",
  "ts" : 1410633140061872,
  "ttl" : 100000
}
'''

measurement = '''
{ "$schema" : "http://unis.incntre.iu.edu/schema/20140214/measurement#",
  "configuration" : { "collection_schedule" : "builtins.simple",
      "collection_size" : 100000,
      "collection_ttl" : 1500000,
      "kwargs" : { "proc_dir" : "/proc" },
      "ms_url" : "https://pcvm2-4.geni.kettering.edu:8888",
      "name" : "cpu",
      "probe_module" : "cpu",
      "reporting_params" : 8,
      "schedule_params" : { "every" : 2 }
    },
  "eventTypes" : [ "ps:tools:blipp:linux:cpu:utilization:iowait",
      "ps:tools:blipp:linux:cpu:utilization:hwirq",
      "ps:tools:blipp:linux:cpu:load:fivemin",
      "ps:tools:blipp:linux:cpu:utilization:user",
      "ps:tools:blipp:linux:cpu:utilization:swirq",
      "ps:tools:blipp:linux:cpu:utilization:guest",
      "ps:tools:blipp:linux:cpu:utilization:system",
      "ps:tools:blipp:linux:cpu:utilization:idle",
      "ps:tools:blipp:linux:cpu:load:fifteenmin",
      "ps:tools:blipp:linux:cpu:utilization:steal",
      "ps:tools:blipp:linux:cpu:load:onemin",
      "ps:tools:blipp:linux:cpu:utilization:nice"
    ],
  "id" : "54148db3377f97513b6c9735",
  "properties" : { "geni" : { "slice_uuid" : "da4d6550-5bc1-4279-b6f7-ba8a8b7f0da7" } },
  "selfRef" : "https://unis.incntre.iu.edu:8443/measurements/54148db3377f97513b6c9735",
  "service" : "https://unis.incntre.iu.edu:8443/services/54148d5c377f97513b6c9704",
  "ts" : 1410633139912614
}
'''

metadata = '''
{ "$schema" : "http://unis.incntre.iu.edu/schema/20140214/metadata#",
  "eventType" : "ps:tools:blipp:linux:cpu:load:fivemin",
  "id" : "54148dcd377f97513b6c97f6",
  "parameters" : { "datumSchema" : "http://unis.incntre.iu.edu/schema/20140214/datum#",
      "geni" : { "slice_uuid" : "da4d6550-5bc1-4279-b6f7-ba8a8b7f0da7" },
      "measurement" : { "href" : "https://unis.incntre.iu.edu:8443/measurements/54148db3377f97513b6c9735",
          "rel" : "full"
        }
    },
  "selfRef" : "https://unis.incntre.iu.edu:8443/metadata/54148dcd377f97513b6c97f9",
  "subject" : { "href" : "https://unis.incntre.iu.edu:8443/nodes/VM-0.pubsub.ch-geni-net.geni.kettering.edu",
      "rel" : "full"
    },
  "ts" : 1410633165691278
}
'''

data = '''
  { "ts" : 1410636418312413,
    "value" : 0.02
  },
  { "ts" : 1410636415789804,
    "value" : 0.02
  },
  { "ts" : 1410636413789815,
    "value" : 0.02
  },
  { "ts" : 1410636411789751,
    "value" : 0.02
  },
  { "ts" : 1410636409789714,
    "value" : 0.02
  },
  { "ts" : 1410636407789766,
    "value" : 0.02
  },
  { "ts" : 1410636405789025,
    "value" : 0.02
  },
  { "ts" : 1410636403789750,
    "value" : 0.02
  },
  { "ts" : 1410636401789810,
    "value" : 0.02
  },
  { "ts" : 1410636399789749,
    "value" : 0.02
  },
  { "ts" : 1410636397789808,
    "value" : 0.02
  },
  { "ts" : 1410636395789809,
    "value" : 0.02
  },
  { "ts" : 1410636393789769,
    "value" : 0.02
  },
  { "ts" : 1410636391789801,
    "value" : 0.02
  }
'''

print "\033[31mPublishing \033[36m3\033[31m to nodes\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", node, "http://localhost:8888/nodes"])

print "\033[35mPublishing id \033[36m4\033[35m to services\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", service, "http://localhost:8888/services"])

print "\033[34mPublishing id \033[36m2\033[34m to measurements\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", measurement, "http://localhost:8888/measurements"])

print "\033[34mPublishing id \033[36m2\033[34m to metadata\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", metadata, "http://localhost:8888/metadata"])

print "\033[34mPublishing id \033[36m2\033[34m to data\033[0m"
call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", data, "http://localhost:8888/data"])
