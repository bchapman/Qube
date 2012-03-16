#!/usr/bin/python

'''
Submit After Effects v2
Author: Brennan Chapman
Date: 9/26/2011
'''

import os
import sys
import inspect
import logging
import traceback
import re

sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.append("/Volumes/theGrill/.qube/Modules/")
import AESocket

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import Tools

RENDERTOOLS = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + "/Scripts_Remote/RenderTools.jsx"

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

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)
# logger = logging.getLogger()

def getAvailableRAM():
    
    # Get AE's reserved RAM settings
    dlmSettingsPath = "~/Library/Preferences/Adobe/dynamiclinkmanager/2.0/memorybalancercs55v2.xml"
    dlmSettingsPath = os.path.expanduser(dlmSettingsPath)
    if os.path.exists(dlmSettingsPath):
        logging.info("dlmSettings Exists")
        dlmSettingsFile = open(dlmSettingsPath, 'r')
        dlmSettings = dlmSettingsFile.read()
        reservedRAM = int(re.findall("(memorytouseforotherapplications)</key>\n\D+'64'>(\d+)", dlmSettings)[0][1]) / 1073741824
        logging.info("AE Reserved RAM: %dGB" % reservedRAM)
    
        # Get the total host RAM
        hostName = os.uname()[1]
        logging.debug("Host Name: %s" % hostName)
        hostResources = qb.hostinfo(name=hostName)[0]["resources"]
        logging.debug("Host resources: %s" % hostResources)
        hostRAM = int(re.findall("(host.memory=\d+/)(\d+)", hostResources)[0][1])/1024
        logging.info("Host RAM: %dGB" % hostRAM)

        availRAM = hostRAM - reservedRAM
        logging.info("Available RAM: %dGB" % availRAM)
        
        return availRAM
    else:
        return 0

def executeJob(job):
    '''
    Execute the transcoding process.

    '''

    jobstate = 'pending'
    pkg = job.setdefault('package', {})
    # logger.debug("Qube Job: " + str(job))

    try:
        # Setup multiprocessing
        multProcs = True
        ramPerCPU = 2
        if (getAvailableRAM() > 7):
            if (pkg.has_key("complexity")):
                logging.info("complexity found")
                complexValue = pkg["complexity"].lower()
                if complexValue == "normal":
                    pass
                elif complexValue == "complex":
                    multProcs = True
                    ramPerCPU = 3
                elif complexValue == "simple":
                    multProcs = False
        else:
            multProcs = False
        script = "RenderTools.setMultiprocessing(\"%s\",%d);" % (multProcs, ramPerCPU)
        if (multProcs):
            logging.info("Multiprocessing: %s - %dGB per CPU" % (multProcs, ramPerCPU))
        else:
            logging.info("Multiprocessing: %s" % multProcs)

        aeSocket = AESocket.AESocket()
        aeSocket.launchAERender(multProcs)

        # Load the render tools
        script = "$.evalFile(new File(\"%s\"));\"Render Tools Loaded\"" % os.path.abspath(RENDERTOOLS)
        logging.debug("Render Tools Script: %s" % script)
        aeSocket.runScript(script, "Render Tools Setup")

        script = "RenderTools.openProject(\"%s\");" % pkg['renderProjectPath']
        result = aeSocket.runScript(script, "Open Project")
        logging.debug("Open Project Result: %s" % script)
        
        # Finalize multiprocessing setting
        # result = aeSocket.runScript(script, "Set Multiprocessing")
        # logging.debug("Set Multiprocessing Result: %s" % result)
         
        # script = "RenderTools.setRenderQuality(\"%s\");" % pkg['quality']
        # result = aeSocket.runScript(script, "Set Render Quality")
        # logging.debug("Set Render Quality Result: %s" % script)

        while 1:
            agendaItem = qb.requestwork()
            logger.debug("Agenda Item: " + str(agendaItem))
            returnCode = 0

            '''
            First Handle non-running state cases
            '''
            if agendaItem['status'] in ('complete', 'pending', 'blocked', 'waiting'):
                '''
                complete -- no more frames
                pending -- preempted, so bail out
                blocked -- perhaps item is part of a dependency
                '''
                jobstate = agendaItem['status']
                logger.debug('Job %s state is now %s' % (job['id'], jobstate))
                break

            '''
            Main
            '''
            if agendaItem['name'].strip() != '':
                if '-' in agendaItem['name']:
                    startFrame, endFrame = agendaItem['name'].split('-')
                else:
                    startFrame = endFrame = agendaItem['name']
                logger.debug("startFrame: " + str(startFrame) + " endFrame: " + str(endFrame))
                
                script = "RenderTools.setupSegment(%s, %s, %s);" % (startFrame, endFrame, pkg['rqIndex'])
                logging.debug("Setup Segment Script: %s" % script)
                aeSocket.runScript(script, "Setup Segment")
                outputs = pkg['outputFiles'].split(",")
                logger.debug("Outputs: " + str(outputs))

                renderTools = Tools.Tools(agendaItem, outputs, aeSocket.logFilePath, startFrame, endFrame)
                script = "RenderTools.renderQueued();"
                aeSocket._sendScript(script, "Render Queued", timeout=None) # Disable timeout here
                monitorResult = renderTools.monitorRender(timeout=1800) # Max time for frame is 30min
                socketResult = aeSocket.getResponse()
                renderTools.alreadyComplete = True

                if socketResult == True:
                    returnCode = 1
                if not monitorResult:
                    returnCode = 2

                outputPaths = renderTools.getOutputPaths(startFrame, endFrame)
                for path in outputPaths:
                    if not os.path.exists(path):
                        logging.error("Frame doesn't exist: %s" % path)
                        returnCode = 3

                '''
                Update the work status based on the return code.
                '''
                if returnCode == 0:    
                    agendaItem['resultpackage'] = {'outputPaths': ','.join(outputPaths),'progress':'1'}
                    agendaItem['status'] = 'complete'
                else:
                    agendaItem['status'] = 'failed'

            ''' Report back the results to the Supervisor '''
            qb.reportwork(agendaItem)
    
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(repr(traceback.extract_tb(exc_traceback)))
        logger.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        # logger.debug("ERROR: " + str(e))
    
    try:
        aeSocket.terminateConnection()
    except Exception, e:
        logger.error("Unable to terminate aerender. " + str(e))

    logger.info("AERender finished.")
    return jobstate


def cleanupJob(state):
    qb.reportjob(state)

def main():
    '''
    Run preflight checks to make sure the worker is ready and able to transcode.
    '''
    
    state = executeJob(qb.jobobj())
    cleanupJob(state)

if __name__ == "__main__":
    main()
