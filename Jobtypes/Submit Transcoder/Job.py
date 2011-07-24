'''
Transcoder Job Class (Data)

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Job class to store all related data
'''

import os
import time
import inspect

BLENDERLOCATION = "/Applications/blender.app/Contents/MacOS/blender"
BLENDERINITSCRIPT = "Blender_InitSequence.py"
CATMOVIELOCATION = "/usr/local/bin/catmovie"


class Job:
    def __init__(self, logger):
        # Input Settings
        self.sequenceFolder = ''
        self.audioFile = ''
        
        # Output Settings
        self.outputFile = ''
        self.blenderScenePreset = ''
        self.resolution = ''
        self.frameRate = ''

        self.selfContained = True
        
        # Other Settings
        self.qubejob = {}
        self.logger = logger


    # Load Options from the qube package
    def loadOptions(self, qubejob):
        self.qubejob = qubejob
        pkg = qubejob.setdefault('package', {})
        self.sequenceFolder = self.loadOption("sequenceFolder", pkg.get('sequenceFolder', ''), required=True, fullpath=True)
        self.audioFile = self.loadOption("audioFile", pkg.get('audioFile', ''), required=False, fullpath=True)
        
        self.outputFile = self.loadOption("outputFile", pkg.get('outputFile', ''), required=True, folderpath=True)
        self.blenderScenePreset = self.loadOption("blenderScenePreset", pkg.get('blenderScenePreset', ''), required=True, fullpath=True)
        self.resolution = self.loadOption("resolution", pkg.get('resolution', ''), required=True)
        self.frameRate = self.loadOption("frameRate", pkg.get('frameRate', ''), required=True)
        
        self.selfContained = self.loadOption("selfContained", pkg.get('selfContained', ''))


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
        if (work['name'] == 'Initialize'): result = self.getInitCMD()
        elif (work['name'] == 'Finalize'): result = self.getFinalizeCMD()
        else: result = self.getSegmentCMD(work)

        return result

    # Setup the initialize command to setup the blender file for transcoding
    def getInitCMD(self):
        cmd = '\'' + BLENDERLOCATION + '\''
        
        # Add the preset blender file which has the base conversion settings
        cmd += ' -b \'' + self.blenderScenePreset + '\''
        
        # Add the initialization script
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) # Current working directory
        cmd += ' -P \'' + cwd + '/' + BLENDERINITSCRIPT + '\''
        
        # Add the rest of the conversion settings as arguments
        #   1-Sequence Folder
        #   2-Resolution
        #   3-Frame Rate(ex: 100x100)
        #   4-Where to save blender file
        cmd += ' -- ' # Separates the python arguments from blender arguments
        cmd += ' \'' + self.sequenceFolder + '\''
        cmd += ' \'' + self.resolution + '\''
        cmd += ' \'' + self.frameRate + '\''
        cmd += ' \'' + self.getTempBlendSceneName() + '\''
        
        return cmd

    
    # Generate the commands to render each segment based on start and end frames
    # using blender.
    def getSegmentCMD(self, work):
        workPkg = work.setdefault('package', {})
        # Template: blender -b blendfile -x 1 -s startFrame -e endFrame -o outputFile -a
        cmd = '\'' + BLENDERLOCATION + '\''
        cmd += ' -b \'' + self.getTempBlendSceneName() + '\''
        cmd += ' -x 1' # Use an extension on the end of the file
        cmd += ' -s ' + workPkg.get('startFrame', '')
        cmd += ' -e ' + workPkg.get('endFrame', '')
        cmd += ' -o ' + workPkg.get('outputPath', '')
        cmd += ' -a'
        
        return cmd


    # Setup the finalize command to use QTCoffee's catmovie to merge
    # all the segments together
    def getFinalizeCMD(self):
        #Template: catmovie (-self-contained) (audioFile -track "Sound Track") -o outputFile -track "Video Track" (Segments)
        cmd = '\'' + CATMOVIELOCATION + '\''
        if (self.selfContained): cmd += ' -self-contained'
        cmd += ' -o \'' + self.outputFile + '\''
        if (self.audioFile != ''): cmd += ' \'' + self.audioFile + '\' -track \'Sound Track\''
        
        # Add the segments
        cmd += ' -track \'Video Track\'' # Only use the video tracks from the segments
        cmd += ' -' # End argument processing

        segments = self.getAllSegments()
        for segment in segments:
            if not (segment['name'].endswith(('Initialize', 'Finalize'))):
                cmd += ' ' + segment.get('package', {}).get('outputPath', '')

        return cmd


    # Generate the blender initialization scene name based on the qube job number
    # and the output file name.
    def getTempBlendSceneName(self):
        result = os.path.dirname(self.outputFile)
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