import os
import json
from subprocess import call

exnode = ""

domain = """
{
  "links": [
    {
      "directed": false, 
      "name": "lan0", 
      "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill+link+lan0", 
      "properties": {
        "geni": {
          "interface_refs": [
            {
              "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44289", 
              "component_id": "urn:publicid:IDN+instageni.illinois.edu+interface+pc3:eth1", 
              "client_id": "ibp0:if0"
            }, 
            {
              "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44290", 
              "component_id": "urn:publicid:IDN+instageni.illinois.edu+interface+pc1:eth1", 
              "client_id": "ibp1:if0"
            }
          ], 
          "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
          "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
          "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44288", 
          "client_id": "lan0", 
          "link_types": [
            {
              "name": "lan"
            }
          ], 
          "properties": [
            {
              "source_id": "ibp0:if0", 
              "dest_id": "ibp1:if0"
            }, 
            {
              "source_id": "ibp1:if0", 
              "dest_id": "ibp0:if0"
            }
          ], 
          "vlantag": "258"
        }
      }, 
      "$schema": "http://unis.incntre.iu.edu/schema/20140214/link#", 
      "endpoints": [
        {
          "href": "$.ports[?(@.properties.geni.client_id=='urn:publicid:IDN+instageni.illinois.edu+sliver+44289')]", 
          "rel": "full"
        }, 
        {
          "href": "$.ports[?(@.properties.geni.client_id=='urn:publicid:IDN+instageni.illinois.edu+sliver+44290')]", 
          "rel": "full"
        }
      ], 
      "id": "ch.geni.net:idms_slice_idms-ig-ill_link_lan0"
    }
  ], 
  "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
  "properties": {
    "geni": {
      "expires": "2016-03-03T19:08:55Z", 
      "type": "manifest", 
      "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
      "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill"
    }
  }, 
  "id": "ch.geni.net:idms_slice_idms-ig-ill", 
  "$schema": "http://unis.incntre.iu.edu/schema/20140214/domain#", 
  "nodes": [
    {
      "name": "ibp-105-1", 
      "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill+node+ibp-105-1", 
      "relations": {
        "over": [
          {
            "href": "urn:publicid:IDN+instageni.illinois.edu+node+pc3", 
            "rel": "full"
          }
        ]
      }, 
      "id": "ibp-105-1.idms-ig-ill.ch-geni-net.instageni.illinois.edu", 
      "$schema": "http://unis.incntre.iu.edu/schema/20140214/node#", 
      "properties": {
        "geni": {
          "exclusive": false, 
          "component_id": "urn:publicid:IDN+instageni.illinois.edu+node+pc3", 
          "logins": [
            {
              "username": "miaozhan", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm3-24.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "pvivekan", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm3-24.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "swany", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm3-24.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "ezkissel", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm3-24.instageni.illinois.edu", 
              "port": "22"
            }
          ], 
          "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
          "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
          "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44285", 
          "hosts": [
            {
              "hostname": "ibp-105-1.idms-ig-ill.ch-geni-net.instageni.illinois.edu"
            }
          ], 
          "client_id": "ibp-105-1", 
          "sliver_type": {
            "disk_images": [
              {
                "url": "https://www.utahddc.geniracks.net/image_metadata.php?uuid=c542f83c-62c1-11e5-a612-000099989701"
              }
            ], 
            "name": "emulab-xen"
          }, 
          "component_manager_id": "urn:publicid:IDN+instageni.illinois.edu+authority+cm"
        }
      }, 
      "ports": [
        {
          "href": "#/ports/0", 
          "rel": "full"
        }
      ]
    }, 
    {
      "name": "ibp-105-2", 
      "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill+node+ibp-105-2", 
      "relations": {
        "over": [
          {
            "href": "urn:publicid:IDN+instageni.illinois.edu+node+pc1", 
            "rel": "full"
          }
        ]
      }, 
      "id": "ibp-105-2.idms-ig-ill.ch-geni-net.instageni.illinois.edu", 
      "$schema": "http://unis.incntre.iu.edu/schema/20140214/node#", 
      "properties": {
        "geni": {
          "exclusive": false, 
          "component_id": "urn:publicid:IDN+instageni.illinois.edu+node+pc1", 
          "logins": [
            {
              "username": "miaozhan", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm1-21.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "pvivekan", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm1-21.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "swany", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm1-21.instageni.illinois.edu", 
              "port": "22"
            }, 
            {
              "username": "ezkissel", 
              "authentication": "ssh-keys", 
              "hostname": "pcvm1-21.instageni.illinois.edu", 
              "port": "22"
            }
          ], 
          "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
          "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
          "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44286", 
          "hosts": [
            {
              "hostname": "ibp-105-2.idms-ig-ill.ch-geni-net.instageni.illinois.edu"
            }
          ], 
          "client_id": "ibp-105-2", 
          "sliver_type": {
            "disk_images": [
              {
                "url": "https://www.utahddc.geniracks.net/image_metadata.php?uuid=c542f83c-62c1-11e5-a612-000099989701"
              }
            ], 
            "name": "emulab-xen"
          }, 
          "component_manager_id": "urn:publicid:IDN+instageni.illinois.edu+authority+cm"
        }
      }, 
      "ports": [
        {
          "href": "#/ports/1", 
          "rel": "full"
        }
      ]
    }
  ], 
  "ports": [
    {
      "name": "ibp0:if0", 
      "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill+interface+ibp0:if0", 
      "relations": {
        "over": [
          {
            "href": "urn:publicid:IDN+instageni.illinois.edu+interface+pc3:eth1", 
            "rel": "full"
          }
        ]
      }, 
      "id": "ch.geni.net:idms_slice_idms-ig-ill_interface_ibp0:if0", 
      "address": {
        "type": "ipv4", 
        "address": "10.10.105.1"
      }, 
      "$schema": "http://unis.incntre.iu.edu/schema/20140214/port#", 
      "properties": {
        "geni": {
          "component_id": "urn:publicid:IDN+instageni.illinois.edu+interface+pc3:eth1", 
          "ip": {
            "netmask": "255.255.0.0", 
            "type": "ipv4", 
            "address": "10.10.105.1"
          }, 
          "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
          "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
          "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44289", 
          "client_id": "ibp0:if0", 
          "mac_address": "02d170d35505"
        }
      }
    }, 
    {
      "name": "ibp1:if0", 
      "urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill+interface+ibp1:if0", 
      "relations": {
        "over": [
          {
            "href": "urn:publicid:IDN+instageni.illinois.edu+interface+pc1:eth1", 
            "rel": "full"
          }
        ]
      }, 
      "id": "ch.geni.net:idms_slice_idms-ig-ill_interface_ibp1:if0", 
      "address": {
        "type": "ipv4", 
        "address": "10.10.105.2"
      }, 
      "$schema": "http://unis.incntre.iu.edu/schema/20140214/port#", 
      "properties": {
        "geni": {
          "component_id": "urn:publicid:IDN+instageni.illinois.edu+interface+pc1:eth1", 
          "ip": {
            "netmask": "255.255.0.0", 
            "type": "ipv4", 
            "address": "10.10.105.2"
          }, 
          "slice_urn": "urn:publicid:IDN+ch.geni.net:idms+slice+idms-ig-ill", 
          "slice_uuid": "7266bb4e-73a4-44ab-b1c9-c6445f37b0a2", 
          "sliver_id": "urn:publicid:IDN+instageni.illinois.edu+sliver+44290", 
          "client_id": "ibp1:if0", 
          "mac_address": "02ecd329b07e"
        }
      }
    }
  ]
}
"""


exnode = """
{
    "parent": "55b186f5e779890e937b5d0d", 
    "$schema": "http://unis.incntre.iu.edu/schema/exnode/4/exnode#", 
    "test": "2",
    "extents": [
      {
        "lifetimes": [
          {
            "start": "2015-10-27 19:59:04", 
            "end": "2015-11-26 18:59:04"
          }
        ], 
        "mapping": {
          "write": "ibp://192.70.161.60:6714/1#kCyWCHGfUd9UWFeT2j51p0wy5PvoNjkj/2677001338316022366/WRITE", 
          "read": "ibp://192.70.161.60:6714/1#O2oL2kqk3U2+Dl17IOQYafUWzuUHQ8Nl/2677001338316022366/READ", 
          "manage": "ibp://192.70.161.60:6714/1#XvMhH-PIhrlaLF6CGhVCTCbq6LSVyaoy/2677001338316022366/MANAGE"
        }, 
        "location": "ibp://", 
        "offset": 0, 
        "size": 4630852
      }, 
      {
        "lifetimes": [
          {
            "start": "2015-10-27 19:59:04", 
            "end": "2015-11-26 18:59:04"
          }
        ],
        "mapping": {
          "write": "ibp://nadir.ersc.wisc.edu:6714/1#sL4x5r+b4HBs24baUOZ5Dmw9cJSFeRnO/11922522949527297294/WRITE", 
          "read": "ibp://nadir.ersc.wisc.edu:6714/1#VkhPG+4GJYsfdVTRU8nZf62Q6IZK+Zd5/11922522949527297294/READ", 
          "manage": "ibp://nadir.ersc.wisc.edu:6714/1#F22lVoCZkgZimJDxG-LOt7l6sGzMWmFz/11922522949527297294/MANAGE"
        }, 
        "location": "ibp://", 
        "offset": 0, 
        "size": 4630852
      }, 
      {
        "lifetimes": [
          {
            "start": "2015-10-27 19:59:04", 
            "end": "2015-11-26 18:59:04"
          }
        ], 
        "mapping": {
          "write": "ibp://dresci.incntre.iu.edu:6714/0#yVS5NNQOVxeRx6QMzdj8atwlPLOrsHjm/17346428427372809818/WRITE", 
          "read": "ibp://dresci.incntre.iu.edu:6714/0#7rtZSJAvfu1TWkpJPEn+uPTewRVbvIyp/17346428427372809818/READ", 
          "manage": "ibp://dresci.incntre.iu.edu:6714/0#KjA5Aka6oyyt85ubQk2ubODE2Zh5rxLV/17346428427372809818/MANAGE"
        }, 
        "location": "ibp://", 
        "offset": 0, 
        "size": 4630852
      }
    ], 
    "name": "LC80480262015300LGN00.zip", 
    "created": 1445990345, 
    "secToken": [
      "landsat"
    ], 
    "modified": 1445990345, 
    "mode": "file", 
    "size": 4630852, 
    "metadata": {
      "productCode": "FR_BUND", 
      "scene": "LC80480262015300LGN00"
    }
}
"""

network = """
{
  "propertyX": "stuff",
  "nodes": [
    {
      "directed": true,
      "endpoints": ["192.168.1.1", "10.0.0.1"]
    },
    {
      "directed": false,
      "endpoints": ["192.168.1.2", "10.0.0.2"]
    }
  ]
}
"""

print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", domain, "http://localhost:8888/domains"])
