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

from periscope import settings
import docopt
import configparser

class BaseHandler(object):
        
    def __init__(self):
    
      self.log = settings.get_logger(level=self.options['log-level'], filename=self.options['log'])
      
    @property
    def options(self):
        if not hasattr(self, "_options"):
            class DefaultDict(dict):
                def get(self, k, default=None):
                    val = super(DefaultDict, self).get(k, default)
                    return val or default

            #tmpOptions = docopt.docopt(__doc__)
            self._options = DefaultDict(settings.DEFAULT_CONFIG)
            tmpConfig = configparser.RawConfigParser(allow_no_value = True)
            tmpConfig.read("/etc/periscope/unis.cfg")
            
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
            
            #for key, option in tmpOptions.items():
            #    if option is not None:
            #        self._options[key.lstrip("--")] = option
        
        return self._options
