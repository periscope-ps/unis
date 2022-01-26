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
#!/usr/bin/env python

import json, uuid, re, logging
import tornado.web

import periscope.settings as settings


__manager__ = None

def GetManager():
    global __manager__
    
    if not __manager__:
        __manager__ = SubscriptionManager()

    return __manager__

class SubscriptionManager(object):
    def __init__(self):
        global __manager__
        
        self.log = logging.getLogger("unis.subman")
        self.subscriptions = []
        
        if __manager__:
            self.log.warn("SubscriptionManager: Multiple instantiations of singleton SubscriptionManager")

    # @description: publish informs all remote subscribers that a change has been
    #               made to the provided resource.
    # @input:       resource is a json object corrosponding to the resource in question.
    #               trim_function is an optional argument that overrides any previous
    #                 filter on the subscription and replaces them with a custom filter.
    def publish(self, resources, collection = None, headers = {}, trim_function = None):
        resources = resources if isinstance(resources, list) else [resources]
        for resource in resources:
            if "_id" in resource:
                del resource["_id"]
            self._publish(resource, collection, headers, trim_function)

    def _publish(self, resource, collection = None, headers = {}, trim_function = None):
        def _compare(op, val1, val2):
            try:
                if op == "gt":
                    return val1 > val2
                elif op == "gte":
                    return val1 >= val2
                elif op == "lt":
                    return val1 < val2
                elif op == "lte":
                    return val1 <= val2
                elif op == "equal":
                    return val1 == val2
                elif op == "reg":
                    return re.search(val2, val1)
                elif op == "in":
                    for inner_val in val2:
                        if val1 == inner_val:
                            return True
                    return False
                else:
                    self.log.warn("Unkown operator in subscription")
                    return False
            except TypeError as exp:
                self.log.warn("Invalid comparison operator in subscription - {exp}".format(exp = exp))
                return False
            except re.error as exp:
                self.log.warn("Invalid regex string - {exp}".format(exp = exp))
                return False
            
            return True

        for query in self.subscriptions:
            is_member = True
            tmpConditions = query["conditions"]
            if "collection" in query and query["collection"] != collection:
                continue
            
            for key, value in tmpConditions.items():
                tmpKeyList = key.split('.')
                if tmpKeyList[0] not in resource:
                    is_member = False
                    break
                else:
                    tmpResourceValue = resource
                
                # For multipart keys, find the value associated with the full key path
                for keyPart in tmpKeyList:
                    if keyPart in tmpResourceValue:
                        tmpResourceValue = tmpResourceValue[keyPart]
                    else:
                        is_member = False
                        break
                    
                # If the value of the query condition is a dict, it contains an operation that must be
                # evaluated.  If not, the value can be tested as-is.
                if type(value) is dict:
                    for op, inner_val in value.items():
                        if not _compare(op, tmpResourceValue, inner_val):
                            is_member = False
                            break
                else:
                    if tmpResourceValue != value:
                        is_member = False
                        break
                    
                    
            if is_member:
                trim = trim_function or self.trim_published_resource
                trimmed_resource = trim(resource, query["fields"])
                headers["collection"] = headers.get("collection", collection)
                headers["id"] = headers.get("id", resource["id"])
                message = {
                    "headers": headers,
                    "data": trimmed_resource
                }
                for client in query["clients"]:
                    try:
                        client.deliver(tornado.escape.json_encode(message))
                    except Exception as exp:
                        self.log.error("Publish failed - {exp}".format(exp = exp))


    # @description: createChannel registers a series of conditions to a channel for later use
    #                 when publishing resources.
    # @input:       conditions is a dictionary of conditions which are matched against resources
    #                 when published.
    #               fields is an array of fields to filter for when publishing.
    # @output:      createChannel returns the channel that the listener should subscribe to.
    def createChannel(self, conditions, collection, fields, client=None):
        for query in self.subscriptions:
            if conditions == query["conditions"] and collection == query["collection"]:
                query["subscribers"] += 1
                query["clients"].append(client)
                return query["channel"]
            
        channel = uuid.uuid4().hex
        self.subscriptions.append({ "channel": channel,
                                    "conditions": conditions,
                                    "fields": fields,
                                    "collection": collection,
                                    "subscribers": 1,
                                    "clients": [client] })
        return channel

    # @description: removeChannel removes a channel from the availible channels
    # @input:       channel is the hex reference to the channel
    # @output:      boolean succes/failure
    def removeChannel(self, channel, client=None):
        to_remove = None
        
        for query in self.subscriptions:
            if query["channel"] == channel:
                query["subscribers"] -= 1
                try:
                    query["clients"].remove(client)
                except KeyError:
                    pass

                if query["subscribers"] == 0:
                    to_remove = query

        if to_remove:
            self.subscriptions.remove(to_remove)
    
    
    # @description: trim_published_resource filters the resource for the requested fields.
    # @input:       resource is a json object corrosponding to the resource in question.
    #               fields are the fields to filter for.
    def trim_published_resource(self, resource, fields):
        result = {}
        if fields == None:
            return resource
        else:
            for field in fields:
                result[field] = resource[field]
            
            return result
    
    
