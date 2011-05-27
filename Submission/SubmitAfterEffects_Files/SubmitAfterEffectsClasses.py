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

# Dependent JSX Scripts
SCRIPTS = {}
SCRIPTS['commandLineRenderer.jsx'] = 'Startup/commandLineRenderer.jsx'
SCRIPTS['Qube_Tools.jsx'] = 'Startup/Qube_Tools.jsx'
SCRIPTS['Qube_Submit.jsx'] = 'Qube_Submit.jsx'

import wx
import os, sys
import re
import hashlib
import shutil
import shlex, subprocess
import inspect
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/simplejson.egg')
import simplejson as json

# --------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------

class Controller:
    def __init__(self, logger):
        self.data = Data()
        self.logger = logger

    def compareHash(self, fileA, fileB):
        # Get the hash of fileA
        fileAContents = open(fileA, 'rb').read()
        fileAHash = hashlib.md5(fileAContents).hexdigest()
    
        # Get the hash of the server script
        fileBContents = open(fileB, 'rb').read()
        fileBHash = hashlib.md5(fileBContents).hexdigest()
        
        if (fileAHash == fileBHash):
            return True
        else:
            return False

    # Copy the specified file locally to the destination
    # If needed, make a backup if overwriting file and place it under
    # a backups folder with the time at the end of the file name.
    def copyLocal(self, sourceFile, destFile, backup=True):
        try:
            self.logger.info("Updating local copy of " + os.path.basename(sourceFile))
            if os.path.exists(destFile):
                if (backup == True):
                    sourceName = os.path.splitext(os.path.basename(sourceFile)) # Array with [name, ext]
                    bkpFolder = os.path.dirname(sourceFile) + '/(backup)/'
                    bkpPath = bkpFolder + sourceName[0] + '_' + str(int(time.time())) + sourceName[1]
                    self.logger.info('Backing up original to ' + os.path.basename(bkpPath))

                    if not os.path.exists(bkpFolder):
                        os.mkdir(bkpFolder)

                    shutil.move(destFile, bkpPath)

            shutil.copy(sourceFile, destFile)
            return True
        except:
            self.logger.warning("Unable to update local copy of " + os.path.basename(sourceFile))
            return False
                

    # Check to make sure the After Effects commandLineRenderer.jsx script is up to date
    def checkAEScripts(self):
        result = False
        for key, value in SCRIPTS.iteritems():
            result = False
            self.logger.info("KEY: " + str(key) + " VALUE: " + str(value))
            hostScript = os.path.dirname(self.getAERenderPath()) + '/Scripts/' + value
            servScript = os.path.dirname(inspect.getfile(inspect.currentframe())) + '/' + key
            self.logger.info("hostScript: " + str(hostScript))
            self.logger.info("servScript: " + str(servScript))

            if os.path.exists(hostScript):
                self.logger.info("hostScript exists")
                if self.compareHash(hostScript, servScript):
                    self.logger.info("Hash Codes match")
                    result = True

            if not result:
                # Script is either out of date, or doesn't exist
                self.logger.info('After Effects script out of date. Updating...')
                if (self.copyLocal(servScript, hostScript)):
                    result = True

        return result

    # Create the Data file to populate the dialog fields
    def makeDataFile(self):
        # Make sure After Effects has the commandLineRenderer.jsx script with
        # the added support for the makeDataFile flag to generate project data
        if self.checkAEScripts():
            cmd = "\"" + self.getAERenderPath() + "\""
            cmd += " -project \"" + self.data.projectPath + "\""
            cmd += " -makedatafile"

            self.logger.info("Generating Data File...")
            self.logger.info("Data File CMD: " + cmd)
            
            progDlg = wx.ProgressDialog ( 'Loading Project Data...', 'Lauching After Effects...', maximum = 100)
            p = subprocess.Popen(shlex.split(cmd))
            
            progDlg.Update( 25, 'Retrieving Data...')
            p.wait()
            self.logger.debug("Get Data File Exit Code: " + str(p.returncode))
            progDlg.Update( 100, 'Complete!')

            try:
                p.kill()
            except:
                pass

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

    def setProjectPath(self, path):
        self.data.projectPath = path

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