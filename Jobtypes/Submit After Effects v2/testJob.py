#!/usr/bin/python


import os
import sys
import logging
import time

if 'QBDIR' in os.environ:
    sys.path.append('%s/api/python' % os.environ['QBDIR'])
elif os.uname()[0] == 'Darwin':
    sys.path.append('/Applications/pfx/qube/api/python')
else:
    sys.path.append('/usr/local/pfx/qube/api/python')
sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.append('../../Modules')
import sequenceTools

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

rootLogger.setLevel(logging.DEBUG)

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)

def splitPath(inputPath):
    '''
    Split an input path into:
        Folder
        File Name
        File Extension
    '''
    # logger.debug('Splitting Path: ' + str(locals()))
    folder, fullName = os.path.split(inputPath)
    name, extension = os.path.splitext(fullName)

    return folder + '/', name, extension

def testISJob():
    # Set basic job properties
    job = {}
    job['name'] = 'Test After Effects v2'
    job['cpus'] = 50
    job['prototype'] = "Submit After Effects v2"
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1+'
    job['flagsstring'] = 'auto_wrangling'
    job['hosts'] = 'Elevate-bchapman'
    job['priority'] = 50
    job['hostorder'] = '+host.processors.avail'
    job['retrywork'] = 3
    job['retrysubjob'] = 3
    
    
    pkg = {}
    pkg['renderProjectPath'] = "/Volumes/theGrill/Staff-Directories/Brennan/Testing/AESubmitv2/testComp.aep"
    pkg['rqIndex'] = 1
    job['package'] = pkg
    
    agenda = qb.genchunks(10, '1-199')
    job['agenda'] = agenda

    logger.info(job)
    print qb.submit([job])
    qb.archivejob('testISJob.qja', job)

def testMovieJob():
    # Set basic job properties
    job = {}
    job['name'] = 'Test After Effects v2'
    job['cpus'] = 1
    job['requirements'] = ''
    job['prototype'] = "Submit After Effects v2"
    job['reservations'] = 'host.processors=1+'
    job['flagsstring'] = 'auto_wrangling'
    job['hosts'] = ''
    job['priority'] = 50
    job['hostorder'] = '+host.processors.avail'
    job['retrywork'] = 3
    job['retrysubjob'] = 3

    pkg = {}
    pkg['renderProjectPath'] = "/Volumes/theGrill/Staff-Directories/Brennan/Testing/AESubmitv2/testComp.aep"
    pkg['rqIndex'] = 2
    job['package'] = pkg

    agenda = qb.genchunks(200, '0-199')
    job['agenda'] = agenda

    logger.info(job)
    print qb.submit([job])
    # qb.archivejob('testMovieJob.qja', job)

def testJrBSJob():
    # Set basic job properties
    job = {}
    job['name'] = 'Test After Effects v2'
    job['cpus'] = 50
    job['prototype'] = "Submit After Effects v2"
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1+'
    job['flagsstring'] = 'auto_wrangling'
    job['hosts'] = ''
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'
    job['retrywork'] = 3
    job['retrysubjob'] = 3

    pkg = {}
    pkg['renderProjectPath'] = "/Volumes/theGrill/Staff-Directories/Brennan/Testing/AESubmitv2/testBSJr.aep"
    pkg['rqIndex'] = 1
    job['package'] = pkg

    agenda = qb.genchunks(10, '1-199')
    job['agenda'] = agenda

    logger.info(job)
    print qb.submit([job])
    qb.archivejob('testISJob.qja', job)

def testKidsBSJob():
    # Set basic job properties
    job = {}
    job['name'] = 'Test After Effects v2'
    job['cpus'] = 50
    job['prototype'] = "Submit After Effects v2"
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1+'
    job['flagsstring'] = 'auto_wrangling'
    job['hosts'] = ''
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'
    job['retrywork'] = 3
    job['retrysubjob'] = 3

    pkg = {}
    pkg['renderProjectPath'] = "/Volumes/theGrill/Staff-Directories/Brennan/Testing/AESubmitv2/POC_BS_L2.aep"
    pkg['rqIndex'] = 1
    job['package'] = pkg

    agenda = qb.genchunks(10, '0-7422')
    job['agenda'] = agenda

    logger.info(job)
    print qb.submit([job])
    qb.archivejob('testISJob.qja', job)

testISJob()
# testMovieJob()
# testJrBSJob()
# testKidsBSJob()
