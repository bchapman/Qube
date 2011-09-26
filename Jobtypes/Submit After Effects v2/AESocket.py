'''
After Effects Socket Communications Class
Launches and communicates with an After Effects process through a socket.
'''
AERENDER = "\"/Applications/Adobe After Effects CS5.5/aerender\""

import socket
import sys
import time
import logging
import subprocess
import AEScripts
import re

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

class AESocket:
    def __init__(self, port=None):
        self.host = '127.0.0.1'
        if not port:
            self.port = self.getOpenPort()
        else:
            self.port = 5000
        self.aerender = None
        self.socket = None


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
                break
            
            time.sleep(.1)
            
        logger.debug("Total wait time: " + str(time.time() - startTime))

    def runScript(self, javascript):
        self.waitForAE()
        javascript = str(javascript)

        response = None
        try:
            logger.debug("Sending script: " + javascript)
            self.socket.send(javascript + "\n")
            response = self.socket.recv(1024)
            logger.debug("Received: %s" % response)
        except Exception, e:
            logger.error("Unable to send script. " + str(e))

        return response            

    def launchAERender(self):
        cmd = AERENDER + " -daemon " + str(self.port)
        logger.debug("CMD: " + cmd)
        self.aerender = subprocess.Popen(cmd, shell=True)
        self.initConnection()

    def initConnection(self):
        self.runScript("INITIALIZE")

    def terminateConnection(self):
        self.runScript("TERMINATE")

    def monitorRender(self):
        statusbar = ""

        # # Start the Reporter Thread for Qube
        # queue = Queue.Queue() # Store the qube updates to be processed
        # # Start 1 threads for now
        # for i in range(0, 1):
        #     reporter = Reporter.Reporter(queue)
        #     reporter.setDaemon(True) # Set it to run continuosly
        #     reporter.start() # Spawn the thread
        # self.logger.info("Reporter Thread Started")

        prevFrame = None
        currFrame = None
        progressPattern = re.compile('(?<=^PROGRESS:  )(?:\(Skipping \d+\)|\d+?|\d;.*?) \((.*?)\).*$')
        completePattern = re.compile('(Total Time Elapsed)')
        while True:
            stdOut = self.aerender.stdout.readline()
            if not stdOut: break

            ''' Write the actual output line '''
            sys.stdout.write(stdOut)
            sys.stdout.flush()

            ''' Retrieve the info from each line of output '''

            prevFrame = currFrame
            result = self.reSearch(progressPattern, stdOut)
            if result != "":
                currFrame = result
                logger.info("Last Completed Frame: " + str(result))

            result = self.reSearch(completePattern, stdOut)
            if result:
                break

            # # Update Qube if frames have changed
            # if (self.job.prevFrame != self.job.currFrame):
            #     queue.put(self.job.getPercentComplete())

        # Wait for the Qube Updates to be processed
        # queue.join()

    def reSearch(self, pattern, data):
        ''' Search string for regex and return first match '''
        pattern = re.compile(pattern)
        match = pattern.search(data)    
        if (match != None):
            return match.group(1)
        else:
            return ""

# aeSocket = AESocket()
# aeSocket.launchAERender()
# 
# script = AEScripts.getOpenProjectScript("/tmp/testComp.aep")
# aeSocket.runScript(script)
# 
# script = AEScripts.getSetupSegmentScript(0, 100, 1)
# aeSocket.runScript(script)
# 
# script = AEScripts.getRenderAllScript()
# aeSocket.runScript(script)
# 
# script = AEScripts.getSetupSegmentScript(10, 19, 1)
# aeSocket.runScript(script)
# 
# script = AEScripts.getRenderAllScript()
# aeSocket.runScript(script)
# 
# aeSocket.terminateConnection()