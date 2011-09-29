'''
After Effects Socket Communications Class
Launches and communicates with an After Effects process through a socket.
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
logger.setLevel(logging.DEBUG)

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

    def waitForAE(self, timeout=60):
        logger.info("Waiting for After Effects...")
        
        startTime = time.time()
        while True:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.socket.connect((self.host, self.port))
                break
            except:
                pass
            
            if time.time() > (startTime + timeout):
                logger.error("Timeout limit reached.  No response from After Effects. Shutting down.")
                self.connected = False
                break
            
            time.sleep(.1)
            
        logger.debug("Total wait time: " + str(time.time() - startTime))

    def runScript(self, javascript):
        self.sendScript(javascript)
        return self.getResponse()

    def sendScript(self, javascript):
        if self.connected:
            self.waitForAE()
            javascript = str(javascript)
            try:
                logger.debug("Sending script: " + javascript)
                self.socket.send(javascript + "\n")
            except Exception, e:
                logger.error("Unable to send script. " + str(e))
        
    def getResponse(self):
        if self.connected:
            response = None
            try:
                response = self.socket.recv(1024)
                logger.debug("Received: %s" % response)
            except Exception, e:
                logger.error("Unable to receive response." + str(e))
        
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
        self.runScript("INITIALIZE")

    def terminateConnection(self):
        self.runScript("TERMINATE")