#!/usr/bin/python

'''
Path Convert
Author: Brennan Chapman
Date: 3/18/2012

Purpose:
    Convert render paths to a different drive location
    for rendering using a background user.
'''

# --------------------------------------------------------

ConfigPath = "~/.renderMounts"

# --------------------------------------------------------

import os
import logging
from defaultLogging import *

# logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)

def replacePath(path, setting, reverse=False):
    result = path
    if reverse:
        result = path.replace(setting['bgMount'], setting['guiMount'])
    else:
        result = path.replace(setting['guiMount'], setting['bgMount'])
    return result

def convertList(lst, config=None, reverse=False):
    
    if not config:
        config = readConfig()
    
    if config:
        for setting in config:
            for index, item in enumerate(lst):
                if setting['guiMount'] in item or setting['bgMount'] in item:
                    lst[index] = replacePath(item, setting, reverse)
                    logger.debug("Updating list item:\n---> %s -> %s" % (item, lst[index]))

    return lst

def convertDict(pkg, config=None, reverse=False):
    
    if not config:
        config = readConfig()
    
    logging.debug("config: %s" % config)
    if config:
        for setting in config:
            for key, value in pkg.items():
                    if type(value) == str:
                        if setting['guiMount'] in value or setting['bgMount'] in value:
                            pkg[key] = replacePath(value, setting, reverse)
                            logger.debug("Updating key: %s\n---> %s -> %s" % (key, value, pkg[key]))
                    elif isinstance(value, dict):
                        pkg[key] = convertDict(value)
                    elif isinstance(value, list):
                        logger.debug("Found list at key: %s" % key)
                        pkg[key] = convertList(value)
                    else:
                        logger.debug("Skipping value %s" % value)

    return pkg

def readConfig():
    '''
    Read the configuration from the .renderMount files.
    Read them into an array of dictionaries.
        URL
        guiMount
        bgMount
    '''

    config = []

    path = os.path.expanduser(ConfigPath)
    if os.path.exists(path):
        f = open(path, 'r')
        lines = f.readlines()
        for line in lines:
            if not line.startswith("#"):
                data = line.replace("\n","").split(",")
                if len(data) != 3:
                    print "Invalid mount config:\n\t%s" % line
                else:
                    mount = {}
                    mount['URL'] = data[0]
                    mount['guiMount'] = data[1]
                    mount['bgMount'] = data[2]
                    config.append(mount)

        return config
    else:
        return False