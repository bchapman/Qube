#!/usr/bin/python

'''
Default logging setup

To Use:
    Place this line at the beginning of your script:
        from defaultLogging import *
    Then decide what level of logging to use:
        logger.setLevel(logging.INFO)
        logger.setLevel(logging.DEBUG)
        etc...

'''

import sys
import logging

class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno != self.passlevel)
        else:
            return (record.levelno == self.passlevel)

'''
Set the root logging settings
'''
logger = logging.getLogger(__name__)            

h1 = logging.StreamHandler(sys.stdout)
h1_formatter = logging.Formatter(
        "%(levelname)s: %(message)s")
h1.setFormatter(h1_formatter)
f1 = SingleLevelFilter(logging.INFO, False)
h1.addFilter(f1)
logger.addHandler(h1)

h2 = logging.StreamHandler(sys.stderr)
h2_formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(funcName)s: %(message)s")
h2.setFormatter(h2_formatter)
f2 = SingleLevelFilter(logging.INFO, True)
h2.addFilter(f2)
logger.addHandler(h2)