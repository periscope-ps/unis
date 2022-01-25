import argparse, configparser, copy, os, logging, logging.config
from collections import namedtuple


Argument = namedtuple('Argument', ['short', 'long', 'default', 'ty', 'help'])
def _expandvar(x, default):
    v = os.path.expandvars(x)
    return default if v == x else v

def from_template(template, desc=None, *,
                  filevar=None,
                  include_logging=False,
                  general_tag="general"):
    defaults = {}
    for _,l,d,_,_ in template:
        block = defaults
        for p in l.lstrip('-').split('.')[:-1]:
            block = block.setdefault(p, {})
        block[l.lstrip('-').split('.')[-1]] = d
    config = MultiConfig(defaults, desc, filevar=filevar)
    parser = argparse.ArgumentParser()
    for s,l,d,ty,h in template:
        flags = [s, l] if s else [l]
        if ty is list: parser.add_argument(*flags, nargs='+', help=h)
        elif ty is bool: parser.add_argument(*flags, action='store_true', help=h)
        else: parser.add_argument(*flags, type=ty, help=h)
    return config.from_parser(parser, include_logging=include_logging, general_tag=general_tag)

class MultiConfig(object):
    CONFIG_FILE_VAR = "$PYTHON_CONFIG_FILENAME"

    def __init__(self, defaults, desc=None, *, filevar=None):
        self.CONFIG_FILE_VAR = filevar or self.CONFIG_FILE_VAR
        self.defaults, self._desc = defaults, (desc or "")
        self.loglevels = {'NOTSET': logging.NOTSET, 'ERROR': logging.ERROR,
                          'WARN': logging.WARNING, 'INFO': logging.INFO,
                          'DEBUG': logging.DEBUG}

    def _from_file(self, path):
        result, tys = {}, { "true": True, "false": False, "none": None, "": None }
        if path:
            parser = configparser.ConfigParser(allow_no_value=True)
            try:
                parser.read(path)
                for section,body in parser.items():
                    result[section] = {}
                    for k,v in body.items():
                        result[section][k] = tys.get(v, v)
            except OSError: pass
        return result

    def _setup_logging(self, level, filename):
        levels = sorted([v for v in self.loglevels.values()], reverse=True)
        level = levels[min(level, len(levels) - 1)]
        if filename: logging.config.fileConfig(filename)
        else: logging.getLogger().setLevel(level)
        return level

    def add_loglevel(self, n, v): self.loglevels[n] = v

    def from_file(self, include_logging=False, general_tag="general"):
        result = copy.deepcopy(self.defaults)
        filepath = _expandvar(self.CONFIG_FILE_VAR, "")
        for section,body in self._from_file(filepath).items():
            if section not in result: result[section] = {k:v for k,v in body.items()}
            if section == general_tag: [result.__setitem__(k,v) for k,v in body.items()]
            else: [result[section].__setitem__(k,v) for k,v in body.items()]
        if include_logging:
            self._setup_logging(0, result.get('logfile', None))
        return result

    def from_parser(self, parsers, *, include_logging=False, general_tag="general"):
        parsers = parsers if isinstance(parsers, list) else [parsers]
        internal = argparse.ArgumentParser(description=self._desc, parents=parsers, add_help=False)
        internal.add_argument('-c', '--configfile', type=str, help='Path to the program configuration file')
        if include_logging:
            internal.add_argument('--logfile', type=str, help='Path to the logging configuration file')
            internal.add_argument('-v', '--verbose', action='count', default=0, help="Set verbosity of the root logger")

        args = internal.parse_args()
        filepath = args.configfile or _expandvar(self.CONFIG_FILE_VAR, "")
        result = copy.deepcopy(self.defaults)
        for section,body in self._from_file(filepath).items():
            if section not in result: result[section] = {}
            if section == general_tag: [result.__setitem__(k, v) for k,v in body.items()]
            else: [result[section].__setitem__(k, v) for k,v in body.items()]
        for k,v in args.__dict__.items():
            block, path = result, k.split('.')
            for section in path[:-1]:
                if section not in block: block[section] = {}
                block = block[section]
            if v is not None: block[path[-1]] = v

        if include_logging:
            result['verbose'] = self._setup_logging(result['verbose'], result.get('logfile', None))
        return result
