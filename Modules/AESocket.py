'''
After Effects Socket Communications Class
Launches and communicates with an After Effects process through a socket.

Author: Brennan Chapman
Version: 1.2

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
import getpass
import socket
import time
import logging
import shlex, subprocess
import signal

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
# logger.setLevel(logging.INFO)

class AESocketError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr("After Effects returned an error.\n%s" % self.value)

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
        
        signal.signal(signal.SIGTERM, self._exitHandler)
        signal.signal(signal.SIGILL, self._exitHandler)
        signal.signal(signal.SIGSEGV, self._exitHandler)

    '''
    Private Methods
    '''

    def _exitHandler(self, signum, frame):
        '''
        Kill AERenderCore Processes for the specified project.
        
        The aerendercore process isn't directly tied to aerender.
        It is spawned by launchd.
        
        So to find which aerendercore process correlates to each render
        we sort through open files, the log files are most always open.
        By default, these carry the name of the project.
        We search for these to associate each aerendercore process
        with it's project.
        '''

        # Wait a few seconds to make sure aerendercore has enough time to load the log file
        time.sleep(10)

        projectFile = self.job.projectPath
        log = open('/tmp/aeCrashLog.log', 'a')
        log.write(str(os.path.basename(projectFile)) + '\n')
        log.write("Signal: %s" % signum)

        processes = self.getAERenderCoreProcesses()
        log.write("AERender Core Processes:" + str(processes))

        # Scan each process for open files matching the project file
        relatedPIDs = []
        for pid,files in processes.iteritems():
            for f in files:
                found = False
                log.write("Scanning:" + str(f) + '\n')
                if os.path.basename(projectFile) in f:
                    found = True
                if found:
                    relatedPIDs.append(pid)

        log.write("Related AERender Core Processes:" + str(relatedPIDs) + '\n')
        for pid in relatedPIDs:
            log.write('Killing AERenderCore (' + str(pid) + ')\n')
            os.kill(int(pid), 9)

        log.close()


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
    
        logger.debug("Found open port: " + str(openPort))

        return openPort

    def _prepScript(self, script):
        '''
        Remove comments and make the script one line
        so it can be sent through the socket.
        Return a dictionary containing the name and the script.
        '''
        if "\n" in script:
            resultScript = []
            lines = script.split("\n")
            for line in lines:
                if not line.strip().startswith("//"):
                    resultScript.append(line)

            resultScript = "".join(resultScript)

            return resultScript
        else:
            return script


    def _waitForAE(self, timeout=600):
        '''
        Wait for AE to send response.
        '''
        logger.info("--> Waiting for After Effects...")
        
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

    def _sendScript(self, script, name, timeout=600):
        '''
        Send a script to the AERender daemon.
        '''
        script = self._prepScript(script)
        if self._checkConnectionActive():
            self._waitForAE(timeout)
            logger.info("Running Script: %s" % name)
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
                logging.debug("Connection Active.")
                result = True

        return result
                

    '''
    Public Methods
    '''

    def runScript(self, script, name=""):
        '''
        Run the supplied script string.
        Input includes the name of the script, and the script as a string.
        '''
        if not name:
            name = script.split("\n")[0]
        
        self._sendScript(script, name)
        return self.getResponse()
    
    def runScriptFile(self, script):
        '''
        Run the supplied script file.
        Use the javascript $.evalFile, seems to work better.
        '''
        if os.path.exists(script):
            script = "$.evalFile(\"%s\");" % script
            name = os.path.basename(script)
            return self.runScript(script, name)
        else:
            logging.error("Script doesn't exist. %s" % script)
            return ""        
        
    def getResponse(self):
        '''
        Wait for a response from aerender. Then return it.
        '''
        if self._checkConnectionActive():
            response = None
            response = self.socket.recv(1024)
            logger.debug("Received: %s" % response)
            if "error" in response.lower():
                raise AESocketError(response)
        
            return response

    def launchAERender(self, multProcs=False, projectFile=None):
        '''
        Launch the aerender daemon.
        Uses the custom aerender commandLineRenderer with the -daemon flag.
        '''
        cmd = AERENDER + " -v ERRORS_AND_PROGRESS"
        if (multProcs):
            cmd += " -mp"
        if (projectFile):
            cmd += " -project \"" + projectFile + "\""
        cmd += " -daemon " + str(self.port)
        logger.debug("AERender CMD: %s" % cmd)
        logger.debug("Launching After Effects")
        
        '''
        We will store the log output to a file,
        then have another process read it back in.
        '''
        user = getpass.getuser()
        self.logFilePath = '/tmp/aerender.%s.%s.log' % (user, str(self.port))
        
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
