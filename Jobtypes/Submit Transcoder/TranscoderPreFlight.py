'''
Submit Transcoder - Preflight
Author: Brennan Chapman
Date: 8/18/2011

Check that the worker is ready to render this job
  + Make sure blender is installed
  + Make sure QTCoffee is installed
'''

import os, subprocess
import logging

BLENDERLOCATION = "/Applications/blender.app"
QTCOFFEELOCATION = "/usr/local/bin/catmovie"

''' Setup the logger. '''
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def run():
    logger.info("Running Transcoder PreFlight...")

    result = False
    if (checkBlender()): result = True
    if (checkQTCoffee()): result = True
    
    if (result):
        logger.info("Transcoder PreFlight Sucess!")
    else:
        logger.info("Transcoder PreFlight Failed!")

    return result

'''
Checks
'''
def checkBlender():
    '''
    Make sure blender exists on the worker.
    Also, print out the version info.
    '''
    
    result = False
    if (os.path.exists(BLENDERLOCATION)):
        # Check it's version using mdls
        cmd = 'mdls -name kMDItemVersion -raw \'' +  BLENDERLOCATION + '\''
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        version = p.stdout.readlines()
        
        logger.info("+ Blender(" + ''.join(version) + ") Installed.")
        result = True
    else:
        logger.error("- Blender not installed.")
    
    return result

def checkQTCoffee():
    '''
    Make sure QT exists on the worker.
    '''
    
    result = False
    if (os.path.exists(QTCOFFEELOCATION)):
        logger.info("+ QTCoffee Installed.")
        result = True
    else:
        logger.info("- QTCoffee not installed.")
    
    return result
        
    
    
        
        
        
        
        
        