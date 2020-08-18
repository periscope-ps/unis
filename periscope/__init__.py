import falcon
from periscope.settings import middleware, dbcfg
from periscope.handlers.abouthandler import *
from periscope.handlers.mainhandler import *
from periscope.handlers.resourcehandler import *
from periscope.handlers.eventshandler import *
from periscope.handlers.datahandler import *
from periscope.handlers.subscriptionhandler import *
from periscope.handlers.collectionhandler import *
from periscope.handlers.exnodehandler import *

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
app.add_route('/exnodes', ExnodeHandler())
app.add_route('/extents', ResourceHandler())
app.add_route('/events', EventsHandler())
app.add_route('/data', DataHandler())
app.add_route('/topologies', CollectionHandler())

app.add_route('/ports/{res_id}', ResourceHandler())
app.add_route('/links/{res_id}', ResourceHandler())
app.add_route('/nodes/{res_id}', ResourceHandler())
app.add_route('/services/{res_id}', ResourceHandler())
app.add_route('/paths/{res_id}', ResourceHandler())
app.add_route('/networks/{res_id}', ResourceHandler())
app.add_route('/domains/{res_id}', ResourceHandler())
app.add_route('/topologies/{res_id}', ResourceHandler())
app.add_route('/metadata/{res_id}', ResourceHandler())
app.add_route('/measurements/{res_id}', ResourceHandler())
app.add_route('/exnodes/{res_id}', ExnodeHandler())
app.add_route('/extents/{res_id}', ResourceHandler())
app.add_route('/events/{res_id}', EventsHandler())
app.add_route('/data/{res_id}', DataHandler())

