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

'''
Set up the logging module.
'''
logging.basicConfig()
logger = logging.getLogger('Execute')
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

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
                print 'job %s state is now %s' % (qbJob['id'], jobstate)
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
                logger.info('Starting Transcoder Initialize Process...\n')

                returnCode = runCMD(control.getInitCMD(agendaItem))
                logger.debug('Initialize Exit Code: ' + str(returnCode))

                if returnCode == 0:
                    logger.info("Transcoder Initialize Process Complete!\n")
                else:
                    logger.error("Transcoder Initialization Failed! (Exit Code)\n")

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
                    logger.debug("Loading frame range from the work package...")
                    frameRangeString = agendaItem['package']['frameRange']
                    frameRange = sequenceTools.loadFrameRange(frameRangeString)

                    ''' Check for Missing Frames '''
                    logger.info("Checking for missing frames...")
                    mySequence = control.getSequence()
                    missingFrames = mySequence.getMissingFrames(frameRange)

                    if len(missingFrames) > 0:
                        logger.error('Missing frames!\n' + ','.join(missingFrames))
                        error = True

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
                            logger.info('Loading frames...')

                            logger.info('Retrieving current modification times...')
                            currentModTimes = mySequence.getModTimes(frameRange)

                            logger.info('Comparing modification times...')
                            compare = mySequence.compare(modTimeDBFile, frameRange, currentModTimes=currentModTimes)
                            logger.debug('Sequence Differences: ' + str(compare))

                            differences = compare['Added'] + compare['Deleted'] + compare['Modified']
                            logger.info('Differences: ' + str(len(differences)))

                            if len(differences) > 0:
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
                        cmd = control.getSegmentCMD(agendaItem)
                        returnCode = runCMD(cmd)
                        logger.debug('Initialize Exit Code: ' + str(returnCode))

                        if control.getSmartUpdate():
                            logger.info("Saving modification times...")
                            logger.debug("Saved ModTimes: " + str(currentModTimes))
                            control.job.sequence.saveModTimes(modTimeDBFile,
                                modTimeDict=currentModTimes, frameRange=frameRange)

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

                changes = control.checkSegmentsForChanges(dependantSegments)
                logger.debug('Changes: ' + str(changes))
                if changes:
                    transcode = True
                else:
                    logger.info('No changes for final output.')

                segmentOutputPaths = control.loadSegmentOutputPaths(dependantSegments)
                if segmentOutputPaths:
                    transcode = True
                else:
                    errors = True

                finalOutputPath = agendaItem['package']['outputFile']
                finalOutputPath = control.validateOutputFile(finalOutputPath)
                if finalOutputPath:
                    transcode = True
                else:
                    errors = True

                startFrame = control.getOutputStartFrame(dependantSegments)
                logger.debug('Output Start Frame: ' + startFrame)

                if transcode:
                    cmd = control.getFinalOutputCMD(segmentOutputPaths, finalOutputPath, startFrame, 29.97, agendaItem)
                    returnCode = runCMD(cmd)
                    logger.debug('Final Output CMD Exit Code: ' + str(returnCode))
                    if returnCode != 0:
                        logger.error('Non-zero exit code. ' + str(returnCode))
                        errors = True
                else:
                    logger.info('No changes to Final ' + agendaItem['name'])

                if not errors:
                    agendaItem['resultpackage'] = {'outputPaths': finalOutputPath}
                    logger.info("Transcoder Finalize Process Completed Succesfully!\n")
                else:
                    logger.info("Transcoder Finalize Process Failed!\n")


            else:
                logger.error("Invalid Work Item")
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
