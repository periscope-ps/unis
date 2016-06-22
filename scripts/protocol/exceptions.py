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

class AllocationException(Exception):
    ''' Generic exception for IBP related errors '''
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop("response", None)
        self.allocation = kwargs.pop("allocation", { "id": None })
        super(AllocationException, self).__init__(*args, **kwargs)
