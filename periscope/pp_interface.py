from abc import ABCMeta, abstractmethod

class PP_Error(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class PP_INTERFACE:
    __metaclass__ = ABCMeta

    @abstractmethod
    def pre_get(obj, app=None, req=None):
        return obj
    
    @abstractmethod
    def post_get(obj, app=None, req=None):
        return obj

    @abstractmethod
    def pre_post(obj, app=None, req=None):
        return obj

    @abstractmethod
    def post_post(obj, app=None, req=None):
        return obj

    @abstractmethod
    def process_query(obj, app=None, req=None):
        return obj
