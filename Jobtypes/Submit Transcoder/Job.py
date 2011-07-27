'''
Transcoder Job Class (Data)

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Job class to store all related data
'''

import os, sys, time, inspect

sys.path.append('/Volumes/theGrill/.qube/Modules/')
import sequenceTools

BLENDERLOCATION = "/Applications/blender.app/Contents/MacOS/blender"
BLENDERINITSCRIPT = "Blender_InitSequence.py"
CATMOVIELOCATION = "/usr/local/bin/catmovie"
MUXMOVIELOCATION = "/usr/local/bin/muxmovie"
HASHCODEFILEPREFIX = '.DATA.'

class Job:
    def __init__(self, logger):
        # Input Settings
        self.sequence = ''
        self.audioFile = ''
        
        # Output Settings
        self.outputFile = ''
        self.preset = ''
        self.resolution = ''
        self.frameRate = ''

        self.selfContained = True
        self.smartUpdate = True
        
        # Other Settings
        self.qubejob = {}
        self.logger = logger


    # Load Options from the qube package
    def loadOptions(self, qubejob):
        self.qubejob = qubejob
        pkg = qubejob.setdefault('package', {})
        
        seqFile = self.loadOption("sequence", pkg.get('sequence', ''), required=True, fullpath=True)
        self.sequence = sequenceTools.Sequence(seqFile)
        
        self.audioFile = self.loadOption("audioFile", pkg.get('audioFile', ''), required=False, fullpath=True)
        
        self.outputFile = self.loadOption("outputFile", pkg.get('outputFile', ''), required=True, folderpath=True)
        self.preset = self.loadOption("preset", pkg.get('preset', ''), required=True, fullpath=True)
        self.resolution = self.loadOption("resolution", pkg.get('resolution', ''), required=True)
        self.frameRate = self.loadOption("frameRate", pkg.get('frameRate', ''), required=True)
        
        self.selfContained = self.loadOption("selfContained", pkg.get('selfContained', True))
        self.smartUpdate = self.loadOption("smartUpdate", pkg.get('smartUpdate', True))


    # Load an option with error checking
    def loadOption(self, name, option, required=False, fullpath=False, folderpath=False):
        if (option != ""):
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
                    self.logger.error("Invalid path for " + name + " : " + option)
                    exit(64)
            else:
                return option
        else:
            if (required != True):
                return ""
            else:
                self.logger.error("Missing value for " + name)
                exit(64)


    # Load the segments from the qube job
    # Agenda Format (id : purpose : name):
    #   0 : Initialize : "Initialize"
    #   1-n : Segments : startFrame-endFrame
    #       Segment package includes outputPath    
    #   n+1 : Finalize : "Finalize"
    def getAllSegments(self):
        segments = []
        
        # Load the qube job agenda
        agenda = self.qubejob.get('agenda', {})
        if (agenda == {}):
            logger.error('Job missing agenda')
            sys.exit(1)
        else:
            # Add each subjob to the segments array
            for subjob in agenda:
                segments.append(subjob)
            
            return segments


    # Loads only the requested work segment
    def getCurrentSegment(self, work):
        segments = []
        segments.append(work)
        
        return segments

    # Choose which command to use based on the work item
    def getCMD(self, work):
        result = ''
        if (work['name'] == 'Initialize'): result = self.getInitCMD(work)
        elif (str(work['name']).endswith('.mov')): result = self.getFinalizeCMD(work)
        elif (work['name'] != ''):
            result = self.getSegmentCMD(work)
        else:
            self.logger.error("Weird Work:" + str(work))
            self.logger.error("Weird Work Status: " + str(work['status']))
            result = 'ls'

        return result

    def getHashFile(self):
        '''
        Get the filepath to the hashfile.
        This contains the md5 hash codes for the latest renders of a sequence.
        Later this can be compared to find changes in the sequence.
        '''
        result = self.sequence.folder + '/' + HASHCODEFILEPREFIX + os.path.splitext(os.path.basename(self.sequence.initFile))[0] + '.db'
        return result

    # Setup the initialize command to setup the blender file for transcoding
    def getInitCMD(self, work):
        cmd = '\'' + BLENDERLOCATION + '\''
        
        # Add the preset blender file which has the base conversion settings
        cmd += ' -b \'' + self.preset + '\''
        
        # Add the initialization script
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # Current working directory
        cmd += ' -P \'' + cwd + '/' + BLENDERINITSCRIPT + '\''
        
        # Add the rest of the conversion settings as arguments
        #   1-Sequence Folder
        #   2-Resolution
        #   3-Frame Rate(ex: 100x100)
        #   4-Where to save blender file
        cmd += ' -- ' # Separates the python arguments from blender arguments
        cmd += ' \'' + self.sequence.initFile + '\''
        cmd += ' \'' + self.resolution + '\''
        cmd += ' \'' + self.frameRate + '\''
        cmd += ' \'' + self.getTempBlendSceneName(work) + '\''
        if self.audioFile:
            cmd += ' \'' + self.audioFile + '\''
        
        return cmd

    
    # Generate the commands to render each segment based on start and end frames
    # using blender.
    def getSegmentCMD(self, work):
        workPkg = work.setdefault('package', {})
        # Template: blender -b blendfile -x 1 -s startFrame -e endFrame -o outputFile -a
        cmd = '\'' + BLENDERLOCATION + '\''
        cmd += ' -b \'' + self.getTempBlendSceneName() + '\''
        cmd += ' -x 1' # Use an extension on the end of the file
        # Get the start and end frames from the Work name
        self.logger.info("Work: " + str(work))
        start, end = work.get('name', '').split('-')
        cmd += ' -s ' + start
        cmd += ' -e ' + end
        cmd += ' -o ' + workPkg.get('outputPath', '')
        cmd += ' -a'
        
        return cmd


    def getFinalizeCMD(self, work):
        '''
        Setup the finalize command to use QTCoffee's catmovie to merge
        the segments together.
        
        Template: catmovie (-self-contained) -o outputFile - (Segments)
        '''

        segments = self.getAllSegments()

        '''
        Put all the segments together using catmovie from QTCoffee.
        Use the names of the final agenda items for the output files.
        '''
        finalizeOutput = os.path.dirname(self.outputFile) + '/' + work['name']
        if (self.audioFile):
            segmentFolder = segments[2].get('package',{}).get('outputPath', '')
            catMovieOutput = os.path.dirname(segmentFolder) + '/' + os.path.basename(finalizeOutput)
            
        cmd = '/bin/bash -c "\'' + CATMOVIELOCATION + '\''
        if (self.selfContained): cmd += ' -self-contained'
        cmd += ' -o \'' + finalizeOutput + '\''
        
        # If audio file wasn't included, apply the self-contained attribute here if required.
        if not (self.audioFile):
            cmd += ' -self-contained'
        
        # Add the segments
        cmd += ' -' # End argument processing

        dependants = work.get('package', {}).get('Dependencies', {})
        self.logger.info("Dependants: " + str(dependants))
        for segment in segments:
            if not (segment['name'].endswith(('Initialize', 'Finalize'))):
                if segment['name'] in dependants:
                    cmd += ' ' + segment.get('package', {}).get('outputPath', '')
        cmd += '"'

        return cmd


    # Generate the blender initialization scene name based on the qube job number
    # and the output file name.
    def getTempBlendSceneName(self, work):
        result = work.get('package', {}).get('sceneFolder', '/tmp/')
        result += '/' + str(self.qubejob.get('id', ''))
        result += '-' + os.path.splitext(os.path.basename(self.outputFile))[0] + '.blend'
        
        return result


    def __str__(self):
        result = "Job Details:\n"
        for key, value in vars(self).items():
            result += "\t" + str(key) + " : " + str(value) + "\n"
        return result


    def __repr__(self):
        return self.__str__()