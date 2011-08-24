'''
Transcoder Controller Class

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Controls the transcoding job process.
'''

import os
import sys
import inspect
import logging

sys.path.append('/Volumes/theGrill/.qube/Modules/')
import sequenceTools
import inputValidation
import Job
import qb

''' Constants '''
BLENDERLOCATION = '/Applications/blender.app/Contents/MacOS/blender'
BLENDERINITSCRIPT = 'Blender_InitSequence.py'
CATMOVIELOCATION = '/usr/local/bin/catmovie'
MUXMOVIELOCATION = '/usr/local/bin/muxmovie'
MODTIMEDBFILEPREFIX = '.DATA.'

''' Setup the logger. '''
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Control:
    '''
    Controller for the transcode process.
    '''

    def __init__(self, qubeJobObject):
        logger.debug('Initialize Controller')
        logger.debug('Incoming Qube Job Object: ' + str(qubeJobObject))
        self.job = Job.Job()
        self.errors = []
        self.job.qubejob = qubeJobObject
        self.loadOptions()

    def checkForErrors(self):
        if len(self.errors) > 0:
            return True
        else:
            return False

    def loadOptions(self):
        '''
        Load all the options from the qube job object into the Job model.
        '''

        job = self.job
        seqFile = self.loadOption('sequence', required=True, isFullPath=True)
        job.audioFile = self.loadOption('audioFile', required=False, isFullPath=True)
        job.outputFile = self.loadOption('outputFile', required=True, isFolderPath=True)
        job.preset = self.loadOption('preset', required=True, isFullPath=True)
        job.selfContained = self.loadOption('selfContained', isBool=True)
        job.smartUpdate = self.loadOption('smartUpdate', isBool=True)
        job.fillMissingFrames = self.loadOption('fillMissingFrames', isBool=True)
        job.transcoderFolder = self.loadOption('transcoderFolder', required=True)
        job.frameRange = self.loadOption('frameRange', required=True)

        if self.errors:
            logger.error('Unable to load job options:\n\t' + '\n\t'.join(self.errors))
        else:
            self.job.sequence = sequenceTools.Sequence(seqFile)
            logger.info('Job Options Loaded Successfully')
            
        logger.debug('Job after loading all options: \n' + str(job)) 

    def loadOption(self, name, required=False, isFullPath=False,
                    isFolderPath=False, isFloat=False, isBool=False):
        '''
        Load a job option with error checking and input validation.

        Process:
            > Load the value from the qube job package with the supplied name.
            > Validate the returned value.
        '''

        logger.debug('Loading Option:\n' + \
                        '\tName: ' + str(name) + '\n' + \
                        '\tRequired: ' + str(required) + '\n' + \
                        '\tisFullPath: ' + str(isFullPath) + '\n' + \
                        '\tisFolderPath: ' + str(isFolderPath) + '\n' + \
                        '\tisFloat: ' + str(isFloat) + '\n' + \
                        '\tisBool: ' + str(isBool) + '\n')

        pkg = self.job.qubejob.setdefault('package', {})

        result = ''
        errors = []
        try:
            result = str(pkg.get(name, ''))
            logger.debug('Package contents for ' + str(name) + ': ' + result)
        except:
            logger.debug('Unable to retrieve ' + name +
                        ' from the qube job package.')
            errors.append('Unable to retrieve ' + name +
                        ' from the qube job package.')

        if not errors:
            if result == '':
                if required:
                    errors.append('Required option ' + name + ' is empty.')
            else:
                if isFloat:
                    try:
                        result = float(result)
                    except:
                        errors.append('Invalid Float Value of ' + str(result) + ' for ' + name)

                if isBool:
                    try:
                        result = bool(result)
                    except:
                        errors.append('Invalid Boolean Value of ' + str(result) + ' for ' + name)

                if isFullPath:
                    try:
                        result = inputValidation.validateFile(result)
                    except:
                        errors.append('Invalid File Path for ' + name + ': ' + result)

                elif isFolderPath:
                    try:
                        result = inputValidation.validateFolder(result)
                    except:
                        errors.append('Invalid Folder Path\n' + name + ': ' + result)

        if errors:
            logger.debug('Error loading Option ' + str(name) + ': ' + str(result))
            self.errors.extend(errors)
        else:
            logger.debug('Returning Option ' + str(name) + ': ' + str(result))

        return result

    def getValidOutputPath(self, outputPath):
        '''
        Checks that an the outputPath is valid.
        If the file already exists, it is removed.
        If we can't remove it, choose another file name
        with an _# suffix.
        Returns the valid output path.
        '''

        inName, inExt = os.path.splitext(outputPath)
        resultPath = outputPath
        if os.path.exists(resultPath):
            count = 0
            while(True):
                count += 1
                try:
                    if os.path.exists(resultPath):
                        os.remove(resultPath)
                    break
                except:
                    logger.warning('Unable to delete existing file. ' + str(resultPath))
                    resultPath = inName + '_' + str(count) + inExt
                    logger.debug('Trying updated output path. ' + resultPath)
                if count > 5:
                    logger.error('Unable to find valid output path.')
                    resultPath = None
                    break

        return resultPath

    def getSequence(self):
        return self.job.sequence

    def getSegments(self, segmentNameList=[]):
        '''
        Load the all segments from the qube job object.
        '''

        agenda = qb.jobinfo(id=self.job.qubejob['id'], agenda=True)[0]['agenda']
        if (agenda == {}):
            logger.error('Job missing agenda')
            return None
            
        else:
            segments = []
            for subjob in agenda:
                if segmentNameList != []:
                    if subjob['name'] in segmentNameList:
                        segments.append(subjob)
                else:
                    segments.append(subjob)

            return segments

    def getCurrentSegment(self, work):
        '''
        Loads only the requested work segment.
        '''

        segments = []
        segments.append(work)

        return segments

    def getModTimeDBFile(self):
        '''
        Get the filepath to the modification database file.
        This contains the modification times for the latest renders of a sequence.
        Later this can be compared to find changes in the sequence.
        '''

        result = self.job.sequence.folder + '/' + MODTIMEDBFILEPREFIX
        result += os.path.splitext(os.path.basename(self.job.sequence.initFile))[0]
        result += '.db'
        return result

    def getSmartUpdate(self):
        return self.job.smartUpdate

    def getQubeJobObject(self):
        return self.job.qubejob

    def getInitCMD(self, work):
        '''
        Returns the initialize command which sets up a blender scene
        to transcode the sequence.
        Input:
            agenda work item from Qube

        Output Command Structure:
            BLENDERLOCATION Preset Script -- Sequence Destination Autofill
            
            Blender Preset File
                Blender project file that contains the preset settings
            Blender Initialization Script
                The script that runs inside of blender to generate the template.

            Separate the script arguments with '--'

            Sequence File
                Single file from the image sequence
            Destination for blender file
            Autofill missing frames
                Whether the autofill the missing frames with surrounding frames.
        '''

        cmd = '\'' + BLENDERLOCATION + '\''
        cmd += ' -b \'' + self.job.preset + '\''
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        cmd += ' -P \'' + cwd + '/' + BLENDERINITSCRIPT + '\''

        cmd += ' -- '
        cmd += ' \'' + self.job.sequence.initFile + '\''
        cmd += ' \'' + self.getBlendFile() + '\''
        cmd += ' \'' + str(self.job.fillMissingFrames) + '\''

        return cmd

    def getSegmentCMD(self, work):
        '''
        Returns the command to render the segment using blender.

        Template: blender -b blendfile -x 1 -s startFrame -e endFrame -o outputFile -a
        '''

        workPkg = work.setdefault('package', {})

        segmentFile = workPkg.get('segmentFile', '')
        segmentFile = self.getValidOutputPath(segmentFile)
        
        if segmentFile:
            cmd = '\'' + BLENDERLOCATION + '\''
            cmd += ' -b \'' + self.getBlendFile() + '\''
            cmd += ' -x 1' # Use an extension on the end of the file

            ''' Get the start and end frames from the work item name. '''
            startFrame, endFrame = workPkg.get('frameRange', '').split('-')

            cmd += ' -s ' + startFrame
            cmd += ' -e ' + endFrame
            cmd += ' -o ' + segmentFile
            cmd += ' -a'

        return cmd

    def getFinalOutputCMD(self, segmentOutputPaths, finalOutputPath, startFrame,
                        frameRate, work):
        '''
        Returns the Finalize command to put together a final quicktime.
        Steps:
            1) Check if any of the related segments had changes.
                If not, skip finalizing this segment.
            1) Create a reference movie containing all the segments
                This uses catmovie.
            2) Create the final movie adding audio if necessary.
                If the self-contained was checked, this is also applied.
                If the render is split up, audio will be split as well.
                This uses muxmovie.

        *Name of the output files is defined by the name of the agenda item.
        *Only segments listed in the agenda item's package are used in the final quicktime.

        Command Templates:
            catmovie -o tempOutputFile - (Segments)
            muxmovie -o finalOutputFile (-self-contained) (-startAt SECONDS audioFile) tempOutputFile
        '''

        cmd = ''
        
        catOutput = self.getTempOutputFile(work)
        catCMD = '\'' + CATMOVIELOCATION + '\''
        catCMD += ' -o \'' + catOutput + '\''
        catCMD += ' -'
        catCMD += ' '.join(segmentOutputPaths)

        muxCMD = '\'' + MUXMOVIELOCATION + '\''
        muxCMD += ' -o \'' + finalOutputPath + '\''
        if self.job.selfContained:
            muxCMD += ' -self-contained -trimToShortestTrack'
        if self.job.audioFile:
            ''' Calculate the offset start time for the audio. '''
            audioStart = float(startFrame)/float(frameRate)
            muxCMD += ' \'' + str(self.job.audioFile) + '\' -startAt ' + str(audioStart)
        muxCMD += ' ' + catOutput

        cmd += '/bin/bash -c "' + catCMD + '; ' + muxCMD + '"'
        
        return cmd

    def checkSegmentsForChanges(self, segments):
        '''
        Takes a list of segment subjobs and checks the result package of each
        for the changes property.  If changes are found to any of the
        segments the return in True, otherwise it's False.
        '''
        
        changes = False
        for segment in segments:
            if not (segment['name'].startswith(('Initialize', 'Output'))):
                segmentChanges = bool(segment.get('resultpackage', {}).get('Changed', ''))
                logger.debug(segment['name'] + ' - Changes: ' + str(segmentChanges))
                if segmentChanges:
                    changes = True
        
        return changes
    
    def getSegmentOutputPaths(self, segments):
        '''
        Takes a list of segment subjobs and checks the result package of each
        for the segmentFile property.  These are added to an array and returned.
        '''
        
        logger.debug('outputPaths|segments: ' + str(segments))
        outputPaths = []
        for segment in segments:
            if not (segment['name'].startswith(('Initialize', 'Output'))):
                segmentFile = segment.get('resultpackage', {}).get('segmentFile', '')
                outputPaths.append(segmentFile)
                logger.debug(segment['name'] + ' - segmentFile: ' + segmentFile)
        
        error = False
        logger.debug('outputPaths: ' + str(outputPaths))
        for path in outputPaths:
            if not os.path.exists(path):
                logger.error('Segment Output doesn\'t exist: ' + path)
                error = True
        
        if error:
            return None
        else:
            return outputPaths
        
    def getOutputStartFrame(self, segments):
        '''
        Takes a list of segment subjobs and checks the package of each for the
        frameRange property.  All of the frame ranges are then returned
        as a list.
        '''
        
        startFrame = None
        frameRangeString = segments[0].get('package', {}).get('frameRange', '')
        startFrame = frameRangeString.split('-')[0]
        logger.debug('Start Frame: ' + str(startFrame))

        return startFrame

    def getBlendFile(self):
        '''
        Returns a full path for the blender file to use
        when transcoding.
        Names are in the form of QUBEID-INITIALFRAME.blend
        '''

        fileName = str(self.getQubeJobObject().get('id', ''))
        fileName += '-' + os.path.splitext(os.path.basename(self.job.sequence.initFile))[0] + '.blend'
        blenderFolder = os.path.join(self.job.transcoderFolder, 'Blender/')
        result = os.path.join(blenderFolder, fileName)

        self.makeFolders(blenderFolder)

        logger.debug('getBlendFile result: ' + str(result))

        return result

    def getSegmentOutputFile(self, fileName):
        '''
        Returns a full path for a segment based on the name of the file.
        '''

        segmentsFolder = os.path.join(self.job.transcoderFolder, 'Segments/')
        result = os.path.join(segmentsFolder, fileName)

        self.makeFolders(segmentsFolder)

        return result

    def getTempOutputFile(self, work):
        '''
        Returns a full path for a temporary output file for catmovie
        based on the supplied work item's name.
        We'll place this under the segments folder.
        '''

        fileName = os.path.basename(work['package'].get('outputFile', ''))
        result = self.getSegmentOutputFile(fileName)

        return result

    def makeFolders(self, folderPath):
        try:
            logger.debug('Creating folder ' + str(folderPath) + '...')
            os.makedirs(folderPath)
        except:
            logger.debug('Folder already exists ' + str(folderPath) + '.')

    def __str__(self):
        result = 'Job Details:\n'
        for key, value in vars(self).items():
            result += '\t' + str(key) + ' : ' + str(value) + '\n'
        return result

    def __repr__(self):
        return self.__str__()
