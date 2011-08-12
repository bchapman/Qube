#!/usr/bin/python

"""
Submit Transcoder
Author: Brennan Chapman
Date: 8/11/2011

Purpose:
    Use a combination of Blender and QTCoffee to render
    image sequences to separate quicktime files using
    multiple computers and compile them back together
    using QTCoffee's catmovie.
    *Only works on Mac render nodes.

Features:
    Free
        Based on Blender and QTCoffee which are both free!
    Flexible
        Expandable to an unlimited # of nodes.
    Low Memory Usage
        Uses around 200MB of memory per instance.
    Smart Update
        Only renders the parts of the sequence that changed.
    AutoResolves File Output Errors
        Auto renames the output file if for some reason it
        can't be overwritten.
"""

import os, sys
import inspect
import logging
import shlex, subprocess
import time
import tempfile, cProfile
sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import TranscoderPreFlight
import Job

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
    
    logger.debug("Command: " + cmd)
    proc = subprocess.Popen(shlex.split(cmd), bufsize=-1)
    proc.wait()
    return proc.returncode

def executeJob(job):
    '''
    Main Execution of the job.
    '''

    jobstate = 'complete'

    jobObject = job.qubejob
    while 1:
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
        
            cmd = job.getInitCMD(agendaItem)
            returnCode = runCMD(cmd)
            logger.debug('Initialize Exit Code: ' + str(returnCode))
            
            if returnCode == 0:
                logger.info("Transcoder Initialize Process Complete!\n")
            else:
                logger.error("Transcoder Initialization Faild! (Exit Code)\n")
        
        elif agendaItem['name'].startswith('Segment'):
            '''
            Segment Process:
                > Load the segment frame range from the work package.
                > Check for missing frames in the segments frame range.
                    True
                        > Report an error and end the subjob
                    False
                        > Continue with transcode
                > Check if smartUpdate is turned on.
                    True
                        > Check if the Modification Times Database and the output file exists.
                            True
                                > Check if there have been modifications to any frames in this segment.
                                    True
                                        > Continue with transcode
                                    False
                                        > Skip transcoding
                > Check if we are still transcoding.
                    True
                        > Try to Remove output file if it already exists
                            Success
                                > Transcode
                            Failure
                                > Add '_' to the output file name and try again until sucess.
                                    Max retry is 3 times, then fail the subjob.
                > Check if smartUpdate is turned on.
                    True
                        > Update the modification times database
                    False
                        > Continue
                > Update the resultPackage with whether changes were made and the segment output file.
            '''
            
            logger.info("Starting Transcoder Segment Process...")

            ''' Load the frame range from the work package '''
            logger.debug("Loading frame range from the work package...")
            frameRange = agendaItem['package']['frameRange']
            job.frameRange = mySequence.loadFrameRange(frameRange)
        
            ''' Check for Missing Frames '''
            logger.info("Checking for missing frames...")
            mySequence = job.sequence
            missingFrames = mySequence.getMissingFrames(job.frameRange)

            if len(missingFrames) > 0:
                logger.error('Exiting due to missing frames!\n' + ','.join(missingFrames))

            else:
                
                ''' Variables used multiple times '''
                render = False
                error = False
                segmentFilePath = agendaItem.setdefault('package', {}).get('outputName', '')
                segmentFileExists = os.path.exists(segmentFilePath)
                currentModTimes = {}
                modTimeDBFile = job.getModTimeDBFile()

                if job.smartUpdate:
                    
                    modTimeDBFileExists = os.path.exists(modTimeDBFile)
                    
                    logger.debug('Segment Output: ' + str(segmentFilePath))
                    logger.debug('Segment Exists: ' + str(segmentFileExists))
                    logger.debug('ModTimeDBFile: ' + str(modTimeDBFile))
                    logger.debug('ModTimeDBFile Exists: ' + str(modTimeDBFileExists))
                    
                    if segmentFileExists and modTimeDBFileExists:
                        logger.info('Loading frames...')
                        segmentFrames = mySequence.getFrames(job.frameRange)
                        segmentFrameFilenames = mySequence.getFrameFilenames(segmentFrames)
                
                        logger.info('Retrieving current modification times...')
                        currentModTimes = mySequence.getModTimes(job.frameRange)
                
                        logger.info('Comparing modification times...')
                        compare = mySequence.compare(modTimeDB, job.frameRange, currentModTimes=currentModTimes)
                        logger.debug('Sequence Differences: ' + str(compare))

                        differences = compare['Added'] + compare['Deleted'] + compare['Modified']
                        logger.info('Differences: ' + str(len(differences)))

                        if len(differences) > 0:
                            render = True

                    else:
                        render = True

                else:
                    render = True

                if render and segmentFileExists:
                    for tryCount in range(0, 3+1):
                        try:
                            os.remove(segmentFilePath)
                            render = True
                        except:
                            logger.warning('Unable delete existing segment file.')
                            ''' Rename the outputFile '''
                            if tryCount < 3:
                                path, extension = os.path.splitext(segmentFilePath)
                                segmentFilePath = path + '_' + extension
                                logger.debug('segmentFilePath Updated: ' + segmentFilePath)
                            else:
                                logger.error('Unable to find suitable output path for segment.')
                                error = True
                    
                if render:
                    cmd = job.getSegmentCMD(agendaItem)
                    returnCode = runCMD(cmd)
                    logger.debug('Initialize Exit Code: ' + str(returnCode))
                
                    if job.smartUpdate:
                        logger.info("Saving modification times...")
                        logger.debug("Saved ModTimes: " + str(currentModTimes))
                        job.sequence.saveModTimes(modTimeDBFile, modTimeDict=currentModTimes, frameRange=job.frameRange)
                
                else:
                    logger.info("No changes to segment " + agendaItem['name'])
                    if not error:
                        returnCode = 0

                '''
                Check if this is the last agenda item that's complete.
                If so, unblock the final output subjobs.
                '''
                agendaItem['resultpackage'] = { 'Changed': render, 'segmentFile':segmentFile }

                logger.info("Transcoder Segment Process Complete!\n")

        elif agendaItem['name'].startswith('Output'):
            '''
            Final Output Process
                > Gather the output paths and changes for all of the segments
                stored in their resultPackage.
                > Check if there were changes.
                    True
                        > Try to Remove output file if it already exists
                        ...
            '''
            logger.info("Starting Final Output Process...\n")

            cmd = job.getFinalOutputCMD(segmentOutputPaths)
            returnCode = runCMD(cmd)            

            '''
            Add the quicktime file to the subjob's outputPaths
            '''
            agendaItem['resultpackage'] = { 'outputPaths': job.getFinalOutputFile(agendaItem) }
            
            logger.info("Transcoder Finalize Process Complete!\n")

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
    # f = tempfile.NamedTemporaryFile(delete=False)
    # cProfile.run('main()', f.name)
    main()
