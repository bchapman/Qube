#!/usr/bin/python

"""
Submit Transcoder
Author: Brennan Chapman
Date: 7/12/2011

Purpose:
    Run the transcoder jobs using blender
    to cluster transcode image sequences
    to separate quicktime movies.
    Then use qttools to merge them together.
    *Only works on Mac render nodes

Features:
    Uses blender which is free!
    Can use an unlimited # of computers
    Low memory usage...around 200MB per instance
"""

import os, sys
import inspect
import logging
sys.path.append('/Applications/pfx/qube/api/python/')
import qb

# Gotta be a better way to do this.  Suggestions?
sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
print 'PATH: ' + str(sys.path) + "\n"
import PreFlight
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

'''
Main
'''

def initJob():
    # Get the job object
    jobObject = qb.jobobj()
    # Make sure the agenda is added
    if not jobObject.get('agenda', False):
        jobObject['agenda'] = qb.jobinfo(id=jobObject['id'], agenda=True)[0]['agenda']
    # print "Qube Job Agenda: " + str(jobObject['agenda']) + "\n"
    job = Job.Job(logger) # Create our own Job Object
    job.loadOptions(jobObject) # Load the Qube Job into our job template

    return job

def runCMD(cmd):
    '''
    Run the specified command, and return the exit code.
    '''
    
    logger.info("Command: " + cmd)
    proc = subprocess.Popen(shlex.split(cmd), bufsize=-1)
    proc.wait()
    return proc.returncode

def executeJob(job):
    '''
    Execute the job.
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
            logger.info("Checking for missing frames...")
            missingFrames = mySequence.getMissingFrames(frameRange)
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
                '''
                render = False
                hashFile = ''
                currentHashCodes = {}
                outputFileName = agendaItem.setdefault('package', {}).get('outputPath', '')
                if job.smartUpdate and os.path.exists(job.getSegmentOutputFile(outputFileName)):
                    hashFile = job.getHashFile()
                    logger.debug('Hash File: ' + hashFile)
                    exists = os.path.exists(hashFile)
                    logger.debug('Exists: ' + str(exists))
                    if exists:
                        logger.debug("Hash exists.")
                        logger.info('Loading frames...')
                        segmentFrames = mySequence.getFrames(frameRange)
                        
                        logger.info('Generating current hash codes...')
                        currentHashCodes = mySequence.getHashCodes(frameRange)
                        
                        logger.info('Comparing hash codes...')
                        compare = mySequence.compareHashCodes(hashFile, frameRange)
                        differences = compare['Added'] + compare['Deleted'] + compare['Modified']
                        logger.info('Differences: ' + str(len(differences)))
                        
                        for frame in segmentFrames:
                            if os.path.basename(frame) in differences:
                                render = True
                                break
                    else:
                        logger.debug('Hash file doesn\'t exist.') 
                        render = True
                else:
                    render = True

                if render:
                    cmd = job.getCMD(agendaItem)
                    returnCode = runCMD(cmd)
                    
                    '''
                    Store the hash codes for the image sequence so we can
                    find changes that happen between now and next time.
                    '''
                    if job.smartUpdate:
                        logger.info("Saving hash codes to db...")
                        logger.debug("Current Hash Codes: " + str(currentHashCodes))
                        job.sequence.saveHashCodes(hashFile, hashDict=currentHashCodes)
                    
                else:
                    logger.info("No changes to segment " + agendaItem['name'])
                    returnCode = 0

                '''
                Check if this is the last agenda item that's complete.
                If so, unblock the final output subjobs.
                '''
                currAgenda = qb.jobinfo(id=job.qubejob['id'], agenda=True)[0]['agenda']
                lastSegment = True
                finalOutputs = []
                for item in currAgenda:
                    if item['name'].endswith('.mov'):
                        logger.debug('Found final output subjob: ' + str(item['name']))
                        finalOutputs.append(str(job.qubejob['id']) + ':' + str(item['name']))
                    elif not item['name'].endswith('Initialize'):
                        logger.debug('Found segment subjob: ' + str(item['name']) + ' Status: ' + str(item['status']))
                        if item['status'] is not 'complete':
                            if item['name'] is not agendaItem['name']:
                                lastSegment = False
                if lastSegment:
                    for output in finalOutputs:
                        logger.info("Unblocking Output: " + output)
                        qb.unblockwork(output)
                else:
                    logger.debug('Not the last segment.')

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
    preflight = PreFlight.PreFlight(logger)
    
    if (preflight.check()):
        job      = initJob()
        state    = executeJob(job)
        cleanupJob(job, state)
    
if __name__ == "__main__":
    f = tempfile.NamedTemporaryFile(delete=False)
    cProfile.run('main()', f.name)
