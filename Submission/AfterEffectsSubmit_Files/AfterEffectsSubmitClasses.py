'''
After Effects Data Classes and Methods for After Effects v2 SimpleSubmit

Author: Brennan Chapman
Date: 5/25
Version: 1.0

Stores information related to the submission of jobs
using the After Effects v2 SimpleSubmit.
'''

# AERender paths
AERENDERPATH = {}
# Store paths as array of [ (Windows Path), (Mac Path) ]
# I only need CS5, so that's all I've loaded
AERENDERPATH['CS5'] = { 'win32':'c:/Program Files/Adobe/Adobe After Effects CS5/Support Files/aerender',\
                        'darwin':'/Applications/Adobe After Effects CS5/aerender'}

PATHTRANSLATIONS = {}
PATHTRANSLATIONS['/Volumes/theGrill/'] = '//10.1.111.161/theGrill/'
PATHTRANSLATIONS['g:/'] = '//10.1.111.161/theGrill/'

import wx
import os, sys
import re
import hashlib
import shutil
import shlex, subprocess
import inspect
import time

# sys.path.insert(0, '/Volumes/theGrill/.qube/SimpleCMDs/simplejson.egg')
sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import simplejson as json

# --------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------

class Controller:
    def __init__(self, logger):
        self.data = Data()
        self.logger = logger


    # Check to make sure the After Effects commandLineRenderer.jsx script is up to date
    def checkAERenderScript(self):
        # Get the hash of the host script
        hostAEScriptPath = os.path.dirname(self.getAERenderPath()) + '/Scripts/Startup/commandLineRenderer.jsx'
        hostAEScript = open(hostAEScriptPath, 'rb').read()
        hostAEScriptHash = hashlib.md5(hostAEScript).hexdigest()
    
        # Get the hash of the server script
        servAEScriptPath = os.path.dirname(inspect.getfile(inspect.currentframe())) + 'AfterEffectsSubmit_Files/commandLineRenderer.jsx'
        servAEScript = open(servAEScriptPath, 'rb').read()
        servAEScriptHash = hashlib.md5(servAEScript).hexdigest()
    
        if (hostAEScriptHash != servAEScriptHash):
            print 'After Effects Render Script Is Wrong Version'
            try:
                self.logger.info('Attempting To Update After Effects Render Script...')
            
                # Make a backup of the original
                # Add the time to the filename so if this method
                # runs multiple times, there is always an original
                # backup if needed.
                bkpFolder = os.path.dirname(hostAEScriptPath) + '/(backup)/'
                if not os.path.exists(bkpFolder):
                    os.mkdir(bkpFolder)
                bkpPath = bkpFolder + 'commandLineRenderer_' + str(int(time.time())) + '.jsx'
                shutil.move(hostAEScriptPath, bkpPath)
                self.logger.info('Backup Render Script: ' + bkpPath)
            
                shutil.copy(servAEScriptPath, hostAEScriptPath)
                ('After Effects Render Script Updated.')
                return True
            except:
                return False
        else:
            return True

    # Create the Data file to populate the dialog fields
    def makeDataFile(self):
        # Make sure After Effects has the commandLineRenderer.jsx script with
        # the added support for the makeDataFile flag to generate project data
        if self.checkAERenderScript():
            cmd = "\"" + self.getAERenderPath() + "\""
            cmd += " -project " + self.data.projectPath
            cmd += " -makedatafile"

            self.logger.info("Generating Data File...")
            self.logger.debug("Data File CMD: " + cmd)
            
            progDlg = wx.ProgressDialog ( 'Loading Project Data...', 'Lauching After Effects...', maximum = 100)
            p = subprocess.Popen(shlex.split(cmd))
            
            progDlg.Update( 25, 'Retrieving Data...')
            p.wait()
            self.logger.debug("Get Data File Exit Code: " + str(p.returncode))
            progDlg.Update( 100, 'Complete!')

            if (p.returncode != 123):
                raise("Error creating data file.")
                return False
            else:
                return True
        else:
            self.logger.error('Unable to create data file.')
            return False

    def makeCopyOfProject(self, sourcePath, subDirectory):
        #Create the time string to be placed on the end of the AE file
        fileTimeStr = time.strftime("_%m%d%y_%H%M%S", time.gmtime())

        #Copy the file to the project files folder and add the time on the end
        sourceFolderPath, sourceFileName = os.path.split(sourcePath)
        newFolderPath = os.path.join(sourceFolderPath, subDirectory)
        newFileName = os.path.splitext(sourceFileName)[0] + fileTimeStr + '.aep'
        newFilePath = os.path.join(newFolderPath, newFileName)

        # Make the new folder
        try:
            if not (os.path.exists(newFolderPath)):
                os.mkdir(newFolderPath)
        except:
            raise("Unable to create the folder " + newFolderPath)

        # Copy the file
        try:
            shutil.copy2(sourcePath, newFilePath)
            self.logger.info("Project file copied to " + newFilePath)
        except:
            raise("Unable to create a copy of the project under " + newFilePath)
            return ''
        
        return newFilePath

    # Load the aerender path based on os
    def getAERenderPath(self, version='CS5', sysOS=sys.platform):
        try:
            return AERENDERPATH[version][sysOS]
        except:
            print 'ERROR: No AERender path for OS: ' + sys.platform + ' and Version: ' + str(version)
            return None

    def getDataHash(self):
        return self.data.data['project']['hash']

    def getFileHash(self, filePath):
        fileData = open(filePath, 'rb').read()
        fileHash = hashlib.md5(fileData).hexdigest()
        return fileHash

    def getRQChoices(self):
        result = []
        for item in self.data.rqItems:
            result.append(str(item))
        return result

    def getRQIndex(self, index):
        for item in self.data.rqItems:
            if (int(item.index) == int(index)):
                return item
        return None
        
    def getRQItems(self):
        for item in self.data.data['rqItems']:
            self.data.rqItems.append(RQItem(item))
        return self.data.rqItems

    def loadData(self, data):
        # Reset Data
        self.data.data = {}
        self.data.rqItems = []
        
        self.data.data = data
        self.data.rqItems = self.getRQItems()

    # Method to check if a path is a sequence
    def isSequence(self, path):
        sequences = ['.png','.tga','.targa','.jpg','.jpeg','.bmp','.gif']
        ext = os.path.splitext(path)[1]
        if (ext in sequences):
            return True
        else:
            return False

    def loadDataFile(self, path):
        try:
            self.data.dataFile = path
            fileData = open(path, 'r')
            jsonData = json.load(fileData)
            self.loadData(jsonData)
            return True
        except:
            self.logger.warning('Unable to load data file.')
            return False

    # Use our own path translation
    # FUTURE: Implement Qube Submission Path Translation Setings
    def translatePath(self, path):
        # First switch all of the \ to /
        result = path.replace('\\', '/')
        
        # Then go through the list of path translations
        for key, value in PATHTRANSLATIONS.iteritems():
            try:
                sourceCaseMatch = re.findall(str(key), result, re.IGNORECASE)[0]
                result = result.replace(sourceCaseMatch, value)
            except:
                pass

        self.logger.debug('Translated: ' + path + ' -> ' + result)
        return result
        


# Class to store the After Effects Data from the data file
class Data:
    def __init__(self):
        self.data = {}
        self.rqItems = []
        self.dataFile = ''
        self.projectPath = ''
        self.selRQIndex = ''
    
    def __str__(self):
        result = str(self.data) + '\n'
        for item in self.rqItems:
            result += str(item) + '\n'
            result += '\t' + str(item.getOutputNames()) + '\n'
        return result

# Class to store the details about the render queue items in the aeData class
class RQItem():
    def __init__(self, rqItem):
        self.status = rqItem['status']
        self.index = rqItem['index']
        self.render = rqItem['render']
        self.comp = rqItem['comp']
        self.frameRate = rqItem['frameRate']
        self.compDuration = rqItem['compDuration']
        self.outputs = rqItem['outFilePaths']
        self.stopTime = rqItem['stopTime']
        self.startTime = rqItem['startTime']
        self.duration = rqItem['duration']
    
    def getOutputNames(self):
        outNames = []
        for output in self.outputs:
            outNames.append(os.path.basename(output))
        return outNames
    
    def getOutputPaths(self):
        return ",".join(self.outputs)
    
    def __str__(self):
        result = str(self.index)
        result += ". " + str(self.comp)
        return result
    
    def __repr__(self):
        return self.__str__()