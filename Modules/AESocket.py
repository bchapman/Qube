'''
After Effects Socket Communications Class
Launches and communicates with an After Effects process through a socket.

Author: Brennan Chapman
Version: 1.1

Basic Use:
launchAERender()
    Start the aerender daemon
runScript(scriptString, scriptName)
    Send a script for aerender to run, and return the result.
terminateConnection()
    Shutdown aerender
    FUTURE: Ensure any related aerendercore processes
    are shutdown.
'''
AERENDER = "\"/Applications/Adobe After Effects CS5.5/aerender\""

import os
import socket
import time
import logging
import shlex, subprocess

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
Setup this files logging settings
'''
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

class AESocket:
    def __init__(self, port=None):
        '''
        If no port is specifed, we find the first open port after 5000.
        '''
        self.host = '127.0.0.1'
        if not port:
            self.port = self._getOpenPort()
        else:
            self.port = 5000
        self.aerender = None
        self.socket = None
        
        self.logFilePath = None
        self.logFile = None

    '''
    Private Methods
    '''

    def _getOpenPort(self, startingValue=5000):
        '''
        Find an open port to use to for the daemon.
        '''

        openPort = startingValue

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:        
            try:
                s.bind((self.host, openPort))
                break
            except Exception, e:
                logger.debug("Unable to connect on port %s\n%s" % (str(openPort), str(e)))
            openPort += 1
    
        logger.info("Found open port: " + str(openPort))

        return openPort

    def _waitForAE(self, timeout=180):
        '''
        Wait for AE to send response.
        '''
        logger.info("Waiting for After Effects...")
        
        startTime = time.time()
        while True:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.connect((self.host, self.port))
                break
            except:
                pass
            
            if timeout:
                if time.time() > (startTime + timeout):
                    logger.error("Timeout limit reached.  No response from After Effects. Shutting down.")
                    break
            
            time.sleep(.1)
            
        logger.debug("Total wait time: %s" % str(time.time() - startTime))

    def _sendScript(self, script, name, timeout=60):
        '''
        Send a script to the AERender daemon.
        '''
        if self._checkConnectionActive():
            self._waitForAE(timeout)
            logger.info("Sending script: %s" % name)
            logger.debug("Script Contents: %s" % script)
            self.socket.send("%s\n" % script)
        else:
            logger.error("Unable to send script %s.  AERender isn't connected." % name)

    def _initConnection(self):
        '''
        Init the AERender daemon to start receiving input.
        '''
        self.runScript('INITIALIZE', 'Initialize AERender')

    def _checkConnectionActive(self):
        '''
        Check that the aerender daemon is still active.
        '''
        result = False

        if self.aerender:
            if not self.aerender.poll():
                logging.info("Connection Active.")
                result = True

        return result
                

    '''
    Public Methods
    '''

    def runScript(self, script, name=""):
        '''
        Run the supplied script.
        Input includes the name of the script, and the script as a string.
        '''
        if not name:
            name = script.split("\n")[0]
        
        self._sendScript(script, name)
        return self.getResponse()
        
    def getResponse(self):
        '''
        Wait for a response from aerender. Then return it.
        '''
        if self._checkConnectionActive():
            response = None
            response = self.socket.recv(1024)
            logger.debug("Received: %s" % response)
            if response.strip() == "ERROR":
                raise RuntimeError("Received error from After Effects.")
        
            return response

    def launchAERender(self):
        '''
        Launch the aerender daemon.
        Uses the custom aerender commandLineRenderer with the -daemon flag.
        '''
        cmd = AERENDER + " -daemon " + str(self.port)
        logger.debug("AERender CMD: %s" % cmd)
        
        '''
        We will store the log output to a file,
        then have another process read it back in.
        '''
        self.logFilePath = '/tmp/aerender.%s.log' % str(self.port)
        
        if os.path.exists(self.logFilePath):
            try:
                os.remove(self.logFilePath)
            except:
                logger.error("Unable to remove existing AERender log file. (%s)" % os.path.basename(self.logFilePath))
        self.logFile = open(self.logFilePath, 'w')
        
        self.aerender = subprocess.Popen(cmd, shell=True, stdout=self.logFile)
        self.aerenderlog = subprocess.Popen(shlex.split("tail -f " + self.logFilePath))
        self._initConnection()

    def terminateConnection(self):
        '''
        Shutdown the aerender daemon.
        '''
        self._sendScript('TERMINATE', 'Terminate Connection')
        del self.aerender
        del self.aerenderlog
