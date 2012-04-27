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
import xml.dom.minidom
import subprocess

sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))) + "/Modules")
import AESocket
import memUsage
import pathConvert

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

def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

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

        reservedMem = reservedMem * 1024 * 1024
        logging.info("DLM Reserved Memory (Bytes): %s" % reservedMem)
        memNode.parentNode.childNodes[3].firstChild.nodeValue = reservedMem

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

    msg = "Memory Usage\n\tSystem Total: %0.2fGB\n\tSystem Active: %0.2fGB\n\tSystem Available: %0.2fGB\n\tAE Avail: %0.2fGB\n\tAE Reserved: %0.2fGB"
    f = float(1024)
    msg = msg % (d['totalMem']/f, d['actMem']/f, d['availMem']/f, d['aeAvailMem']/f, d['aeResvMem']/f)
    logging.info(msg)

    # Update DLM if we have enough memory to render
    if d['aeAvailMem'] < 1024:
        logging.error("Error: Not enough memory free")
        d['error'] = True
    else:
        if not updateDLM(d['aeResvMem']):
            d['error'] = True

    # Now check if we need to enable multiprocessing
    # Node must have more than 4GB of RAM available for AE
    if d['aeAvailMem'] > 2048:
        d['multProcs'] = True

    return d

def getCPUCores(availMem, ramPerCPU):
    # Return the dictionary of the renders
    # available and reserved core count based
    # on the input memory requirements

    logging.debug("availMem: %s ramPerCPU: %s" % (availMem, ramPerCPU))

    cores = {}

    # Get the total # of cores available
    cmd = "/usr/sbin/sysctl hw.ncpu | awk '{print $2}'"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.wait()
    totalCores = int(p.communicate()[0].strip())
    print("Total CPU Cores: %s" % totalCores)

    # Get the number of cpus allowed within the available memory
    # Subtract one extra to make room for the foreground process
    cores['available'] = min(availMem / ramPerCPU, totalCores) - 1

    cores['reserved'] = totalCores - cores['available']

    return cores

def executeJob(job):
    '''
    Execute the transcoding process.

    '''

    # Convert the paths
    logging.debug("#### Start Path Convert")
    job = pathConvert.convertDict(job)
    logging.debug("#### End Path Convert")

    jobstate = 'pending'
    pkg = job.setdefault('package', {})
    # logger.debug("Qube Job: " + str(job))

    try:
        memUsage = setupAEMemory()
        
        if memUsage['error'] == True:
            raise Exception, "Fatal Error with Memory Usage"
        
        # Setup multiprocessing
        multProcs = memUsage['multProcs']
        ramPerCPU = 2
        if (pkg.has_key("complexity")):
            logging.debug("complexity found")
            complexValue = pkg["complexity"].lower()
            if complexValue == "normal":
                pass
            elif complexValue == "complex":
                multProcs = True
                ramPerCPU = 3
            elif complexValue == "simple":
                multProcs = False

        # Get the number of virtual cores
        cores = getCPUCores(memUsage['aeAvailMem']/1024, ramPerCPU)
        logging.debug("Cores: %s" % cores)

        script = "RenderTools.setMultiprocessing(\"%s\",%d, %d);" % (multProcs, ramPerCPU, cores['reserved'])
        if (multProcs):
            logging.info("Multiprocessing: %s - %dGB per CPU with %d Cores Available" % (multProcs, ramPerCPU, cores['available']))
        else:
            logging.info("Multiprocessing: %s" % multProcs)

        aeSocket = AESocket.AESocket()
        aeSocket.launchAERender(multProcs, projectFile=pkg['renderProjectPath'])

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
                    outputPaths = pathConvert.convertList(outputPaths, reverse=True)
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
