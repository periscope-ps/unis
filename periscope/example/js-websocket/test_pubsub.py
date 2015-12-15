import os
import json
from subprocess import call

exnode = ""

with open('test.uef') as uef:
    exnode = uef.read()

metadata = """
{
    "parameters": {
      "datumSchema": "http://unis.incntre.iu.edu/schema/20140214/datum#", 
      "measurement": {
        "href": "http://dev.incntre.iu.edu:8888/measurements/561d3802e7798906a033123f", 
        "rel": "full"
      }
    }, 
    "eventType": "ps:tools:blipp:linux:network:ip:utilization:drops", 
    "ts": 1444755463768479, 
    "subject": {
      "href": "http://dev.incntre.iu.edu:8888/ports/561d3802e7798906a033124b", 
      "rel": "full"
    }
  }
"""

exnode = """
{
    "parent": "55b186f5e779890e937b5d0d", 
    "$schema": "http://unis.incntre.iu.edu/schema/exnode/4/exnode#", 
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

print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", exnode, "http://localhost:8888/exnodes"])
