#!/usr/bin/env python
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
Usage:
  periscoped [options]

Options:
  -l FILE --log=FILE           File to store log information
  -d LEVEL --log-level=LEVEL   Select log verbosity [ERROR, DEBUG, CONSOLE]
  -c FILE --config-file=FILE   File with extra configurations [default: /etc/periscope/unis.cfg]
  -p PORT --port=PORT          Run on PORT
  -r --lookup                  Run UNIS as a lookup service
'''

import falcon
import docopt
import sys
import configparser
import socket
import requests
import functools
import re
import time
import json
import requests
import multiprocessing
import gunicorn.app.base
from periscope import settings 
from urllib.parse import urlparse
from periscope.settings import * #middleware, dbcfg
from periscope.models import Manifest, ObjectDict
from pymongo import MongoClient
from periscope.handlers import * 
from string import Template
from apscheduler.schedulers.background import BackgroundScheduler



class PeriscopeApplication(gunicorn.app.base.BaseApplication):
    
    @property
    def options(self):
        if not hasattr(self, "_options"):
            class DefaultDict(dict):
                def get(self, k, default=None):
                    val = super(DefaultDict, self).get(k, default)
                    return val or default

            tmpOptions = docopt.docopt(__doc__)
            self._options = DefaultDict(settings.DEFAULT_CONFIG)
            tmpConfig = configparser.RawConfigParser(allow_no_value = True)
            tmpConfig.read('/etc/periscope/unis.cfg')
            
            for section in tmpConfig.sections():
                if section.lower() == 'connection':
                    for k, o in tmpConfig.items(section):
                        self._options[k] = {'true': True, 'false': False}.get(o, o)
                        if k in settings.LIST_OPTIONS:
                            self._options[k] = [] if not o else o.split(',')
                    continue
                elif not section in self._options:
                    self._options[section] = {}
                
                for key, option in tmpConfig.items(section):
                    if "{s}.{k}".format(s = section, k = key) in settings.LIST_OPTIONS:
                        if not option:
                            self._options[section][key] = []
                        else:
                            self._options[section][key] = option.split(",")
                    elif option == "true":
                        self._options[section][key] = True
                    elif option == "false":
                        self._options[section][key] = False
                    else:
                        self._options[section][key] = option
            
            self.options["lookup"] = False
            
            for key, option in tmpOptions.items():
                if option is not None:
                    self._options[key.lstrip("--")] = option
        
        return self._options
        
    def registered(self, response, fatal = True):
        if response.error:
            self._log.error("Couldn't connect to Client: ERROR {e}  {b}".format(e = response.error, b = response.body))
            if fatal:
                import sys
                sys.exit()
        else:
            body=json.loads(response.body)
            
    def _report_to_root(self):
        manifests = []
        cursor = self.db["manifests"].find({ "\\$shard": False}, {"_id": False })
        
        for manifest in cursor:
            manifests.append(ObjectDict._from_mongo(manifest))

        service = {
            u"id": u"unis_" + urlparse(self.options['unis']['url']).hostname,
            u"ts": int(time.time() * 1e6),
            u"\$schema": str(SCHEMAS["service"]),
            u"accessPoint": u"%s/" % (self.options['unis']['url']),
            u"name": u"unis_" + urlparse(self.options['unis']['url']).hostname,
            u"status": u"ON",
            u"serviceType": u"ps:tools:unis",
            u"ttl": int(self.options["unis"]["summary_collection_period"]),
            u"communities": self.options["unis"]["communities"],
            u"runningOn": {
                u"href": u"%s/nodes/%s" % (self.options['unis']['url'], socket.gethostname()),
                u"rel": u"full"
            },
            u"properties": {
                #u"summary": manifests,
                u"summary": [{'$shard': False, '$collection': 'paths', 'properties': {}, 'id': '5eba1a133872d96d6451a872', 'ts': 1598137716644555}],
                u"depth": self._depth
            }
        }
        
        for lookup in self.options["unis"]["root_urls"]:
            service_url = lookup + '/register'
            content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
            headers = {"Content-Type" : content_type,
                       "Cache-Control" : "no-cache",
                       "Accept" : MIME['PSJSON'],
                       "Connection" : "close"}

            requests.post(service_url, data=json.dumps(service), headers=headers)

    def load_config(self):
        config = {key: value for key, value in self.server_options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application
        
    def __init__(self, app, server_options=None):
        self.cookie_secret="S19283u182u3j12j3k12n3u12i3nu12i3n12ui3"
        self._depth = 1 if bool(self.options["lookup"]) else 0
        self.db = MongoClient('localhost', 27017).unis_db
        self._ppi_classes = []
        self._log = settings.get_logger(level=self.options['log-level'], filename=self.options['log'])
        handlers = []
        
        self.server_options = server_options or {}
        self.application = app
        
        try:
            for url in settings.SELF_LOOKUP_URLS:
                res = requests.get(url)
                if res.status_code == 200:
                    ref = "http{}://{}:{}".format(
                        's' if self.options["unis_ssl"]["enable"] else '',
                        res.text,
                        self.options['port']
                    )
                    break
            raise Exception("No valid lookup url found")
        except:
            ref = "http{}://{}:{}".format(
                's' if self.options["unis_ssl"]["enable"] else '',
                socket.getfqdn(),
                self.options['port']
            )
            
        self.options['unis']['url'] = self._options['unis']['url'] or ref
        self.options['unis']['ms_url'] = self._options['unis']['ms_url'] or ref
        
        # import and initialize pre/post content processing modules
        for pp in settings.PP_MODULES:
            mod = __import__(pp[0], fromlist=pp[1])
            c = getattr(mod, pp[1])
            if issubclass(c, PPI):
                if not self.options["auth"]["enabled"] and c.pp_type is PPI.PP_TYPES[PPI.PP_AUTH]:
                    pass
                else:
                    self._ppi_classes.append(c())
            else:
                self._log.error("Not a valid PPI class: {name}".format(name = c.__name__))
        
        
        if 'auth' in self.options and self.options["auth"]["enabled"]:
            from periscope.auth import ABACAuthService
            
            self._auth = ABACAuthService(settings.SSL_OPTIONS['certfile'],
                                         settings.SSL_OPTIONS['keyfile'],
                                         settings.AUTH_STORE_DIR,
                                         self.get_db_layer("authNZ",
                                                           "id", "ts", False, 0))
            for auth in settings.AuthResources:
                handlers.append(self.make_simple_handler(**settings.AuthResources[auth]))
        
        for res in settings.Resources:
            if bool(self.options["lookup"]):
                settings.Resources[res]["handler_class"] = "DelegationHandler"
                settings.Resources[res]["allow_delete"] = False
                settings.Resources[res]["allow_put"] = False
                settings.Resources[res]["allow_post"] = False

            app.add_route(settings.Resources[res]["uri_template"], getattr(sys.modules[__name__], settings.Resources[res]["handler_class"])())
        
        for sub in settings.Subscriptions:
            app.add_route(settings.Subscriptions[sub]["uri_template"], getattr(sys.modules[__name__], settings.Subscriptions[sub]["handler_class"])())
            
        app.add_route(settings.getSchema["uri_template"], getattr(sys.modules[__name__], settings.getSchema["handler_class"])())       
        app.add_route(settings.main_handler_settings["uri_template"], getattr(sys.modules[__name__], settings.main_handler_settings["handler_class"])())
        app.add_route(settings.about_handler_settings["uri_template"], getattr(sys.modules[__name__], settings.about_handler_settings["handler_class"])())
        app.add_route(settings.getParent["uri_template"], getattr(sys.modules[__name__], settings.getParent["handler_class"])())
        
        if bool(self.options["lookup"]):
            app.add_route(settings.reg_settings["uri_template"], getattr(sys.modules[__name__], settings.reg_settings["handler_class"])())
        
        app.add_route('/create', CallbackHandler())
        
        if self.options["unis"]["root_urls"]:
            self._report_to_root()
        
        if self.options["unis"]["use_ms"] and not bool(self.options["lookup"]):
            import time
            if self.options["unis_ssl"]["enable"]:
                http_str = "https"
            else:
                http_str = "http"
            #callback = functools.partial(self.registered)
            service = {
                u"id": u"ms_" + socket.gethostname(),
                u"ts": int(time.time() * 1e6),
                u"\$schema": str(SCHEMAS["service"]),
                u"accessPoint": u"%s://%s:%d/" % (http_str, socket.getfqdn(), int(self.options["port"])),
                u"name": u"ms_" + socket.gethostname(),
                u"status": u"ON",
                u"serviceType": u"ps:tools:ms",
                u"ttl": 600,
                u"runningOn": {
                    u"href": u"%s/nodes/%s" % (self.options["unis"]["ms_url"], socket.gethostname()),
                    u"rel": u"full"
                },
                u"properties": {
                    u"configurations": {
                        u"default_collection_size": 10000,
                        u"max_collection_size": 20000
                    },
                    u"summary": {
                        u"metadata": []
                    }
                }
            }
            
            if settings.AUTH_UUID:
                service['properties'].update({"geni": {"slice_uuid": settings.AUTH_UUID}})

            if socket.getfqdn() in self.options['unis']['ms_url']:
                self.db["services"].insert_one(service)
            else:
                service_url = self.options["unis"]["ms_url"]+'/services'
                content_type = MIME['PSJSON'] + '; profile=' + SCHEMAS['service']
                headers = {"Content-Type" : content_type,
                           "Cache-Control" : "no-cache",
                           "Accept" : MIME['PSJSON'],
                           "Connection" : "close"}

                requests.post(service_url, data=json.dumps(service), headers=headers)
        super().__init__()


app = falcon.App(middleware=middleware)

def aggregate_manifests():
    requests.get('http://127.0.0.1:8888/create')

scheduler = BackgroundScheduler()
job = scheduler.add_job(aggregate_manifests, 'interval', seconds=int(settings.DEFAULT_CONFIG["unis"]["summary_collection_period"]))

def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1

def main():
    server_options = {
        'bind': '%s:%s' % ('127.0.0.1', '8888'),
        #'workers': number_of_workers(),
        'reload' : True,
    }

    scheduler.start()

    appPeriscope = PeriscopeApplication(app, server_options)
    appPeriscope.run()

if __name__ == '__main__':
    main()


