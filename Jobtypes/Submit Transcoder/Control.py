'''
Transcoder Controller Class

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Controls the transcoding job process.
'''

import os, sys, time, inspect

sys.path.append('../../Modules/')
import sequenceTools
import inputValidation
import logging
import Job

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

        seqFile = self.loadOption('sequence', required=True, isFullPath=True)
        self.job.audioFile = self.loadOption('audioFile', required=False, isFullPath=True)
        self.job.outputFile = self.loadOption('outputFile', required=True, isFolderPath=True)
        self.job.preset = self.loadOption('preset', required=True, isFullPath=True)
        self.job.resolution = self.loadOption('resolution', required=True)
        self.job.frameRate = self.loadOption('frameRate', isFloat=True, required=True)
        self.job.selfContained = self.loadOption('selfContained', isBool=True)
        self.job.smartUpdate = self.loadOption('smartUpdate', isBool=True)
        self.job.transcoderFolder = self.loadOption('transcoderFolder', required=True)
        
        if self.errors:
            logger.error('Unabled to load Options:' + '\n'.join(self.errors))
        else:
            self.job.sequence = sequenceTools.Sequence(seqFile)

    def loadOption(self, name, required=False, isFullPath=False, isFolderPath=False, isFloat=False, isBool=False):
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
            logger.debug('Unable to retrieve ' + name + ' from the qube job package.')
            errors.append('Unable to retrieve ' + name + ' from the qube job package.')
        
        if errors:
            if result == '':
                if required:
                    errors.append('Required option ' + name + ' is empty.')
                    
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
            else:
                if isFullPath:
                    result = inputValidation.validateFile(result)
                    if not result:
                        errors.append('Invalid File Path\n' + name + ': ' + result)
                elif isFolderPath:
                    result = inputValidation.validateFolder(result)
                    if not result:
                        errors.append('Invalid Folder Path\n' + name + ': ' + result)

        if errors:
            logger.debug('Error loading Option ' + str(name) + ': ' + str(result))
            self.errors.extend(errors)
        else:
            logger.debug('Returning Option ' + str(name) + ': ' + str(result))

        return result

    def getAllSegments(self):
        '''
        Load the all segments from the qube job object.
        '''
        
        agenda = self.qubejob.get('agenda', {})
        if (agenda == {}):
            logger.error('Job missing agenda')
            sys.exit(1)
        else:
            segments = []
            for subjob in agenda:
                segments.append(subjob)
            
            return segments

    def getCurrentSegment(self, work):
        '''
        Loads only the requested work segment.
        '''
        
        segments = []
        segments.append(work)
        
        return segments

    #  Old
    # def getCMD(self, work):
    #     '''
    #     Returns the command for the subjob based on the work item.
    #     '''
    #     
    #     result = ''
    #     if (work['name'] == 'Initialize'): result = self.getInitCMD(work)
    #     elif (str(work['name']).endswith('.mov')): result = self.getFinalizeCMD(work)
    #     elif (work['name'] != ''):
    #         result = self.getSegmentCMD(work)
    #     else:
    #         logger.error('Weird Work:' + str(work))
    #         logger.error('Weird Work Status: ' + str(work['status']))
    #         result = 'ls'
    # 
    #     return result

    def getModTimeDBFile(self):
        '''
        Get the filepath to the modification database file.
        This contains the modification times for the latest renders of a sequence.
        Later this can be compared to find changes in the sequence.
        '''

        result = self.sequence.folder + '/' + MODTIMEDBFILEPREFIX + os.path.splitext(os.path.basename(self.sequence.initFile))[0] + '.db'
        return result

    def getInitCMD(self, work):
        '''
        Returns the initialize command which sets up a blender scene
        to transcode the sequence.
        '''
        
        cmd = '\'' + BLENDERLOCATION + '\''
        
        ''' Add the preset blender file which has the base conversion settings. '''
        cmd += ' -b \'' + self.job.preset + '\''
        
        '''
        Add the Blender_InitSequence script which runs
        inside of blender once it's launched.
        '''
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        cmd += ' -P \'' + cwd + '/' + BLENDERINITSCRIPT + '\''

        '''
        Add the rest of the conversion settings as arguments after
        the seperator '--'
            1 - Sequence Folder
            2 - Resolution
            3 - Frame Rate(ex: 100x100)
            4 - Where to save blender file
            5 - Audio File
        '''
        cmd += ' -- '
        cmd += ' \'' + self.job.sequence.initFile + '\''
        cmd += ' \'' + self.job.resolution + '\''
        cmd += ' \'' + self.job.frameRate + '\''
        cmd += ' \'' + self.getBlendFile() + ' \''
        if self.job.audioFile:
            cmd += ' \'' + self.job.audioFile + '\''
        
        return cmd

    def getSegmentCMD(self, work):
        '''
        Returns the command to render the segment using blender.
        
        Template: blender -b blendfile -x 1 -s startFrame -e endFrame -o outputFile -a
        '''
        
        workPkg = work.setdefault('package', {})

        cmd = '\'' + BLENDERLOCATION + '\''
        cmd += ' -b \'' + self.getBlendFile() + '\''
        cmd += ' -x 1' # Use an extension on the end of the file

        ''' Get the start and end frames from the work item name. '''
        startFrame, endFrame = work.get('name', '').split('-')

        cmd += ' -s ' + startFrame
        cmd += ' -e ' + endFrame
        cmd += ' -o ' + self.getSegmentOutputFile(workPkg.get('outputName', ''))
        cmd += ' -a'
        
        return cmd

    def getSmartUpdate(self):
        return self.job.smartUpdate
    
    def getQubeJobObject(self):
        return self.job.qubejob

    def getFinalizeCMD(self, work):
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

        allSegments = self.getAllSegments()
        dependantNames = work.get('package', {}).get('Dependencies', {}).split(',')
        logger.debug('Dependants: ' + str(dependantNames))
        
        ''' Only add the files that are dependants. '''
        segments = ''
        changes = False
        for segment in allSegments:
            if not (segment['name'].endswith(('Initialize', '.mov'))):
                if segment['name'] in dependantNames:
                    fileName = segment.get('package', {}).get('outputName', '')
                    segments += ' \'' + self.getSegmentOutputFile(fileName) + '\''
                    segChanges = segment.get('resultpackage', {}).get('Changed', '0')
                    if segChanges != '0': changes = True
                    logger.debug('Found Dependent: ' + str(segment['name']))
                    logger.debug('Changes: ' + str(changes))

        cmd = ''
        logger.debug('Anything changed? ' + str(changes))
        finalOutputFile = self.getFinalOutputFile(work)
        logger.debug('Final Output File: ' + str(finalOutputFile))
        finalOutputFileExists = os.path.exists(finalOutputFile)
        logger.debug('Final Output File Exists: ' + str(finalOutputFileExists))
        if not changes and finalOutputFileExists:
            cmd += 'echo "No Changes"'
        else:
            catOutput = self.getTempOutputFile(work)
            catCMD = '\'' + CATMOVIELOCATION + '\''
            catCMD += ' -o \'' + catOutput + '\''
            catCMD += ' -'
            catCMD += segments

            muxCMD = '\'' + MUXMOVIELOCATION + '\''
            muxCMD += ' -o \'' + finalOutputFile + '\''
            if self.selfContained: muxCMD += ' -self-contained -trimToShortestTrack'
            if self.audioFile:
                ''' Calculate the offset start time for the audio. '''
                startFrame, endFrame = dependantNames[0].split('-')
                logger.debug(work.get('name', '') + ' start frame is ' + str(startFrame))
                frameRate = self.frameRate
                audioStart = float(startFrame)/float(frameRate)
                audioEnd = float(endFrame)/float(frameRate)
                muxCMD += ' \'' + str(self.audioFile) + '\' -startAt ' + str(audioStart)
            muxCMD += ' ' + catOutput

            cmd += '/bin/bash -c "' + catCMD + '; ' + muxCMD + '"'

        return cmd

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

        return result

    def getSegmentOutputFile(self, fileName):
        '''
        Returns a full path for a segment based on the name of the file.
        '''
        
        segmentsFolder = os.path.join(self.transcoderFolder, 'Segments/')
        result = os.path.join(segmentsFolder, fileName)
        
        self.makeFolders(segmentsFolder)
        
        return result

    def getFinalOutputFile(self, work):
        '''
        Returns a full path for a final output file based
        on the supplied work item's name.
        '''
        
        fileName = work.get('name', '')
        finalFolder = os.path.dirname(self.outputFile)
        result = os.path.join(finalFolder, fileName)
        
        self.makeFolders(finalFolder)
        
        return result

    def getTempOutputFile(self, work):
        '''
        Returns a full path for a temporary output file for catmovie
        based on the supplied work item's name.
        We'll just use the segments folder.
        '''
        
        fileName = work.get('name', '')
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