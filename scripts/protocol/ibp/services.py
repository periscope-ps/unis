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
'''
@Name:   ProtocolService.py
@Author: Jeremy Musser
@Date:   04/01/2015

-------------------------

ProtocolService provides low level API access
to the IBP protocol

'''

import argparse
import urllib2
import socket

import settings
import flags
import allocation

from flags import print_error

class ProtocolService(object):
    def __init__(self):
        pass
    
    def GetStatus(self, address, **kwargs):
    # Query the status of a Depot.
    
    # Generate request with the following form
    # IBPv031[0] IBP_ST_INQ[2] pwd timeout
        pwd = settings.DEFAULT_PASSWORD
        timeout = settings.DEFAULT_TIMEOUT
        tmpCommand = ""
        
        if "password" in kwargs:
            pwd = kwargs["password"]
        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        
        try:
            tmpCommand = "{0} {1} {2} {3} {4}\n".format(flags.IBPv031, flags.IBP_STATUS, flags.IBP_ST_INQ, pwd, timeout)
            result = self._dispatch_command(address["host"], address["port"], tmpCommand)
            if not result:
                return None
            result = result.split(" ")
        except Exception as exp:
            return None
            
        return dict(zip(["total", "used", "volatile", "used-volatile", "max-duration"], result))




    def Manage(self, alloc, **kwargs):
        cap_type    = 0
        reliability = flags.IBP_HARD
        timeout     = settings.DEFAULT_TIMEOUT
        max_size    = settings.DEFAULT_MAXSIZE
        duration    = settings.DEFAULT_DURATION
        tmpCommand  = ""
        mode        = flags.IBP_CHANGE

    # Generate manage request with the following form
    # IBPv031[0] IBP_MANAGE[9] manage_key "MANAGE" IBP_CHANGE[43] cap_type max_size duration reliability timeout
        if "cap_type" in kwargs:
            cap_type = kwargs["cap_type"]
        if "reliability" in kwargs:
            reliability = kwargs["reliability"]
        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        if "max_size" in kwargs:
            max_size = kwargs["max_size"]
        if "duration" in kwargs:
            duration = kwargs["duration"]
        if "mode" in kwargs:
            mode = kwargs["mode"]
            
        try:
            cap = alloc.GetManageCapability()
            tmpCommand = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9}\n".format(flags.IBPv031,
                                                                            flags.IBP_MANAGE,
                                                                            cap.key,
                                                                            cap.code,
                                                                            mode,
                                                                            cap_type,
                                                                            max_size,
                                                                            duration,
                                                                            reliability,
                                                                            timeout
                                                                            )
            result = self._dispatch_command(alloc.host, alloc.port, tmpCommand)
            if not result:
                return None
            result = result.split(" ")
        except Exception as exp:
            return None

        if result[0].startswith("-"):
            return None
        else:
            return result



    def Probe(self, alloc, **kwargs):
        results = self.Manage(alloc, mode = flags.IBP_PROBE, **kwargs)
        if not results:
            return None
        
        result = dict(zip(["read_count", "write_count", "size", "max_size", "duration", "reliability", "type"], results[1:]))
        return result
    
 

   
    def Allocate(self, depot, size, **kwargs):
    # Generate destination Allocation and Capabilities using the form below
    # IBPv031[0] IBP_ALLOCATE[1] reliability cap_type duration size timeout
        reliability = flags.IBP_HARD
        cap_type    = flags.IBP_BYTEARRAY
        timeout     = settings.DEFAULT_TIMEOUT
        duration    = settings.DEFAULT_DURATION
        tmpCommand  = ""

        if "reliability" in kwargs:
            reliability = kwargs["reliability"]
        if "type" in kwargs:
            cap_type = kwargs["type"]
        if "duration" in kwargs:
            duration = kwargs["duration"]
        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
            
        try:
            tmpCommand = "{0} {1} {2} {3} {4} {5} {6} \n".format(flags.IBPv031, flags.IBP_ALLOCATE, reliability, cap_type, duration, size, timeout)
            result = self._dispatch_command(depot["host"], depot["port"], tmpCommand)
            result = result.split(" ")[1:]

        except Exception as exp:
            return None

        if result[0].startswith("-"):
            return None

        alloc = allocation.Allocation()
        alloc.SetReadCapability(result[0])
        alloc.SetWriteCapability(result[1])
        alloc.SetManageCapability(result[2])
        alloc.depotSize = size
        return alloc
    
    
    # Below are several shorthand versions of Allocate for hard and soft allocations of various types.
    def AllocateSoftByteArray(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_SOFT, type = flags.IBP_BYTEARRAY, **kwargs)

    def AllocateHardByteArray(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_HARD, type = flags.IBP_BYTEARRAY, **kwargs)

    def AllocateSoftBuffer(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_SOFT, type = flags.IBP_BUFFER, **kwargs)
    
    def AllocateHardBuffer(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_HARD, type = flags.IBP_BUFFER, **kwargs)

    def AllocateSoftFifo(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_SOFT, type = flags.IBP_FIFO, **kwargs)

    def AllocateHardFifo(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_HARD, type = flags.IBO_FIFO, **kwargs)

    def AllocateSoftCirq(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_SOFT, type = flags.IBP_CIRQ, **kwargs)

    def AllocateHardCirq(self, depot, size, **kwargs):
        return self.Allocate(depot, size, reliability = flags.IBP_HARD, typ = flags.IBP_CIRQ, **kwargs)



    def Store(self, alloc, data, size, **kwargs):
        timeout  = settings.DEFAULT_TIMEOUT
        duration = settings.DEFAULT_DURATION
        tmpCommand  = ""

        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        if "duration" in kwargs:
            duration = kwargs["duration"]
        
        cap = alloc.GetWriteCapability()
        
        try:
            tmpCommand = "{0} {1} {2} {3} {4} {5}\n".format(flags.IBPv031, flags.IBP_STORE, cap.key, cap.wrmKey, size, timeout)
            result = self._dispatch_data(alloc.host, alloc.port, tmpCommand, data)
            if not result:
                return None
            result = result.split(" ")
        except Exception as exp:
            return None
            
        if result[0].startswith("-"):
            return None
        else:
            alloc.depotSize = size
            alloc.depotOffset = 0
            return duration


    def Send(self, source, destination, **kwargs):
    # Move an allocation from one {source} Depot to one {destination} depot
        timeout     = settings.DEFAULT_TIMEOUT
        duration    = settings.DEFAULT_DURATION
        tmpCommand  = ""
        offset      = 0

        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        if "duration" in kwargs:
            duration = kwargs["duration"]
        if "offset" in kwargs:
            offset = kwars["offset"]
        size = kwargs.get("size", source.depotSize)

        src_cap  = source.GetReadCapability()
        dest_cap = destination.GetWriteCapability()
        
    # Generate move request with the following form
    # IBPv040[1] IBP_SEND[5] src_read_key src_WRMKey dest_write_cap offset size timeout timeout timeout
        try:
            tmpCommand = "{version} {command} {source} {dest} {keytype} {offset} {size} {timeout} {timeout} {timeout} \n".format(version = flags.IBPv040,
                                                                                                                                 command = flags.IBP_SEND,
                                                                                                                                 source  = src_cap.key,
                                                                                                                                 dest    = str(dest_cap),
                                                                                                                                 keytype = src_cap.wrmKey,
                                                                                                                                 offset  = offset,
                                                                                                                                 size    = source.depotSize,
                                                                                                                                 timeout = timeout)
            result = self._dispatch_command(source.host, source.port, tmpCommand)
            if not result:
                return None
            result = result.split(" ")
        except Exception as exp:
            return None

        if result[0].startswith("-"):
            return None
        else:
            return duration
                         


    def Load(self, alloc, **kwargs):
        timeout = settings.DEFAULT_TIMEOUT
        tmpCommand  = ""

        if "timeout" in kwargs:
            timeout = kwargs["timeout"]
        
        cap = alloc.GetReadCapability()
        
        try:
            tmpCommand = "{version} {command} {key} {wrmkey} {offset} {length} {timeout} \n".format(version = flags.IBPv031, 
                                                                                                    command = flags.IBP_LOAD, 
                                                                                                    key     = cap.key, 
                                                                                                    wrmkey  = cap.wrmKey,
                                                                                                    offset  = alloc.depotOffset,
                                                                                                    length  = alloc.depotSize,
                                                                                                    timeout = timeout)
            result = self._recieve_data(alloc.host, alloc.port, tmpCommand, alloc.depotSize)
            if not result:
                return None
        except Exception as exp:
            return None
            
        if result["headers"].startswith("-"):
            return None
        else:
            return result["data"]


    def _recieve_data(self, host, port, command, size):
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        try:
            sock.send(command)
            header = sock.recv(1024)
            data = sock.recv(size)
        except socket.timeout as e:
            return None
        except e:
            return None
        finally:
            sock.close()
        
        return { "headers": header, "data": data }


    def _dispatch_data(self, host, port, command, data):
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        try:
            sock.send(command)
            response = sock.recv(1024)
            if not response.startswith("-"):
                sock.send(data)
                response = sock.recv(1024)
        except socket.timeout as e:
            return None
        except e:
            return None
        finally:
            sock.close()
                
        return response
        

    def _dispatch_command(self, host, port, command):
    # Create socket and configure with host and port
        port = int(port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        try:
            sock.send(command)
            response = sock.recv(1024)
        except socket.timeout as e:
            return None
        except e:
            return None
        finally:
            sock.close()
        
        return response


def UnitTests():
    depot1 = { "host": "dresci.incntre.iu.edu", "port": 6714 }
    depot2 = { "host": "ibp1.crest.iu.edu", "port": 6714 }
    service = ProtocolService()
    
    status1 = service.GetStatus(depot1)
    status2 = service.GetStatus(depot2)
    
    assert status1 and status2
    print "Dresci: {status}".format(status = status1)
    print "IBP1:   {status}\n".format(status = status2)
    
    data = """Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vestibulum tortor quam, feugiat vitae, ultricies eget, tempor sit amet, ante. Donec eu libero sit amet quam egestas semper. Aenean ultricies mi vitae est. Mauris placerat eleifend leo. Quisque sit amet est et sapien ullamcorper pharetra. Vestibulum erat wisi, condimentum sed, commodo vitae, ornare sit amet, wisi. Aenean fermentum, elit eget tincidunt condimentum, eros ipsum rutrum orci, sagittis tempus lacus enim ac dui. Donec non enim in turpis pulvinar facilisis. Ut felis. Praesent dapibus, neque id cursus faucibus, tortor neque egestas augue, eu vulputate magna eros eu erat. Aliquam erat volutpat. Nam dui mi, tincidunt quis, accumsan porttitor, facilisis luctus, metus"""
    
    first_alloc = service.Allocate(depot1, len(data))
    second_alloc = service.Allocate(depot2, len(data))
    
    assert first_alloc and second_alloc
    
    alloc_status1 = service.Probe(first_alloc)
    alloc_status2 = service.Probe(second_alloc)
    
    assert alloc_status1 and alloc_status2
    print "Alloc1: {status}".format(status = alloc_status1)
    print "Alloc2: {status}\n".format(status = alloc_status2)
    
    duration = service.Store(first_alloc, data, len(data))
    
    assert duration

    is_ok = service.Manage(first_alloc, duration = 300)

    print service.Probe(first_alloc)
    
    assert is_ok
    
#    duration2 = service.Send(first_alloc, second_alloc)
    
#    assert duration2
    
#    new_status1 = service.Probe(first_alloc)
#    new_status2 = service.Probe(second_alloc)
    
#    assert new_status1 and new_status2
#    print "Alloc1 (new): {status}".format(status = new_status1)
#    print "Alloc2 (new): {status}\n".format(status = new_status2)

#    data_out = service.Load(second_alloc)

#    assert data_out

#    print data_out

if __name__ == "__main__":
    UnitTests()
