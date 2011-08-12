#!/usr/bin/python

"""
Submit Transcoder
Author: Brennan Chapman
Date: 7/12/2011

Purpose:
    Use a combination of Blender and QTCoffee to render
    image sequences to separate quicktime files using
    multiple computers and compile them back together
    using QTCoffee's catmovie.
    *Only works on Mac render nodes.

Features:
    Uses blender which is Free!
    Can use an unlimited # of computers
    Low memory usage...around 200MB per instance :)
"""

import os, sys
import inspect
import logging
sys.path.append('/Applications/pfx/qube/api/python/')
import qb

# Gotta be a better way to do this.  Suggestions?
sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
# print 'PATH: ' + str(sys.path) + "\n"
import TranscoderPreFlight
import Job
import shlex, subprocess
import time

import tempfile
import cProfile

'''
Set up the logging module.
'''

logger = logging.getLogger("main")
ch = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)
ch.setLevel(logging.DEBUG)


def initJob():
    '''
    Create our own job object that can serve as the
    central storage for all execution based variables.
    '''

    job = Job.Job()
    job.loadOptions(qb.jobobj())

    return job

def runCMD(cmd):
    '''
    Run the specified command using subprocess and
    return the exit code.
    '''
    
    logger.info("Command: " + cmd)
    proc = subprocess.Popen(shlex.split(cmd), bufsize=-1)
    proc.wait()
    return proc.returncode

def executeJob(job):
    '''
    Main Execution of the job.
    '''
    
    global render
    jobstate = 'complete'

    jobObject = job.qubejob
    while 1:
        # logger.info("Job Object" + str(jobObject))
        agendaItem = qb.requestwork()
        returnCode = 1

        '''
        If our subjob is the Initialize command, block the other jobs.
        This is because the output blender scene of the initialize command
        is used as the input for the segment commands.
        '''

        ''' First Handle non-running state cases '''
        if agendaItem['status'] in ('complete', 'pending', 'blocked', 'waiting'):
            '''
            complete -- no more frames
            pending -- preempted, so bail out
            blocked -- perhaps item is part of a dependency
            '''
            jobstate = agendaItem['status']
            print 'job %s state is now %s' % (jobObject['id'], jobstate)
            break

        '''
        Isolate which command to execute based on the work name.
        Then execute each associated command.
        '''
        if agendaItem['name'] == 'Initialize':
            logger.info("Starting Transcoder Initialize Process...\n")
            
            logger.info("Blocking Segment and Finalize Subjobs:")
            for item in jobObject['agenda']:
                if item['name'] != 'Initialize':
                    workID = str(jobObject['id']) + ':' + str(item['name'])
                    qb.blockwork(workID)
                    logger.info('- ' + item['name'] + " - " + workID)
            logger.info("")
        
            cmd = job.getCMD(agendaItem)
            returnCode = runCMD(cmd)
            
            if returnCode == 0:
                logger.info("Unblocking Segment Subjobs:")
                
                for item in jobObject['agenda']:
                    itemName = str(item['name'])
                    if itemName.endswith('Initialize') == False and itemName.endswith('.mov') == False:
                        workID = str(jobObject['id']) + ':' + str(item['name'])
                        qb.unblockwork(workID)
                        logger.info('+ ' + item['name'] + " - " + workID)
                logger.info("")

                logger.info("Transcoder Initialize Process Complete!\n")
            else:
                logger.error("Transcoder Initialization Faild! (Exit Code)\n")
        
        elif agendaItem['name'].endswith('.mov'):                
            logger.info("Starting Transcoder Finalize Process...\n")

            cmd = job.getCMD(agendaItem)
            returnCode = runCMD(cmd)            

            '''
            Add the quicktime file to the subjob's outputPaths
            '''
            agendaItem['resultpackage'] = { 'outputPaths': job.getFinalOutputFile(agendaItem) }
            
            logger.info("Transcoder Finalize Process Complete!\n")
        
        elif agendaItem['name'] != '':
            logger.info("Starting Transcoder Segment Process...")
            
            '''
            First check for missing frames that may have dissappeared.
            '''
            mySequence = job.sequence
            frameRange = agendaItem['name']
            job.frameRange = mySequence.loadFrameRange(frameRange)
            logger.info("Checking for missing frames...")
            missingFrames = mySequence.getMissingFrames(job.frameRange)
            if len(missingFrames) > 0:
                logger.error("Missing Frames!")
                for frame in missingFrames:
                    logger.error(str(frame))
            else:
                
                '''
                (Smart-Update)
                If the sequence has been rendered before,
                Only render this segment if this part of the sequence
                has changed since last time.
                Check for differences based on modification times.
                '''
                render = False
                modTimeDB = job.getModTimeDBFile()
                currentModTimes = {}
                outputFileName = agendaItem.setdefault('package', {}).get('outputName', '')
                outputFilePath = job.getSegmentOutputFile(outputFileName)
                outputExists = os.path.exists(outputFilePath)
                logger.debug('Segment Output: ' + str(outputFilePath))
                logger.debug('Segment Exists: ' + str(outputExists))
                if job.smartUpdate and outputExists:
                    segmentFilePath = job.getSegmentOutputFile(agendaItem.get('outputName', ''))
                    logger.debug('modTimeDB: ' + modTimeDB)
                    modTimeDBExists = os.path.exists(modTimeDB)
                    logger.debug('modTimeDB Exists: ' + str(modTimeDBExists))
                    if modTimeDBExists:
                        logger.info('Loading frames...')
                        segmentFrames = mySequence.getFrames(job.frameRange)
                    
                        logger.info('Generating current modification times...')
                        currentModTimes = mySequence.getModTimes(job.frameRange)
                    
                        logger.info('Comparing modification times...')
                        compare = mySequence.compare(modTimeDB, job.frameRange)
                        differences = compare['Added'] + compare['Deleted'] + compare['Modified']
                        logger.info('Differences: ' + str(len(differences)))
                    
                        for frame in segmentFrames:
                            if os.path.basename(frame) in differences:
                                render = True
                                break
                    else:
                        render = True
                else:
                    render = True

                if render:
                    cmd = job.getCMD(agendaItem)
                    returnCode = runCMD(cmd)
                    
                    '''
                    Store the modification times for the image sequence so
                    we can find changes that happen between now and next time.
                    '''
                    if job.smartUpdate:
                        logger.info("Saving modTimesDB...")
                        logger.debug("Current ModTimes: " + str(currentModTimes))
                        job.sequence.saveModTimes(modTimeDB, modTimeDict=currentModTimes, frameRange=job.frameRange)
                    
                else:
                    logger.info("No changes to segment " + agendaItem['name'])
                    returnCode = 0

                '''
                Check if this is the last agenda item that's complete.
                If so, unblock the final output subjobs.
                '''
                agendaItem['resultpackage'] = { 'Changed': render }

                logger.info("Transcoder Segment Process Complete!\n")

        else:
            logger.error("Invalid Agenda Item")
            logger.info(str(agendaItem))

        '''
        Update the work status based on the return code.
        '''
        if returnCode == 0:
            agendaItem['status'] = 'complete'
        else:
            agendaItem['status'] = 'failed'

        ''' Report back the results to the Supervisor '''
        qb.reportwork(agendaItem)


    return jobstate


def cleanupJob(job, state):
    qb.reportjob(state)


def main():
    ''' First run the preflight to determine if worker is ready. '''
    preflight = TranscoderPreFlight.PreFlight(logger)
    
    if (preflight.check()):
        job      = initJob()
        state    = executeJob(job)
        cleanupJob(job, state)
    
if __name__ == "__main__":
    f = tempfile.NamedTemporaryFile(delete=False)
    cProfile.run('main()', f.name)
