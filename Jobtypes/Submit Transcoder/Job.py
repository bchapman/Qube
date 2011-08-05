'''
Transcoder Job Class (Data)

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Job class to store all related data transcoding.
'''

import os, sys, time, inspect

sys.path.append('/Volumes/theGrill/.qube/Modules/')
import sequenceTools

''' Constants '''
BLENDERLOCATION = '/Applications/blender.app/Contents/MacOS/blender'
BLENDERINITSCRIPT = 'Blender_InitSequence.py'
CATMOVIELOCATION = '/usr/local/bin/catmovie'
MUXMOVIELOCATION = '/usr/local/bin/muxmovie'
MODTIMEDBFILEPREFIX = '.DATA.'

class Job:
    def __init__(self, logger):
        ''' Input Settings '''
        self.sequence = ''
        self.audioFile = ''
        self.frameRange = []
        
        ''' Output Settings '''
        self.outputFile = ''
        self.preset = ''
        self.resolution = ''
        self.frameRate = ''
        self.transcoderFolder = ''

        self.selfContained = True
        self.smartUpdate = True
        
        ''' Other Settings '''
        self.qubejob = {}
        self.logger = logger

    def loadOptions(self, qubejob):
        '''
        Load all the options from the qube job object into the Job class.
        '''
        
        self.qubejob = qubejob
        pkg = qubejob.setdefault('package', {})
        
        seqFile = self.loadOption('sequence', pkg.get('sequence', ''), required=True, fullpath=True)
        self.sequence = sequenceTools.Sequence(seqFile)
        
        self.audioFile = self.loadOption('audioFile', pkg.get('audioFile', ''), required=False, fullpath=True)
        
        self.outputFile = self.loadOption('outputFile', pkg.get('outputFile', ''), required=True, folderpath=True)
        self.preset = self.loadOption('preset', pkg.get('preset', ''), required=True, fullpath=True)
        self.resolution = self.loadOption('resolution', pkg.get('resolution', ''), required=True)
        self.frameRate = self.loadOption('frameRate', pkg.get('frameRate', ''), required=True)
        
        self.selfContained = self.loadOption('selfContained', pkg.get('selfContained', True))
        self.smartUpdate = self.loadOption('smartUpdate', pkg.get('smartUpdate', True))

        self.transcoderFolder = self.loadOption('transcoderFolder', pkg.get('transcoderFolder', ''), required=True)


    def loadOption(self, name, option, required=False, fullpath=False, folderpath=False):
        '''
        Load a job option with error checking and input validation.
        '''
        
        if (option != ''):
            if (fullpath ==True or folderpath == True):

                # Expand variables in path
                newPath = os.path.expandvars(option)
                newPath = os.path.expanduser(newPath)

                if (fullpath == True):
                    tmpPath = newPath
                else:
                    tmpPath = os.path.dirname(newPath)

                if (os.path.exists(tmpPath)):
                    return newPath
                else:
                    self.logger.error('Invalid path for ' + name + ' : ' + option)
                    exit(64)
            else:
                return option
        else:
            if (required != True):
                return ''
            else:
                self.logger.error('Missing value for ' + name)
                exit(64)

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

    def getCMD(self, work):
        '''
        Returns the command for the subjob based on the work item.
        '''
        
        result = ''
        if (work['name'] == 'Initialize'): result = self.getInitCMD(work)
        elif (str(work['name']).endswith('.mov')): result = self.getFinalizeCMD(work)
        elif (work['name'] != ''):
            result = self.getSegmentCMD(work)
        else:
            self.logger.error('Weird Work:' + str(work))
            self.logger.error('Weird Work Status: ' + str(work['status']))
            result = 'ls'

        return result

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
        cmd += ' -b \'' + self.preset + '\''
        
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
        cmd += ' \'' + self.sequence.initFile + '\''
        cmd += ' \'' + self.resolution + '\''
        cmd += ' \'' + self.frameRate + '\''
        cmd += ' \'' + self.getBlendFile() + ' \''
        if self.audioFile:
            cmd += ' \'' + self.audioFile + '\''
        
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
        self.logger.debug('Dependants: ' + str(dependantNames))
        
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
                    self.logger.debug('Found Dependent: ' + str(segment['name']))
                    self.logger.debug('Changes: ' + str(changes))

        cmd = ''
        self.logger.debug('Anything changed? ' + str(changes))
        finalOutputFile = self.getFinalOutputFile(work)
        self.logger.debug('Final Output File: ' + str(finalOutputFile))
        finalOutputFileExists = os.path.exists(finalOutputFile)
        self.logger.debug('Final Output File Exists: ' + str(finalOutputFileExists))
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
                self.logger.debug(work.get('name', '') + ' start frame is ' + str(startFrame))
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

        fileName = str(self.qubejob.get('id', ''))
        fileName += '-' + os.path.splitext(os.path.basename(self.sequence.initFile))[0] + '.blend'        
        blenderFolder = os.path.join(self.transcoderFolder, 'Blender/')
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
            self.logger.debug('Creating folder ' + str(folderPath) + '...')
            os.makedirs(folderPath)
        except:
            self.logger.debug('Folder already exists ' + str(folderPath) + '.')


    def __str__(self):
        result = 'Job Details:\n'
        for key, value in vars(self).items():
            result += '\t' + str(key) + ' : ' + str(value) + '\n'
        return result


    def __repr__(self):
        return self.__str__()