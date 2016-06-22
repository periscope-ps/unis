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
from mock import Mock
from mock import patch
import time
import json

import tornadoredis
import tornado
import tornado.web
import tornado.websocket
import pymongo

from tornado.testing import gen_test

from periscope.handlers.subscriptionhandler import SubscriptionHandler
from periscope.handlers.subscriptionmanager import SubscriptionManager
from periscope.handlers.subscriptionmanager import GetManager
from periscope.handlers import subscriptionmanager
from periscope.test.base import PeriscopeHTTPTestCase

class SubscriptionTest(PeriscopeHTTPTestCase):
    def setUp(self):
        super(SubscriptionTest, self).setUp()
        self.publisher = tornadoredis.Client()

    def get_app(self):
        return tornado.web.Application([('/(?P<resource_type>[^\/]*)$', SubscriptionHandler)])
    
    def get_protocol(self):
        return 'ws'

    @tornado.gen.engine
    def pause(self, timeout, callback):
        self.io_loop.add_timeout(time.time() + timeout, callback)
    
    def test_does_deliver(self):
        _self = self
        data = "{ 'test': 'data'}"

        def on_open(self):
            _self.publisher.publish("1", data)
            
        def on_message(message):
            _self.assertEqual(message, data)
            _self.stop()
            
            
        with patch("periscope.handlers.subscriptionmanager.SubscriptionManager.createChannel") as manager_mock:
            manager_mock.side_effect = ["1"]
            
            tornado.websocket.websocket_connect(
                self.get_url('/test'),
                io_loop = self.io_loop,
                callback = on_open,
                on_message_callback = on_message)
            
            
            connection = self.wait()
            self.assertTrue(manager_mock.called)


    @gen_test
    def test_multiple_subscriptions(self):
        _self = self
        
        def on_open(self):
            pass
                    
        with patch("periscope.handlers.subscriptionmanager.SubscriptionManager.createChannel") as manager_mock:
            manager_mock.side_effect = ["1", "2", "3"]
            
            conn = yield tornado.websocket.websocket_connect(
                self.get_url('/test'),
                io_loop = self.io_loop,
                callback = on_open)
            
            conn.write_message(json.dumps(dict(resourceType = 'test2')))
            conn.write_message(json.dumps(dict(resourceType = 'test3')))
            
            yield tornado.gen.Task(self.pause, 1)
            self.assertEqual(manager_mock.call_count, 3)
            conn.close()

        
                
    @patch.object(SubscriptionHandler, 'listen', mocksigniture=True)
    def test_blank_subscription(self, listen_mock):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = {"tests": None})
        handler = SubscriptionHandler(app, Mock())
        handler._manager = Mock()
        
        # Act
        handler.open()

        # Assert
        self.assertFalse(listen_mock.called)
        self.assertFalse(handler.listening)

    
    @patch.object(SubscriptionHandler, 'listen', mocksigniture=True)
    def test_resource_subscription(self, listen_mock):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = {"tests": None})
        resource_mock = Mock()
        resource_mock.arguments = dict()
        handler = SubscriptionHandler(app, resource_mock)
        handler._manager = Mock()

        # Act
        handler.open(resource_type = "test")

        # Assert
        self.assertTrue(listen_mock.called)
        self.assertEqual(handler._manager.createChannel.call_count, 1)
        self.assertEqual(handler._manager.createChannel.call_args[0][1], "test")


    def test_resource_id_subscription(self):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = {"tests": None})
        resource_mock = Mock()
        resource_mock.arguments = dict()
        handler = SubscriptionHandler(app, resource_mock)
        handler._manager = Mock()
        
        # Act
        handler.open(resource_type = "test", resource_id="1")

        # Assert
        self.assertEqual(handler._manager.createChannel.call_args[0][0], { "id": "1" })
        

    def test_subscription_good_fields(self):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = {"tests": None})
        fields_request = Mock()
        fields_request.arguments = dict(fields = ["name,ts"])
        
        manager_mock = Mock()
        
        handler = SubscriptionHandler(app, fields_request)
        handler._manager = manager_mock
        
        # Act
        handler.open(resource_type = "test")
        
        # Assert
        self.assertEqual(manager_mock.createChannel.call_args[0][2], ["name", "ts"])
        


    def test_subscription_good_query(self):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = {"tests": None})
        query_request = Mock()
        query_request.arguments = dict(query = ['{ "name": "test", "ts": { "gte": 145 } }'])
        handler = SubscriptionHandler(app, query_request)
        
        manager_mock = Mock()
        
        handler._manager = Mock()
        handler.write_message = Mock(side_effects = ValueError)
        handler._manager = manager_mock
        
        # Act
        handler.open(resource_type = "test")
        
        # Assert
        self.assertTrue(manager_mock.createChannel.called)
        self.assertEqual(manager_mock.createChannel.call_args[0][0], { "name": "test", "ts": { "gte": 145 } })
        
        
    def test_subscription_bad_query(self):
        # Arrange
        app = Mock(ui_methods = {}, ui_modules = {}, async_db = { "tests": None})
        query_request = Mock()
        query_request.arguments = dict(query = ["{ name: 'test', ts: { gte: 145 }"])

        manager_mock = Mock()
        
        handler = SubscriptionHandler(app, query_request)
        handler._manager = manager_mock
        handler.write_message = Mock(side_effects = ValueError)
        
        # Act
        handler.open(resource_type = "test")

        # Assert
        self.assertFalse(handler.client)
        self.assertFalse(manager_mock.createChannel.called)


class PublishingTest(PeriscopeHTTPTestCase):
    def get_app(self):
        return tornado.web.Application([])
    

    def test_deep_query(self):
        pass
    
    
    def test_create_channel(self):
        # Arrange
        manager = GetManager()
        manager.trc = Mock()
        
        condition1 = { "id": "test1" }
        condition2 = { "value": 5 }
        condition3 = { "con1": condition1, "con2": condition2 }

        # Act

        # Test single append
        self.assertTrue(manager.createChannel(conditions = condition1, collection = "test", fields = None))
        self.assertEqual(len(manager.subscriptions), 1)

        # Test new append
        self.assertTrue(manager.createChannel(conditions = condition3, collection = "test", fields = None))
        self.assertEqual(len(manager.subscriptions), 2)

        # Test same append
        self.assertTrue(manager.createChannel(conditions = condition1, collection = "test", fields = None))
        self.assertEqual(len(manager.subscriptions), 2)

        # Test different collection
        self.assertTrue(manager.createChannel(conditions = condition1, collection = "test2", fields = None))
        self.assertEqual(len(manager.subscriptions), 3)
        
        manager.subscriptions = []

    
    def test_remove_channel(self):
        # Arrange
        manager = GetManager()
        manager.trc = Mock()
        
        condition1 = { "id": "test1" }
        condition2 = { "value": 5 }
        condition3 = { "con1": condition1, "con2": condition2 }

        channel1 = manager.createChannel(conditions = condition1, collection = "test", fields = None)
        channel2 = manager.createChannel(conditions = condition2, collection = "test", fields = None)
        channel3 = manager.createChannel(conditions = condition2, collection = "test", fields = None)

        # Act
        self.assertEqual(channel2, channel3)
        self.assertEqual(manager.subscriptions[1]["subscribers"], 2)

        manager.removeChannel(channel1)
        channel1_exists = False
        for channel in manager.subscriptions:
            if channel["channel"] == channel1:
                channel1_exists = True
        self.assertFalse(channel1_exists)

        manager.removeChannel(channel2)
        self.assertEqual(manager.subscriptions[0]["subscribers"], 1)

        manager.removeChannel(channel2)

        channel2_exists = False
        for channel in manager.subscriptions:
            if channel["channel"] == channel2:
                channel2_exists = True
        self.assertFalse(channel2_exists)

        manager.subscriptions = []


    def test_query_consistency(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        manager = GetManager()
        manager.trc = Mock()
        
        condition1 = { "id": "test1" }
        fields = [ "name", "file" ]
        channel1 = manager.createChannel(conditions = condition1, collection = "test", fields = fields)
        
        # Act
        self.assertEqual(manager.subscriptions[0]["channel"], channel1)
        self.assertEqual(manager.subscriptions[0]["conditions"], condition1)
        self.assertEqual(manager.subscriptions[0]["fields"], fields)
        self.assertEqual(manager.subscriptions[0]["collection"], "test")
        
        manager.subscriptions = []
        
        
    def test_publish_basic(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock

        condition1 = { "id": "test1" }
        condition2 = { "id": "test2" }

        resource = { "id": "test1", "data": "stuff" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)
        channel2 = manager.createChannel(conditions = condition1, collection = "test_coll2", fields = None)
        channel3 = manager.createChannel(conditions = condition2, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 1)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), resource)

        manager.subscriptions = []


    def test_publish_gt(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": { "gt": 5 } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 1)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), resource1)

        manager.subscriptions = []

        
    def test_publish_gte(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": { "gte": 5 } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        resource3 = { "id": 3, "data": "stuff_more" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")
        manager.publish(resource3, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 2)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[0][0][1]), resource1)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[1][0][1]), resource2)

        manager.subscriptions = []


    def test_publish_lt(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": { "lt": 5 } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        resource3 = { "id": 3, "data": "stuff_more" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")
        manager.publish(resource3, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 1)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), resource3)

        manager.subscriptions = []
        
        
    def test_publish_lte(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": { "lte": 5 } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        resource3 = { "id": 3, "data": "stuff_more" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")
        manager.publish(resource3, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 2)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[0][0][1]), resource2)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[1][0][1]), resource3)

        manager.subscriptions = []


    def test_publish_equal(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock

        condition1 = { "id": { "equal": "test1" } }

        resource = { "id": "test1", "data": "stuff" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)
        channel2 = manager.createChannel(conditions = condition1, collection = "test_coll2", fields = None)

        # Act
        manager.publish(resource, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 1)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), resource)

        manager.subscriptions = []

        
    def test_publish_reg(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "data": { "reg": "ff_a" } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        resource3 = { "id": 3, "data": "stuff_more" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")
        manager.publish(resource3, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 1)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), resource2)
        
        manager.subscriptions = []

        
    def test_publish_in(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": { "in": [ 10, 3 ] } }
        
        resource1 = { "id": 10, "data": "stuff" }
        resource2 = { "id": 5, "data": "stuff_also" }
        resource3 = { "id": 3, "data": "stuff_more" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test_coll1", fields = None)

        # Act
        manager.publish(resource1, "test_coll1")
        manager.publish(resource2, "test_coll1")
        manager.publish(resource3, "test_coll1")


        # Assert
        self.assertEqual(redis_mock.publish.call_count, 2)
        self.assertEqual(redis_mock.publish.call_args[0][0], channel1)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[0][0][1]), resource1)
        self.assertEqual(json.loads(redis_mock.publish.call_args_list[1][0][1]), resource3)

        manager.subscriptions = []

        
    def test_publish_trim(self):
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": "test1" }
        fields = [ "name", "file" ]
        
        resource = { "id": "test1", "name": "test1", "file": "AnnaK", "value": "Tols" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test", fields = fields)
        
        # Act
        manager.publish(resource, "test")

        # Assert
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), { "name": "test1", "file": "AnnaK" })

        manager.subscriptions = []

        
    def test_callback_trim(self):
        def do_trim(resource, fields):
            return { "name": resource["name"], "file": resource["file"] }
        
        # Arrange
        subscriptionmanager.__manager__ = None
        redis_mock = Mock()
        publish_mock = Mock()
        redis_mock.attach_mock(publish_mock, "publish")
        manager = GetManager()
        manager.trc = redis_mock
        
        condition1 = { "id": "test1" }
        
        resource = { "id": "test1", "name": "test1", "file": "AnnaK", "value": "Tols" }
        
        channel1 = manager.createChannel(conditions = condition1, collection = "test", fields = None)
        
        # Act
        manager.publish(resource, "test", do_trim)
        
        # Assert
        self.assertTrue(redis_mock.publish.called)
        self.assertEqual(json.loads(redis_mock.publish.call_args[0][1]), { "name": "test1", "file": "AnnaK" })
        
        manager.subscriptions = []
