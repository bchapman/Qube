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

import os
import sys
import inspect
import logging
import shlex
import subprocess

sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import TranscoderPreFlight
import Control
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

# rootLogger.setLevel(logging.DEBUG)

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)

def initControl():
    '''
    Initialize our controller with the qube job.
    '''

    control = Control.Control(qb.jobobj())

    return control


def runCMD(cmd):
    '''
    Run the specified command using subprocess
    and return the exit code.
    '''

    logger.debug("Command: " + cmd)
    proc = subprocess.Popen(shlex.split(cmd), bufsize=-1)
    proc.wait()
    return proc.returncode


def executeJob(control):
    '''
    Execute the transcoding process.

    '''

    jobstate = 'pending'
    qbJob = control.getQubeJobObject()

    if not control.checkForErrors():
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
                logger.info('Job %s state is now %s' % (qbJob['id'], jobstate))
                break

            '''
            Run the transcoding process that corresponds to the agendaItem name.
                Initialize
                    Setup the blender scene.
                Segment
                    Transcode a segment of frames.
                Final Output
                    Merge that output's segments together with audio.
            '''
            if agendaItem['name'] == 'Initialize':
                logger.info('Initializing...\n')

                if os.path.exists(control.getBlendFile()):
                    logger.info("Initialization script alread exists.")
                    returnCode = 0
                else:
                    returnCode = runCMD(control.getInitCMD(agendaItem))

                if returnCode == 0:
                    logger.info('Initialization Complete! (' + str(returnCode) + ')\n')
                else:
                    logger.error('Initialization Failed! (' + str(returnCode) + ')\n')

            elif agendaItem['name'].startswith('Segment'):
                '''
                Segment Process:
                    > Make sure the blender project was created
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
                render = False
                error = False

                ''' Check for the blender project '''
                if not os.path.exists(control.getBlendFile()):
                    logger.error('Blender Project doesn\'t exist.')
                    error = True
                else:

                    ''' Load the frame range from the work package '''
                    frameRangeString = agendaItem['package']['frameRange']
                    logging.debug("FrameRangeString: %s" % frameRangeString)
                    frameRange = sequenceTools.loadFrameRange(frameRangeString)
                    logging.debug("Loaded frameRange: %s" % frameRange)

                    ''' Check for Missing Frames '''
                    mySequence = control.getSequence()
                    missingFrames = mySequence.getMissingFrames(frameRange)

                    if len(missingFrames) > 0:
                        logger.error('Missing frames!\n' + ','.join(missingFrames))
                        error = True
                    else:
                        logger.info('No Missing Frames')

                if not error:

                    ''' Variables used multiple times '''
                    segmentFilePath = agendaItem.setdefault('package', {}).get('segmentFile', '')
                    segmentFileExists = os.path.exists(segmentFilePath)
                    currentModTimes = {}
                    modTimeDBFile = control.getModTimeDBFile()

                    if control.getSmartUpdate():

                        modTimeDBFileExists = os.path.exists(modTimeDBFile)

                        logger.debug('Segment Output: ' + str(segmentFilePath))
                        logger.debug('Segment Exists: ' + str(segmentFileExists))
                        logger.debug('ModTimeDBFile: ' + str(modTimeDBFile))
                        logger.debug('ModTimeDBFile Exists: ' + str(modTimeDBFileExists))

                        if segmentFileExists and modTimeDBFileExists:
                            logger.info('Smart Updating')

                            logger.debug('Loading current modification times...')
                            currentModTimes = mySequence.getModTimes(frameRange)
                            logger.debug('Current modication times loaded. %s' % currentModTimes)

                            logger.debug('Comparing modification times for frame range %s...' % frameRange)
                            compare = mySequence.compare(modTimeDBFile, frameRange, currentModTimes=currentModTimes)
                            logger.debug('Sequence Differences: %s' % str(compare))

                            differences = ''
                            if len(compare['Added']) > 0:
                                frameNumbers = mySequence.getFramesFromFilenames(compare['Added'])
                                differences += '\n\tAdded: %s' % mySequence.convertListToRanges(frameNumbers)
                            if len(compare['Deleted']) > 0:
                                frameNumbers = mySequence.getFramesFromFilenames(compare['Deleted'])
                                differences += '\n\tDeleted: %s' % mySequence.convertListToRanges(frameNumbers)
                            if len(compare['Modified']) > 0:
                                frameNumbers = mySequence.getFramesFromFilenames(compare['Modified'])
                                differences += '\n\tModified: %s' % mySequence.convertListToRanges(frameNumbers)    
                            
                            if differences:
                                logger.info('Sequence Differences: %s' % differences)
                                render = True

                        else:
                            render = True

                    else:
                        render = True

                    if render:
                        segmentFilePath = control.getValidOutputPath(segmentFilePath)
                        if segmentFilePath:
                            render = True
                        else:
                            error = True

                    if render:
                        logger.info('Transcoding Segment %s' % agendaItem['name'])
                        cmd = control.getSegmentCMD(agendaItem)
                        returnCode = runCMD(cmd)
                        logger.info('Transcoding Segment Complete! (' + str(returnCode) + ')')

                        if control.getSmartUpdate():
                            logger.debug("Saved ModTimes: " + str(currentModTimes))
                            control.job.sequence.saveModTimes(modTimeDBFile,
                                modTimeDict=currentModTimes, frameRange=frameRange)
                            logger.info("Saved Modification Times")

                    else:
                        if not error:
                            logger.info("No changes to segment " + agendaItem['name'])
                            returnCode = 0

                    '''
                    Check if this is the last agenda item that's complete.
                    If so, unblock the final output subjobs.
                    '''
                    agendaItem['resultpackage'] = {'Changed': render, 'segmentFile': segmentFilePath}

                    logger.info("Transcoder Segment Process Complete!\n")

            elif agendaItem['name'].startswith('Output'):
                '''
                Final Output Process
                    > Gather the output paths and changes for all of the segments
                    stored in their resultPackages.
                    > Check if there were changes.
                        True
                            > Continue Transcoding
                        False
                            > Skip Trancoding
                    > Load segmentOutputPaths from the agenda
                    > Check if segmentPaths exist.
                        True
                            > Continue Transcoding
                        False
                            > Skip Transcoding with error
                    > Check if output path is valid
                        True
                            > Continue Transcoding
                        False
                            > Skip Transcoding with error
                    > Check if we are still transcoding.
                        True
                            > Concatenate segments together.
                        False
                            > Skip
                    > Update the resultPackage with the outputPath.
                '''

                logger.info("Starting Final Output Process...\n")

                transcode = False
                errors = False

                dependantNames = agendaItem.get('package', {}).get('segmentSubjobs', '')
                logger.debug('Dependants Names: ' + str(dependantNames))

                dependantSegments = control.getSegments(dependantNames)
                logger.debug('Dependants Segments: ' + str(dependantSegments))

                finalOutputPath = agendaItem['package']['outputFile']
                if finalOutputPath:
                    transcode = True
                else:
                    errors = True

                if transcode:
                    changes = control.checkSegmentsForChanges(dependantSegments)
                    if not changes:
                        logger.info("No changes to segments.")
                    
                        if os.path.exists(str(finalOutputPath)):
                            logger.info('Final output movie already exists. ' + str(finalOutputPath))
                            returnCode = 0
                            transcode = False
                        else:
                            logger.info('Final output movie doesn\'t exist. ' + str(finalOutputPath))
                            transcode = True
                    else:
                        transcode = True

                if transcode:
                    segmentOutputPaths = control.getSegmentOutputPaths(dependantSegments)
                    if segmentOutputPaths:
                        transcode = True
                    else:
                        errors = True

                if transcode:
                    startFrame = control.getOutputStartFrame(dependantSegments)
                    logger.debug('Output Start Frame: ' + startFrame)

                if transcode:                    
                    finalOutputPath = control.getValidOutputPath(finalOutputPath)
                    if finalOutputPath:
                        transcode = True
                    else:
                        errors = True
                    
                if transcode:
                    cmd = control.getFinalOutputCMD(segmentOutputPaths, finalOutputPath, startFrame, 29.97, agendaItem)
                    returnCode = runCMD(cmd)
                    if returnCode != 0:
                        errors = True
                else:
                    logger.info('No changes to Final ' + agendaItem['name'])

                if not errors:
                    agendaItem['resultpackage'] = {'outputPaths': finalOutputPath}
                    logger.info('Transcoder Final ' + agendaItem['name'] + ' Completed Succesfully! (' + str(returnCode) + ')\n')
                else:
                    logger.info('Transcoder Final ' + agendaItem['name'] + ' Failed!' + str(returnCode) + ')\n')


            else:
                logger.error("Invalid Agenda Item")
                logger.error(str(agendaItem))

            '''
            Update the work status based on the return code.
            '''
            if returnCode == 0:
                agendaItem['status'] = 'complete'
            else:
                agendaItem['status'] = 'failed'

            ''' Report back the results to the Supervisor '''
            qb.reportwork(agendaItem)


    if jobstate == 'blocked':
        jobstate = 'pending'

    return jobstate


def cleanupJob(job, state):
    qb.reportjob(state)


def main():
    '''
    Run preflight checks to make sure the worker is ready and able to transcode.
    '''

    if TranscoderPreFlight.run():
        control = initControl()
        state = executeJob(control)
        cleanupJob(control, state)

if __name__ == "__main__":
    # f = tempfile.NamedTemporaryFile(delete=False)
    # cProfile.run('main()', f.name)
    main()
