# Submit Transcoder - Preflight
# Author: Brennan Chapman
# Date: 7/12/2011
#
# Check that the worker is ready to render this job
#   + Make sure blender is installed
#   + Make sure QTCoffee is installed

import os, subprocess

BLENDERLOCATION = "/Applications/blender.app"
QTCOFFEELOCATION = "/usr/local/bin/catmovie"

class PreFlight:
    def __init__(self, logger):
        self.result = False
        self.logger = logger
        
        self.logger.info("Running Transcoder PreFlight...")
    
    def check(self):
        # Run the checks
        if (self.checkBlender()): self.result = True
        if (self.checkQTCoffee()): self.result = True
        
        
        # Report the outcome
        if (self.result):
            self.logger.info("Transcoder PreFlight Sucess!")
        else:
            self.logger.info("Transcoder PreFlight Failed!")
        # Return the final result
        return self.result
    
    # ------------------------------------------------------
    # Checks
    # ------------------------------------------------------
    
    def checkBlender(self):
        result = False
        # Make sure the app exists
        if (os.path.exists(BLENDERLOCATION)):
            # Check it's version using mdls
            cmd = 'mdls -name kMDItemVersion -raw \'' +  BLENDERLOCATION + '\''
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            version = p.stdout.readlines()
            
            self.logger.info("+ Blender(" + ''.join(version) + ") Installed.")
            result = True
        else:
            self.logger.error("X Blender not installed.")
        
        return result
    
    def checkQTCoffee(self):
        result = False
        # Make sure the app exists
        if (os.path.exists(QTCOFFEELOCATION)):
            self.logger.info("+ QTCoffee Installed.")
            result = True
        else:
            self.logger.info("X QTCoffee not installed.")
        
        return result
            
        
        
        
        
        
        
        
        