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

sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import AESocket
import AEScripts

sys.path.insert(0, '../../Modules')
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

def executeJob(job):
    '''
    Execute the transcoding process.

    '''

    jobstate = 'pending'
    pkg = job.setdefault('package', {})
    # logger.debug("Qube Job: " + str(job))

    aeSocket = AESocket.AESocket()
    aeSocket.launchAERender()
    
    script = AEScripts.getOpenProjectScript(pkg['renderProjectPath'])
    aeSocket.runScript(script)

    while 1:
        agendaItem = qb.requestwork()
        returnCode = 1

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
            logger.info('Job %s state is now %s' % (job['id'], jobstate))
            break

        '''
        Main
        '''        
        startFrame, endFrame = agendaItem['name'].split('-')
        logger.debug("startFrame: " + str(startFrame) + " endFrame: " + str(endFrame))
        script = AEScripts.getSetupSegmentScript(startFrame, endFrame, pkg['rqIndex'])
        outputString = aeSocket.runScript(script)
        outputs = outputString.replace("\n", "").split(',')
        logger.debug("Outputs: " + str(outputs))
        
        ''' If output is a movie, go ahead and delete it before rendering. '''
        for output in outputs:
            if output.endswith('.mov'):
                if os.path.exists(output):
                    try:
                        os.remove(output)
                        logger.info("Deleted existing movie.")
                    except:
                        logger.warning("Unable to remove existing movie. " + str(output))
        
        script = AEScripts.getRenderAllScript()
        result = aeSocket.runScript(script)
        if result == True:
            returnCode = 0
        
        for output in outputs:
            if '##' in output:
                firstFrame = output.replace("[", "").replace("]", "")
                firstFrame = firstFrame.replace("#", "0")
                mySequence = sequenceTools.Sequence(firstFrame)
                corruptFrames = mySequence.getCorruptFrames(str(startFrame) + " - " + str(endFrame))
                if corruptFrames:
                    returnCode = 22
                for frame in corruptFrames:
                    framePath = mySequence.getFrameFilename(frame)
                    logger.debug("Deleting corrupt frame: " + os.path.basename(framePath))
                    try:
                        os.remove(framePath)
                    except:
                        logger.error("Unable to delete corrupt frame: " + os.path.basename(framePath))

        '''
        Update the work status based on the return code.
        '''
        if returnCode == 0:
            agendaItem['status'] = 'complete'
        else:
            agendaItem['status'] = 'failed'

        ''' Report back the results to the Supervisor '''
        qb.reportwork(agendaItem)
    
    aeSocket.terminateConnection()

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
