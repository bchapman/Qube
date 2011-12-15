'''
After Effects Socket Communications Class
Launches and communicates with an After Effects process through a socket.
'''
AERENDER = "\"/Applications/Adobe After Effects CS5/aerender\""

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
        self.host = '127.0.0.1'
        if not port:
            self.port = self.getOpenPort()
        else:
            self.port = 5000
        self.aerender = None
        self.socket = None
        self.connected = False
        
        self.logFilePath = None
        self.logFile = None

    def getOpenPort(self, startingValue=5000):

        openPort = startingValue

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:        
            try:
                s.bind((self.host, openPort))
                break
            except Exception, e:
                logger.debug("Unable to connect on port " + str(openPort) + "\n" + str(e))
            openPort += 1
    
        logger.info("Found open port: " + str(openPort))

        return openPort

    def waitForAE(self, timeout=180):
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
                    self.connected = False
                    break
            
            time.sleep(.1)
            
        logger.debug("Total wait time: " + str(time.time() - startTime))

    def runScript(self, script):
        self.sendScript(script)
        return self.getResponse()

    def sendScript(self, script, timeout=60):
        if self.connected:
            self.waitForAE(timeout)
            logger.info("Sending script: " + script['name'])
            logger.debug("Script Contents: " + script['script'])
            self.socket.send(script['script'] + "\n")
        
    def getResponse(self):
        if self.connected:
            response = None
            response = self.socket.recv(1024)
            logger.debug("Received: %s" % response)
            if response.strip() == "ERROR":
                raise RuntimeError("Received error from After Effects.")
        
            return response

    def launchAERender(self):
        cmd = AERENDER + " -daemon " + str(self.port)
        logger.debug("CMD: " + cmd)
        self.logFilePath = '/tmp/aerender.' + str(self.port) + '.log'
        if os.path.exists(self.logFilePath):
            try:
                os.remove(self.logFilePath)
            except:
                logger.error("Unable to remove existing " + os.path.basename(self.logFilePath) + " log file")
        self.logFile = open(self.logFilePath, 'w')
        self.aerender = subprocess.Popen(cmd, shell=True, stdout=self.logFile)
        self.aerenderlog = subprocess.Popen(shlex.split("tail -f " + self.logFilePath))
        self.connected = True
        self.initConnection()

    def initConnection(self):
        self.runScript({'name':'Initialize AERender', 'script':'INITIALIZE'})

    def terminateConnection(self):
        self.sendScript({'name':'Terminate Connection', 'script':"TERMINATE"})
        del self.aerender
        del self.aerenderlog
