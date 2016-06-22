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
from abc import ABCMeta, abstractmethod

class PP_Error(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class PP_INTERFACE:
    __metaclass__ = ABCMeta

    PP_AUTH = 0
    PP_TYPES = ['AUTH']

    pp_type = ''

    @abstractmethod
    def pre_get(obj, app=None, req=None,Handler=None):
        return obj
    
    @abstractmethod
    def post_get(obj, app=None, req=None):
        return obj

    @abstractmethod
    def pre_post(obj, app=None, req=None,Handler=None):
        return obj

    @abstractmethod
    def post_post(obj, app=None, req=None):
        return obj

    @abstractmethod
    def process_query(obj, app=None, req=None,Handler=None):
        return obj
