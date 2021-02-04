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
    
    def supports_sse(self):
        """
        Returen True if 'text/event-stream' was in the HTTP's Accpet field.
        """
        return getattr(self, '_supports_sse', False)

    def get(self,*args):
        if getattr(self.application, '_ppi_classes', None):
            try:
                for pp in self.application._ppi_classes:
                    pp.pre_get(None, self.application, self.request,self)
            except Exception as msg:
                self.send_error(400, message=msg)
                return

    def set_retry(self, retry):
        """
        Set the connection retry time for the client in case if the connection
        failed unexpectedly.
        """
        self.write("retry:%d\n\n" % int(retry))
        self.flush()

    def decide_content_type(self):
        """
        A hook for HTTP content negotiation .
        """
        if self.request.headers.get("Accept", "").find(self.SSE_MIME) > -1:
            return self.SSE_MIME
        else:
            return self.request.headers.get("Accept", None)

    async def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        try:
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
            return await super()._execute(transforms, *args, **kwargs)
        except Exception as e:
            self._handle_request_exception(e)
