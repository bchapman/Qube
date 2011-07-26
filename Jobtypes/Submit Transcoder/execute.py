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
import Render
import signal
import shlex, subprocess

'''
Set up the logging module.
'''

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


'''
Main
'''

def initJob():
    # Get the job object
    jobObject = qb.jobobj()
    # Make sure the agenda is added
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
        if agendaItem['status'] in ('complete', 'pending', 'blocked'):
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
                    if item['name'] not in ('Initialize', 'Finalize'):
                        workID = str(jobObject['id']) + ':' + str(item['name'])
                        qb.unblockwork(workID)
                        logger.info('+ ' + item['name'] + " - " + workID)
                logger.info("")

                logger.info("Transcoder Initialize Process Complete!\n")
            else:
                logger.error("Transcoder Initialization Faild! (Exit Code)\n")
        
        elif agendaItem['name'] == 'Finalize':
            logger.info("Starting Transcoder Finalize Process...\n")
        
            cmd = job.getCMD(agendaItem)
            returnCode = runCMD(cmd)
            
            '''
            Store the hash codes for the image sequence so we can
            find changes that happen between now and next time.
            '''
            logger.info("Saving Hash Codes...")
            mySequence = job.sequence
            mySequence.saveHashCodes(job.getHashFile())
            logger.info("Hash Codes Saved!")
            

            '''
            Add the quicktime file to the subjob's outputPaths
            '''
            agendaItem['resultpackage'] = { 'outputPaths': job.outputFile }
            
            logger.info("Transcoder Finalize Process Complete!\n")
        
        elif agendaItem['name'] != '':
            logger.info("Starting Transcoder Segment Process...\n")
            
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
                if job.smartUpdate and os.path.exists(agendaItem.setdefault('package', {}).get('outputPath', '')):
                    hashFile = job.getHashFile()
                    if os.path.exists(hashFile):
                        logger.info("Getting segmentFrames...")
                        segmentFrames = mySequence.getFrames(frameRange)
                        logger.info("Comparing Hash Codes...")
                        compare = mySequence.compareHashCodes(hashFile, frameRange)
                        differences = compare['Added'] + compare['Deleted'] + compare['Modified']
                        logger.info("Differences: " + str(differences))
                        
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
                else:
                    logger.info("No changes to segment " + agendaItem['name'])
                    returnCode = 0
            
                '''
                Find the last segment subjob ID.
                Then check if this was the last work subjob.
                If so, unblock the finalize subjob.
                '''
                lastSegmentID = 0
                for item in jobObject['agenda']:
                    if item['name'] not in ('Initialize', 'Finalize'):
                        if item['id'] > lastSegmentID:
                            lastSegmentID = item['id']
                if (agendaItem['id'] == lastSegmentID):
                    workID = str(jobObject['id']) + ':' + str('Finalize')
                    qb.unblockwork(workID)
                    logger.info("Finalize Subjob Unblocked.")

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
    main()