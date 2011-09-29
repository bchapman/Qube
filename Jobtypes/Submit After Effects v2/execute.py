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
import Tools


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

rootLogger.setLevel(logging.INFO)

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
        logger.debug("Agenda Item: " + str(agendaItem))
        returnCode = 0
        errors = False

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
        if agendaItem['name'].strip() != '':
            logger.debug("Working")
            if '-' in agendaItem['name']:
                startFrame, endFrame = agendaItem['name'].split('-')
            else:
                startFrame = endFrame = agendaItem['name']
            logger.debug("startFrame: " + str(startFrame) + " endFrame: " + str(endFrame))
            script = AEScripts.getSetupSegmentScript(startFrame, endFrame, pkg['rqIndex'])
            outputString = aeSocket.runScript(script)
            if (outputString.strip() == "ERROR"):
                logger.error("Unable to setup segment.")
                errors = True
            else:
                outputs = outputString.replace("\n", "").split(',')
                logger.debug("Outputs: " + str(outputs))
        
            if not errors:
                renderTools = Tools.Tools(agendaItem, outputs, aeSocket.logFilePath, startFrame, endFrame)
                script = AEScripts.getRenderAllScript()
                aeSocket.sendScript(script)
                monitorResult = renderTools.monitorRender()
                socketResult = aeSocket.getResponse()
                renderTools.alreadyComplete = True
        
                if socketResult == True:
                    returnCode = 1
                if not monitorResult:
                    returnCode = 2

            if errors:
                returnCode = 3

            '''
            Update the work status based on the return code.
            '''
            if returnCode == 0:
                agendaItem['resultpackage'] = {'outputPaths': ','.join(outputs)}
                agendaItem['status'] = 'complete'
            else:
                agendaItem['status'] = 'failed'

        ''' Report back the results to the Supervisor '''
        qb.reportwork(agendaItem)
    
    aeSocket.terminateConnection()
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
