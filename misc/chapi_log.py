#----------------------------------------------------------------------
# Copyright (c) 2013-2014 Raytheon BBN Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
#----------------------------------------------------------------------

# Methods to provide standard logging within CHAPI for 
# invocations, errors, exceptions and other information events

# In this way, the handling of CHAPI messages (what level, to what
# files, what format) can be abstracted away from the rest of the code

import logging
import sys
import traceback

SA_LOG_PREFIX = "SA"
MA_LOG_PREFIX = "MA"
CS_LOG_PREFIX = "CS"
PGCH_LOG_PREFIX = "PGCH"
SR_LOG_PREFIX = "SR"
LOG_LOG_PREFIX = "LOG"

# Class just to hold the is_verbose flag from Parameters.py
class CHAPIVerbose(object):
    def __init__(self, verbose=False):
        self.verbose=verbose
    def setVerbose(self, verbose=True):
        self.verbose=verbose
    def isVerbose(self):
        return self.verbose

verboseObj = CHAPIVerbose()

def chapi_get_audit_logger():
    chapi_audit_logger = logging.getLogger('chapi.audit')
    if len(chapi_audit_logger.handlers) == 0:
        logging.debug("No handler for chapi_audit yet")
        if len(logging.getLogger().handlers) == 0:
            chapi_logging_basic_config()
            chapi_audit_logger = logging.getLogger('chapi.audit')
            logging.info("Had no handler for chapi_audit or for the root logger. Did basic config")
        else:
            logging.debug("But there is a handler for the root")
    return chapi_audit_logger

def chapi_get_logger():
    chapi_logger = logging.getLogger('chapi')
    if len(chapi_logger.handlers) == 0 and len(logging.getLogger().handlers) == 0:
        chapi_logging_basic_config()
        chapi_logger = logging.getLogger('chapi')
        logging.info("Had no handler for chapi yet - did basic_config")
    return chapi_logger

def chapi_logging_basic_config(level=logging.INFO):
    if len(logging.getLogger().handlers) > 0:
        logging.debug("Not (re)doing basic config")
        return
    fmt = '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
    logging.basicConfig(level=level,format=fmt,datefmt='%m/%d/%Y %H:%M:%S')

# Generic call for logging CHAPI messages at different levels
def chapi_log(prefix, msg, logging_level, extra=None):
    chapi_logger = chapi_get_logger()
    if isinstance(msg, unicode): msg = msg.encode('utf-8')
    if extra is not None and extra.has_key('user') and extra['user'] is not None and extra['user'].strip() != '':
        msg = "%s: %s" % (extra['user'].strip(), msg)
    chapi_logger.log(logging_level, "%s: %s" % (prefix, msg))

# Log a potentially auditable event
def chapi_audit(prefix, msg, lvl=logging.INFO, extra=None):
    chapi_audit_logger = chapi_get_audit_logger()
    if isinstance(msg, unicode): msg = msg.encode('utf-8')
    if extra is not None and extra.has_key('user') and extra['user'] is not None and extra['user'].strip() != '':
        msg = "%s: %s" % (extra['user'].strip(), msg)
    chapi_audit_logger.log(lvl, "%s: %s" % (prefix, msg), extra=extra)

# Log both to audit log and regular log an event
def chapi_audit_and_log(prefix, msg, lvl=logging.INFO, extra=None):
    chapi_audit(prefix, msg, lvl, extra)
    chapi_log(prefix, msg, lvl, extra)

# Log a CHAPI warning message
def chapi_warn(prefix, msg, extra=None):
    chapi_log(prefix, msg, logging.WARNING, extra)
    chapi_audit(prefix, msg, logging.WARNING, extra)

# Log a CHAPI debug message
def chapi_debug(prefix, msg, extra=None):
    chapi_log(prefix, msg, logging.DEBUG, extra=extra)

# Log a CHAPI error message
def chapi_error(prefix, msg, extra=None):
    chapi_log(prefix, msg, logging.ERROR, extra=extra)
    chapi_audit(prefix, msg, logging.ERROR, extra=extra)

# Log a CHAPI info message
def chapi_info(prefix, msg, extra=None):
    chapi_log(prefix, msg, logging.INFO, extra=extra)

# Log a CHAPI criticial message
def chapi_critical(prefix, msg, extra=None):
    chapi_log(prefix, msg, logging.CRITICAL, extra=extra)
    chapi_audit(prefix, msg, logging.CRITICAL, extra=extra)

# Log a CHAPI exception
def chapi_log_exception(prefix, e, extra=None):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    tb_info = traceback.format_tb(exc_traceback)
    msg = "Exception: %s\n%s" % (e, "".join(tb_info))
    chapi_error(prefix, msg, extra=extra)
    chapi_audit(prefix, msg, logging.ERROR, extra=extra)

# Log an invocation of a method
def chapi_log_invocation(prefix, method, credentials, options, arguments, extra=None):
    msg = "Invoked %s Options %s Arguments %s" % (method, options, arguments)
    # FIXME: Info or debug?
    chapi_logger = chapi_get_logger()
    if verboseObj.isVerbose() and chapi_logger.isEnabledFor(logging.DEBUG):
        chapi_debug(prefix, msg, extra=extra)
    else:
        if len(msg) > 260:
            chapi_info(prefix, msg[:250] + "...", extra=extra)
        else:
            chapi_info(prefix, msg, extra=extra)

    if verboseObj.isVerbose():
        # Send to syslog at INFO level
        chapi_audit(prefix, msg, logging.INFO, extra=extra)

# Log the result of an invocation of a method
def chapi_log_result(prefix, method, result, extra=None):
    msg = "Result from %s: %s" % (method, result)
    # FIXME: Info or debug?
    chapi_logger = chapi_get_logger()
    if verboseObj.isVerbose() and chapi_logger.isEnabledFor(logging.DEBUG):
        chapi_debug(prefix, msg, extra=extra)
    else:
        if len(msg) > 260:
            chapi_info(prefix, msg[:250] + "...", extra=extra)
        else:
            chapi_info(prefix, msg, extra=extra)

    if verboseObj.isVerbose():
        # Send to syslog at INFO level
        chapi_audit(prefix, msg, logging.INFO, extra=extra)

