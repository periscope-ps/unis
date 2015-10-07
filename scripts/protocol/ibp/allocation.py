'''
@Name:   Allocation.py
@Author: Jeremy Musser
@Data:   04/01/2015

------------------------------

Allocation is a formal definition of the
allocation structure.  It contains keys
that can be used to access data on an IBP
depot.

'''

import datetime

import exnodemanager.record as record

class Allocation(object):
    def __init__(self, alloc = None):
        self._log = record.getLogger()

        self.allocationType = "ibp"
        self.Id          = ""
        self.realSize    = 0
        self.offset      = 0
        self.depotSize   = 0
        self.depotOffset = 0
        self.start       = datetime.datetime.utcnow()
        self.end         = datetime.datetime.utcnow()
        self.timestamp   = 0
        self.host        = ""
        self.port        = 6714
        self.exnode      = ""
        
        if alloc:
            self.Deserialize(alloc)



    def getAddress(self):
        return "{host}:{port}".format(host = self.host, port = self.port)

    def Inherit(self, alloc):
        self.SetReadCapability(str(alloc._read))
        self.SetWriteCapability(str(alloc._write))
        self.SetManageCapability(str(alloc._manage))
        self.depotSize   = alloc.depotSize
        self.depotOffset = alloc.depotOffset
        self.start       = alloc.start
        self.end         = alloc.end
        self.exnode      = alloc.exnode
        
                
    def Deserialize(self, alloc):
        try:
            self.Id          = alloc["id"]
            self.timestamp   = alloc["ts"]
            self.realSize    = alloc["size"]
            self.offset      = alloc["offset"]
            self.depotSize   = alloc.get("alloc_length", self.realSize)
            self.depotOffset = alloc.get("alloc_offset", self.offset)
            self.start       = datetime.datetime.strptime(alloc["lifetimes"][0]["start"], "%Y-%m-%d %H:%M:%S")
            self.end         = datetime.datetime.strptime(alloc["lifetimes"][0]["end"], "%Y-%m-%d %H:%M:%S")
            self.exnode      = alloc["parent"]
            self.SetReadCapability(alloc["mapping"]["read"])
            self.SetWriteCapability(alloc["mapping"]["write"])
            self.SetManageCapability(alloc["mapping"]["manage"])
            self._raw = alloc
        except Exception as exp:
            self._log.warn("{func:>20}| Unable to decode Allocation - {exp}".format(func = "Allocation", exp = exp))            
    
    def Serialize(self):
        if not self._raw:
            self._raw = {}
            self._raw["lifetimes"] = []
            self._raw["lifetimes"].append({})
            self._raw["mapping"] = {}

        self._raw["id"]           = self.Id
        self._raw["ts"]           = self.timestamp
        self._raw["size"]         = self.realSize
        self._raw["offset"]       = self.offset
        self._raw["alloc_length"] = self.depotSize
        self._raw["alloc_offset"] = self.depotOffset
        self._raw["parent"]       = self.exnode
        self._raw["lifetimes"][0]["start"] = self.start.strftime("%Y-%m-%d %H:%M:%S")
        self._raw["lifetimes"][0]["end"]   = self.end.strftime("%Y-%m-%d %H:%M:%S")
        self._raw["mapping"]["read"] = str(self.GetReadCapability())
        self._raw["mapping"]["write"] = str(self.GetWriteCapability())
        self._raw["mapping"]["manage"] = str(self.GetManageCapability())

        return self._raw

    def GetReadCapability(self):
        return self._read

    def GetWriteCapability(self):
        return self._write

    def GetManageCapability(self):
        return self._manage
        
    def SetReadCapability(self, read):
        try:
            tmpCap = Capability(read)
        except ValueError as exp:
            self._log.warn("{func:>20}| Unable to create capability - {exp}".format(func = "SetReadCapability", exp = exp))
            return False
        
        if self.host:
            if tmpCap.host != self.host:
                self._log.warn("{func:>20}| Host Mismatch, read and write hosts must be the same".format(func = "SetReadCapability"))
                return False
            elif tmpCap.port != self.port:
                self._log.warn("{func:>20}| Host Mismatch, read and write ports must be the same".format(func = "SetReadCapability"))
                return False                
        else:
            self.host = tmpCap.host
            self.port = tmpCap.port

        self._read = tmpCap
        

    def SetWriteCapability(self, write):
        try:
            tmpCap = Capability(write)
        except ValueError as exp:
            self._log.warn("{func:>20}| Unable to create capability - {exp}".format(func = "SetWriteCapability", exp = exp))
            return False
        
        if self.host:
            if self.host != tmpCap.host:
                self._log.warn("{func:>20}| Host Mismatch, read and write hosts must be the same".format(func = "SetWriteCapability"))
                return False
            elif self.port != tmpCap.port:
                self._log.warn("{func:>20}| Host Mismatch, read and write ports must be the same".format(func = "SetWriteCapability"))
                return False
        else:
            self.host = tmpCap.host
            self.port = tmpCap.port

        self._write = tmpCap

    def SetManageCapability(self, manage):
        try:
            tmpCap = Capability(manage)
        except ValueError as exp:
            self._log.warn("{func:>20}| Unable to create capability - {exp}".format(func = "SetManageCapability", exp = exp))
            return False
        
        if self.host:
            if self.host != tmpCap.host:
                self._log.warn("{func:>20}| Host Mismatch, read and manage hosts must be the same".format(func = "SetManageCapability"))
                return False
            elif self.port != tmpCap.port:
                self._log.warn("{func:>20}| Host Mismatch, read and manage ports must be the same".format(func = "SetManageCapability"))
                return False
        else:
            self.host = tmpCap.host
            self.port = tmpCap.port
        
        self._manage = tmpCap
        
    

class Capability(object):
    def __init__(self, cap_string):
        try:
            self._cap   = cap_string
            tmpSplit    = cap_string.split("/")
            tmpAddress  = tmpSplit[2].split(":")
            self.host   = tmpAddress[0]
            self.port   = tmpAddress[1]
            self.key    = tmpSplit[3]
            self.wrmKey = tmpSplit[4]
            self.code   = tmpSplit[5]
        except Exception as exp:
            raise ValueError('Malformed capability string')

    def __str__(self):
        return self._cap

    def __repr__(self):
        return self.__str__()
