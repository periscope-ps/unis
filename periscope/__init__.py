import falcon
from periscope.settings import middleware, dbcfg
from periscope.handlers.abouthandler import *
from periscope.handlers.mainhandler import *
from periscope.handlers.resourcehandler import *
from periscope.handlers.subscriptionhandler import *

app = falcon.API(middleware=middleware)

app.add_route('/', MainHandler())
app.add_route('/about', AboutHandler())
app.add_route('/subscribe', SubscriptionHandler())

app.add_route('/ports', ResourceHandler())
app.add_route('/links', ResourceHandler())
app.add_route('/nodes', ResourceHandler())
app.add_route('/services', ResourceHandler())
app.add_route('/paths', ResourceHandler())
app.add_route('/networks', ResourceHandler())
app.add_route('/domains', ResourceHandler())
app.add_route('/topologies', ResourceHandler())
app.add_route('/metadata', ResourceHandler())
app.add_route('/measurements', ResourceHandler())
app.add_route('/exnodes', ResourceHandler())
app.add_route('/extents', ResourceHandler())

