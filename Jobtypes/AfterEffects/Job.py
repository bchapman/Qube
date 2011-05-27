'''
Job Class (Data)

Author: Brennan Chapman
Date: 5/24
Version: 1.0

Job class to store all related data
'''

import os
import time

class Job:
    def __init__(self, logger):
        self.projectPath = ''
        self.rqIndex = ''
        self.multProcs = False
        self.getDataFile = False
        self.prevFrame = ''
        self.qubejob = {}
        self.currAgena = {}
        self.aerenderwin = ''
        self.aerendermac = ''

        self.start = ''
        self.end = ''
        self.duration = ''
        self.currFrame = ''
        self.frameAverage = ''
        self.startTime = time.time()
        self.endTime = ''
        self.logger = logger

    # Convert the time() value to timecode
    def convertSecToTime(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    # Calculate the elapsed time for the render
    def getElapsedTime(self):
        if (self.endTime == ""):
            return time.time() - float(self.startTime)
        else:
            return float(self.endTime) - float(self.startTime)
    
    # Calculate the average render time per frame
    def getFrameAvg(self):
        if (self.endTime == ""):
            return float(self.getElapsedTime()) / float(self.currFrame)
        else:
            return float(self.getElapsedTime()) / float(self.end)
    
    # Calculate the percentage of the render that's complete
    def getPercentComplete(self):
        if (self.currFrame != "" and self.duration != ""):
            return str(int(float(self.currFrame) / float(self.duration) * 100))
        else:
            return str(0)
        
    # Calculate the remaining time in the render
    # based off the frame 
    def getRemainingTime(self):
        return self.getFrameAvg() * (float(self.duration) - float(self.currFrame))
    
    # Load Options from the qube package
    def loadOptions(self, qubejob):
        self.qubejob = qubejob
        pkg = qubejob.setdefault('package', {})
        self.projectPath = self.loadOption("projectPath", pkg.get('projectPath', ''), required=True, fullpath=True)
        self.rqIndex = self.loadOption('rqIndex', pkg.get('rqIndex', '')[0], required=False)
        self.multProcs = self.loadOption('renderProjectPath', pkg.get('multProcs', ''), required=False)
        self.aerenderwin = self.loadOption('aerenderwin', pkg.get('aerenderwin', ''), required=True)
        self.aerendermac = self.loadOption('aerendermac', pkg.get('aerendermac', ''), required=True)

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

    # Set Job as complete
    def setComplete(self):
        self.endTime = time.time()

    def __str__(self):
        result = "Job Details:\n"
        for key, value in vars(self).items():
            result += "\t" + str(key) + " : " + str(value) + "\n"
        return result
        
    def __repr__(self):
        return self.__str__()