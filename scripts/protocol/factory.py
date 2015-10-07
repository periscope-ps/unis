
import json

import ibp.factory
import exnodemanager.record as record

def buildAllocation(json):
    if type(json) is str:
        try:
            json = json.loads(json)
        except Exception as exp:
            record.getLogger().warn("{func:>20}| Could not decode allocation - {exp}".format(func = "buildAllocation", exp = exp))
            return False
    
    # TODO: Implement allocation types
    # if json["type"] == "ibp":
    return ibp.factory.buildAllocation(json)
