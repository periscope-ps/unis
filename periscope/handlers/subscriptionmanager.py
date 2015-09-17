#!/usr/bin/env python

import json
import tornadoredis
import uuid
import tornado.web

__trc__           = tornadoredis.Client()
__subscriptions__ = []

__trc__.connect()

class SubscriptionManager(object):

    # @description: publish informs all remote subscribers that a change has been
    #               made to the provided resource.
    # @input:       resource is a json object corrosponding to the resource in question.
    #               trim_function is an optional argument that overrides any previous
    #                 filter on the subscription and replaces them with a custom filter.
    def publish(self, resource, collection = None, trim_function = None):
        global __subscriptions__
        global __trc__
        
        for query in __subscriptions__:
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
                __trc__.publish(str(query["channel"]), tornado.escape.json_encode(trimmed_resource))
    

    # @description: createChannel registers a series of conditions to a channel for later use
    #                 when publishing resources.
    # @input:       conditions is a dictionary of conditions which are matched against resources
    #                 when published.
    #               fields is an array of fields to filter for when publishing.
    # @output:      createChannel returns the channel that the listener should subscribe to.
    def createChannel(self, conditions, collection, fields):
        global __subsciptions__

        for query in __subscriptions__:
            if conditions == query["conditions"] and collection == query["collection"]:
                return query["channel"]
            
        channel = uuid.uuid4().hex
        print("Subscription added[{collection}]: {query}".format(collection = collection, query = conditions))
        __subscriptions__.append({ "channel": channel, "conditions": conditions, "fields": fields, "collection": collection })
        return channel
    
    
    
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
    
    
