

import sys
import os
import inspect
import logging
import traceback

import xml.dom.minidom
from xml.etree import ElementTree as et

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
rootLogger = logging.getLogger()            

h1 = logging.StreamHandler(sys.stdout)
h1_formatter = logging.Formatter(
        "%(levelname)s: %(message)s")
h1.setFormatter(h1_formatter)
f1 = SingleLevelFilter(logging.INFO, False)
h1.addFilter(f1)
rootLogger.addHandler(h1)

h2 = logging.StreamHandler(sys.stderr)
h2_formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(funcName)s: %(message)s")
h2.setFormatter(h2_formatter)
f2 = SingleLevelFilter(logging.INFO, True)
h2.addFilter(f2)
rootLogger.addHandler(h2)

# rootLogger.setLevel(logging.INFO)
rootLogger.setLevel(logging.DEBUG)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))) + "/Modules")
import memUsage

def f(elem, level=-1):
    if elem.nodeName == "Title":
        yield elem.childNodes[0].nodeValue, level
    elif elem.nodeType == elem.ELEMENT_NODE:
        for child in elem.childNodes:
            for e, l in f(child, level + 1):
                yield e, l

def updateDLM(reservedMem):
    '''
    Update the dynamic link managers reserved memory.
    reservedMem - Gigabytes
    '''
    try:
        xmlPath = "~/Library/Preferences/Adobe/dynamiclinkmanager/2.0/memorybalancercs55v2.xml"
        xmlPath = os.path.expanduser(xmlPath)
        xmlData = open(xmlPath)
        doc = xml.dom.minidom.parse(xmlData)
        node = doc.documentElement
    
        memNode = None
        for n in node.getElementsByTagName('key'):
            name = n.firstChild.nodeValue
            if name == "memorytouseforotherapplications":
                memNode = n

        reservedMem = reservedMem * 1024 * 1024 * 1024
        logging.info("DLM Reserved Memory (Bytes): %s" % reservedMem)
        memNode.parentNode.childNodes[3].firstChild.nodeValue = reservedMem
    
        xmlOutPath = open("/tmp/test.xml", 'w')
        xmlFile = open(xmlPath, 'w')
        doc.writexml(xmlFile)
        return True
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error("Unable to update dynamiclinkmanager")
        print repr(traceback.extract_tb(exc_traceback))
        print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))


def setupAEMemory():
    '''
    Setup After Effects Memory Usage
    We want after effects to use 2/3 of available memory.
    Return a dict of:
        Fatal Error - error
        AE Available - aeAvailMem
        AE Reserved - aeResvMem
        Enable Mult Procs - multProcs
    '''
    mem = memUsage.getMemUsage()
    # Mem is supplied in Megabytes, thus the 1024 conversions
    d = {}
    d['error'] = False
    d['totalMem'] = mem['total']
    d['availMem'] = mem['free'] + mem['inactive']
    d['actMem'] = mem['wired'] + mem['active']
    d['aeAvailMem'] = int(float(d['availMem']) * (float(2)/float(3)))
    d['aeResvMem'] = d['availMem'] - d['aeAvailMem']
    d['multProcs'] = False

    msg = "Memory Usage\n\tSystem Total: %sGB\n\tSystem Active: %sGB\n\tSystem Available: %sGB\n\tAE Avail: %sGB\n\tAE Reserved: %sGB"
    msg = msg % (d['totalMem']/1024, d['actMem']/1024, d['availMem']/1024, d['aeAvailMem']/1024, d['aeResvMem']/1024)
    logging.info(msg)

    # Update DLM if we have enough memory to render
    if d['aeAvailMem']/1024 < 2:
        logging.error("Error: Not enough memory free")
        d['error'] = True
    else:
        if not updateDLM(d['aeResvMem']):
            d['error'] = True
    
    # Now check if we need to enable multiprocessing
    # Node must have more than 4GB of RAM available for AE
    if d['aeAvailMem']/1024 > 4:
        d['multProcs'] = True
    
    return d

print setupAEMemory()