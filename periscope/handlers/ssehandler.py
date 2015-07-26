#!/usr/bin/env python

import tornado.web
from tornado.httpclient import HTTPError


class SSEHandler(tornado.web.RequestHandler):
    """
    Handles Server-Sent Events (SSE) requests as specified in
    http://dev.w3.org/html5/eventsource/.

    This handlers gives the option to to the user to use SSE or any other
    regular MIME types in the same same handler. If the MINE type of the
    request is 'text/event-stream' by default this handler is going to
    respond by 'text/event-stream' Content-Type.

    Examlpe::

        class MyHandler(SSEHandler):
            def periodic_send_events(self):
                # First check if the client didn't go away
                if self.request.connection.stream.closed():
                    self._periodic_sse.stop()
                    return
                # just print the current server's timestamp to the user
                t = time.time()
                self.write_event("id_%d" % int(t), "message",
                    "time is %d; last event id was %s" %
                    (t, self.get_last_event_id()))

            @tornado.web.asynchronous
            def get(self):
                if self.supports_sse():
                    self._periodic_sse = tornado.ioloop.PeriodicCallback(
                                            self.periodic_send_events, 2000)
                    self._periodic_sse.start( )
                else:
                    self.write("This was not server sent event request")
                    self.finish()

            def post(self):
                # just to show this is a regular request handler
                if self.supports_sse():
                    self.write_event('post','message', self.request.body)
    """

    SSE_MIME = "text/event-stream"
    # Default client connection retry time.
    DEFAULT_RETRY = 5000
    
    def get(self,*args):
        if getattr(self.application, '_ppi_classes', None):
            try:                
                for pp in self.application._ppi_classes:
                    pp.pre_get(None, self.application, self.request,self)
            except Exception, msg:
                self.send_error(400, message=msg)
                return
        
    def get_last_event_id(self):
        """
        Returns the value of the last event id sent to the client or.
        For connection retry, returns Last-Event-ID header field.
        """
        return getattr(self, '_last_event_id', None)

    def supports_sse(self):
        """
        Returen True if 'text/event-stream' was in the HTTP's Accpet field.
        """
        return getattr(self, '_supports_sse', False)

    def write_event(self, event_id=None, event=None, data=None):
        """
        Writes a server sent event to the client. event_id is optional
        unique ID for the event. event is optional event's name.

        At the fist look it might look weird to have all function parameters
        set to None by default. However, the SSE specification does not
        specifiy any required fields so it's completely legal to send nothing!
        """
        # Escape values
        if event_id:
            event_id = tornado.escape.utf8(event_id)
        if event:
            event = tornado.escape.utf8(event)
        if data:
            data = tornado.escape.utf8(data).strip()
        else:
            raise TypeError("data must be defined.")
        # Check data types
        if event_id.find("\n") > -1 or event_id.find("\r") > -1:
            raise TypeError("Event ID cannot have new lines.")
        if event.find("\n") > -1 or event_id.find("\r") > -1:
            raise TypeError("Event cannot have new lines.")
        # Handles multiline data
        data = data.replace("\n", "\ndata:")
        # Construct a message to be sent
        message = ""
        if event_id:
            message += "id:%s\n" % event_id
            self._last_event_id = event_id
        if event:
            message += "event:%s\n" % event
        if data:
            message += "data:%s\n\n" % data
        # write and flush the event to the stream
        self.write(message)
        self.flush()

    def set_retry(self, retry):
        """
        Set the connection retry time for the client in case if the connection
        failed unexpectedly.
        """
        self.write("retry:%d\n\n" % int(retry))
        self.flush()

    def write_heartbeat(self):
        """
        Writes a message that is igonored by the client. This is usefull
        for old proxies not to terminate the HTTP connection unexpectedly.
        See: http://dev.w3.org/html5/eventsource/#notes for more information.
        """
        if self.request.connection.stream.closed():
            return

        self.write(":\n\n")
        self.flush()

    def decide_content_type(self):
        """
        A hook for HTTP content negotiation .
        """
        if self.request.headers.get("Accept", "").find(self.SSE_MIME) > -1:
            return self.SSE_MIME
        else:
            return self.request.headers.get("Accept", None)

    def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        self._transforms = transforms
        try:
            if self.request.method not in self.SUPPORTED_METHODS:
                raise HTTPError(405)
            # If XSRF cookies are turned on, reject form submissions without
            # the proper cookie
            if self.request.method not in ("GET", "HEAD", "OPTIONS") and \
               self.application.settings.get("xsrf_cookies"):
                self.check_xsrf_cookie()
            # Handles Server Sent Events requests
            if self.decide_content_type() == self.SSE_MIME:
                self._supports_sse = True
                self._last_event_id = self.request.headers.get("Last-Event-ID",
                                            None)
                self.set_header("Cache-Control", "no-cache")
                self.set_header("Content-Type", self.SSE_MIME)
                if self.DEFAULT_RETRY:
                    self.set_retry(self.DEFAULT_RETRY)
            else:
                self._supports_sse = False
            self.prepare()
            if not self._finished:
                args = [self.decode_argument(arg) for arg in args]
                kwargs = dict((k, self.decode_argument(v, name=k))
                              for (k, v) in kwargs.iteritems())
                getattr(self, self.request.method.lower())(*args, **kwargs)
                if self._auto_finish and not self._finished:
                    self.finish()
        except Exception, e:
            self._handle_request_exception(e)
