import argparse, configparser, copy, csv, os, logging, logging.config, io


class ConfigError(Exception): pass

def _expandvar(x, default=None):
    v = os.path.expandvars(x)
    return default if v == x else v

class MultiConfig(object):
    CONFIG_FILE_VAR = "$PYTHON_CONFIG_FILENAME"

    def __init__(self, defaults, desc=None, *, filevar=None, defaultpath=""):
        self.confpath = _expandvar(filevar or self.CONFIG_FILE_VAR, defaultpath)
        self.defaults, self._desc = defaults, (desc or "")
        self.loglevels = [logging.WARN, logging.INFO, logging.DEBUG]

    def _from_file(self, path):
        path = os.path.expanduser(path)
        result, tys = {}, { "true": True, "false": False, "none": None, "": None }
        if path:
            parser = configparser.ConfigParser(allow_no_value=True)
            try: parser.read(path)
            except OSError: pass
            for section,body in parser.items():
                if not body: continue
                result[section] = {}
                for k,v in body.items():
                    result[section][k] = tys.get(v, v)
        return result

    #def _setup_logging(self, filename):
    #    logging.config.fileConfig(filename)

    def _unify(self, old, new):
        ty = type(old)
        if ty is list:
            ty = lambda v: list(csv.reader(io.StringIO(v)))[0]
        result = new if ty is type(None) else ty(new)
        return result

    #def add_loglevel(self, n, v): self.loglevels[n] = v
    def add_loglevel(self, v): self.loglevels.append(v)

    def from_file(self, include_logging=False, general_tag="general"):
        result = copy.deepcopy(self.defaults)
        for section,body in self._from_file(self.confpath).items():
            if section == general_tag:
                [result.__setitem__(k,self._unify(result.get(k, None), v)) for k,v in body.items()]
            else:
                if section not in result: result[section] = {}
                for k,v in body.items():
                    result[section][k] = self._unify(result[section].get(k, None), v)
        if include_logging:
            if 'verbose' in result:
                logging.getLogger().setLevel(self.loglevels[min(result['verbose'], len(self.loglevels)-1)])
            if result.get('logfile', None) is not None:
                logging.config.fileConfig(result['logfile'])
            else:
                logging.basicConfig(format="%(message)s")
        self.args = result
        return result

    def display(self, log):
        if not hasattr(self, "args"): log.error("Cannot display args before parsing, call from_parser or from_file first")
        
        blocks = {}
        for sec,opt in self.args.items():
            if isinstance(opt, dict): blocks[sec] = opt
            else: log.debug(f"{sec:>10}: {opt}")
            
        for sec,opt in blocks.items():
            log.debug(f"[{sec}]")
            [log.debug(f"  {k:>10}: {v}") for k,v in opt.items()]


    def from_parser(self, parsers, *, include_logging=False, general_tag="general"):
        parsers = parsers if isinstance(parsers, list) else [parsers]
        internal = argparse.ArgumentParser(self._desc, parents=parsers, add_help=False)
        internal.add_argument('-c', '--configfile', type=str, help='Path to the program configuration file')
        if include_logging:
            internal.add_argument('--logfile', type=str, help='Path to the logging configuration file')
            internal.add_argument('-v', '--verbose', action='count', default=0, help='Set the log level of the root logger')

        args = internal.parse_args()
        result = copy.deepcopy(self.defaults)
        result.setdefault('version', False)
        for section,body in self._from_file(args.configfile or self.confpath).items():
            if section == general_tag:
                [result.__setitem__(k, self._unify(result.get(k, None),v)) for k,v in body.items()]
            else:
                if section not in result: raise ConfigError(f"Unknown section {section.upper()} in configfile")
                blk = result[section]
                [blk.__setitem__(k, self._unify(blk.get(k, None), v)) for k,v in body.items()]

        for k,v in args.__dict__.items():
            block, path = result, k.split('.')
            for section in path[:-1]:
                if section not in block: raise ConfigError(f"Corrupt defaults for section {section.upper()} in source")
                block = block[section]
            if v is not None and v is not False: block[path[-1]] = v

        if include_logging:
            #logging.getLogger().setLevel(self.loglevels[result['loglevel'] if 'loglevel' in result else 'NOTSET'])
            #if 'logfile' in result: self._setup_logging(result['logfile'])
            logging.getLogger().setLevel(self.loglevels[min(result['verbose'], len(self.loglevels)-1)])
            if 'logfile' in result and result['logfile']: logging.config.fileConfig(result['logfile'])
            else: logging.basicConfig(format="%(message)s")

        self.args = result
        return result
