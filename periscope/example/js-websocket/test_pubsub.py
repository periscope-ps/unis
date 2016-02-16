import os
import json
from subprocess import call

exnode = ""

with open('test.uef') as uef:
    exnode = uef.read()


print call(["curl", "-H", "Content-Type: application/perfsonar+json", "--data", exnode, "http://localhost:8888/domains"])
