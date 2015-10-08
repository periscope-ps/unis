
import json

import ibp.factory

def buildAllocation(json):
    if type(json) is str:
        try:
            json = json.loads(json)
        except Exception as exp:
            return False
    
    # TODO: Implement allocation types
    # if json["type"] == "ibp":
    return ibp.factory.buildAllocation(json)
