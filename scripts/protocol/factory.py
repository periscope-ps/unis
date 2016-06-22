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
