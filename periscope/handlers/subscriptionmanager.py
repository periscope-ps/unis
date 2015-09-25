#!/usr/bin/env python

import json
import tornadoredis
import uuid
import tornado.web

from netlogger import nllog

__manager__ = None

def GetManager():
    global __manager__
    
    if not __manager__:
        __manager__ = SubscriptionManager()

    return __manager__


class SubscriptionManager(nllog.DoesLogging):
    def __init__(self):
        global __manager__

        nllog.DoesLogging.__init__(self)

        self.trc = tornadoredis.Client()
        self.subscriptions = []

        self.trc.connect()

        if __manager__:
            self.log.warn("SubscriptionManager: Multiple instantiations of singleton SubscriptionManager")


    # @description: publish informs all remote subscribers that a change has been
    #               made to the provided resource.
    # @input:       resource is a json object corrosponding to the resource in question.
    #               trim_function is an optional argument that overrides any previous
    #                 filter on the subscription and replaces them with a custom filter.
    def publish(self, resource, collection = None, trim_function = None):
        for query in self.subscriptions:
            is_member = True
            tmpConditions = query["conditions"]
            
            if "collection" in query and query["collection"] != collection:
                continue
            
            for condition, value in tmpConditions.iteritems():
                if condition not in resource or resource[condition] != value:
                    is_member = False
                    break
                
            if is_member:
                trim = trim_function or self.trim_published_resource
                trimmed_resource = trim(resource, query["fields"])
                self.trc.publish(str(query["channel"]), tornado.escape.json_encode(trimmed_resource))
    

    # @description: createChannel registers a series of conditions to a channel for later use
    #                 when publishing resources.
    # @input:       conditions is a dictionary of conditions which are matched against resources
    #                 when published.
    #               fields is an array of fields to filter for when publishing.
    # @output:      createChannel returns the channel that the listener should subscribe to.
    def createChannel(self, conditions, collection, fields):
        for query in self.subscriptions:
            if conditions == query["conditions"] and collection == query["collection"]:
                query["subscribers"] += 1
                return query["channel"]
            
        channel = uuid.uuid4().hex
        self.subscriptions.append({ "channel": channel, "conditions": conditions, "fields": fields, "collection": collection, "subscribers": 1 })
        return channel

    # @description: removeChannel removes a channel from the availible channels
    # @input:       channel is the hex reference to the channel
    # @output:      boolean succes/failure
    def removeChannel(self, channel):
        to_remove = None
        
        for query in self.subscriptions:
            if query["channel"] == channel:
                query["subscribers"] -= 1
                
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
    
    
