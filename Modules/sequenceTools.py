'''

Sequence Python Module
Author: Brennan Chapman
Date: 8/11/2011

Provides methods to assist in working with image sequences

'''

import os, sys, re, glob, hashlib, DictDifferences
import logging

# Qube workaraound
try:
    import sqlite3
except:
    sys.path.append('/System/Library/Frameworks/Python.framework/Versions/2.5/lib/python2.5')
    sys.path.append('/System/Library/Frameworks/Python.framework/Versions/2.5/lib/python2.5/lib-dynload/')
    import sqlite3


'''
Set up the logging module.
'''
''' Setup the logger. '''
# logging.basicConfig()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

PIL = False
try:
    import Image
    PIL = True
except:
    try:
        sys.path.append("/Library/Python/2.5/site-packages/PIL/")
        import Image
        PIL = True
    except:
        logger.warning("Unable to import PIL Image module.")

def loadFrameRange(frameRange):
    '''
    Parse an input frame range into individual frame numbers
    Ex: 1,20-25,22,100 -> [1, 20, 21, 22, 23, 24, 25, 100]
    Input can also be a list of frames, to save time.
    Updated to be much faster!
    '''
    
    result = []
    if type(frameRange) is str:
        result = list(set(sum(((list(range(*[int(j) + k for k,j in enumerate(i.split('-'))]))
            if '-' in i else [int(i)]) for i in frameRange.replace(' ','').split(',')), [])))
        return result
    else:
        return frameRange

class Sequence:
    def __init__(self, fileName, frameRange='ALL'):
        # Convert all wildcards in the fileName
        fileName = os.path.expanduser(fileName)
        fileName = os.path.expandvars(fileName)

        seqData = self.splitPath(fileName)

        self.initFile = fileName
        self.folder = seqData.get('Folder', '')
        self.prefix = seqData.get('Prefix', '')
        self.padding = seqData.get('Padding', '')
        self.extension = seqData.get('Extension', '')
        self.currentFrame = seqData.get('currentFrame', '')
        self.frameRange = frameRange

    def getName(self):
        '''
        Return the name of the input sequence
        without extension or numbering.
        '''
        result = self.prefix
        if result[-1:] in ('_','.',' ','('):
            result = result[:-1]
        return result

    def loadFrameRange(self, frameRange):
        '''
        Load a frame range with the option of
        all existing frames from the current
        sequence object.
        '''
        if type(frameRange) is list:
            return frameRange
        frameRange = str(frameRange)
        if frameRange.upper() == 'ALL':
            bounds = self.getBounds()
            frameRange = str(bounds['start']) + '-' + str(bounds['end'])
        return loadFrameRange(frameRange)

    def deleteFrames(self, frames):
        '''
        Delete the supplied frame range from the sequence.
        You can also supply the value "ALL" to delete all frames
        '''
        
        framesToDelete = []
        
        if str(frames).upper() == 'ALL':
            framesToDelete = self.getFrames()
        else:
            for frameNumber in self.loadFrameRange(frames):
                framesToDelete.append(self.getFrame(frameNumber))
        
        deleteCount = 0
        for frame in framesToDelete:
            if os.path.exists(frame):
                os.remove(frame)
                deleteCount += 1
        
        return deleteCount

    def checkForCorruptFrame(self, frame):
        result = self.checkForCorruptFrames(str(frame) + '-' + str(frame))
        if result:
            return True
        else:
            return False

    def checkForCorruptFrames(self, frames='All'):
        framesToVerify = []
        
        if str(frames).upper() == 'ALL':
            framesToVerify = self.getFrames()
        else:
            for frameNumber in self.loadFrameRange(frames):
                framesToVerify.extend(self.getFrames(frameNumber))
        
        corruptFrames = []
        if PIL:
            for frame in framesToVerify:
                filePath = self.getFrameFilename(frame)
                # logger.debug("Opening image: " + str(filePath))
                try:
                    img = Image.open(filePath)
                    img.verify()
                    # logger.debug("Image verified: " + filePath)
                except:
                    logger.debug("Corrupt image path: " + filePath)
                    corruptFrames.append(frame)
            if corruptFrames:
                logger.warning("Corrupt Frame Numbers: " + self.convertListToRanges(corruptFrames))
        else:
            logger.warning("Python Imaging Library(PIL) not installed.")

        return corruptFrames
        
    def getDuration(self, frameRate=29.97, timecode=False):
        '''
        Get the time in either frames or timecode
        for the sequence.
        '''
        
        bounds = self.getBounds()
        frames = (int(bounds['end']) - int(bounds['start']))
        if not timecode:
            return frames
        else:
            dHours = self.padFrame(frames // (60*60*frameRate), 2)
            dMinutes = self.padFrame((frames // (60*frameRate)) % 60, 2)
            dSeconds = self.padFrame(((frames // (frameRate)) % 60) % 60, 2)
            dFrames = self.padFrame(frames % frameRate % 60 % 60, 2)
            result = dHours + ";" + dMinutes + ";" + dSeconds + ";" + dFrames
            return result

    def getExistingFrames(self, frameRange='ALL'):
        '''
        Get a list of all frame numbers that currently exist.
        '''
        
        if str(frameRange).upper() == 'ALL':
            '''
            Generate a sequence path with wildcards to use with glob
            Ex /path/to/sequence.*.png
            '''
            
            globPath = self.folder + '/' + self.prefix + '*' + self.extension
            fileList = glob.glob(globPath)
            fileList.sort()
            
            result = []
            for item in fileList:
                result.append(int(self.splitPath(item)['currentFrame']))
            return result
        
        else:
            result = []
            for frameNum in self.loadFrameRange(frameRange):
                if os.path.exists(self.getFrameFilename(frameNum)):
                    result.append(frameNum)
            return result

    def getFrames(self, frameRange='ALL', excludeMissing=False, onlyMissing=False, fillMissing=False):
        '''
        Generate a list of all possible frame numbers in the sequence.
        This is returned either as frame filenames or frame numbers.
        Get a list of frames for the sequence returned in a list.
        If a frame range is supplied, only those frames are returned.
        Check missing will check for missing frames.
        Fill missing frames will repeat the latest frame if a frame is missing.
        '''
        
        myFrameRange = self.loadFrameRange(frameRange)
        result = range(myFrameRange[0], myFrameRange[-1]+1)
        
        if not excludeMissing and not fillMissing and not onlyMissing:
            return result
        else:
            existingFrames = self.getExistingFrames(frameRange)
            if excludeMissing or fillMissing:
                result = list(set(result).intersection(set(existingFrames)))
                if excludeMissing:
                    return result
                else:
                    newList = []
                    bounds = self.getBounds()
                    count = 0
                    for index, frameNum in enumerate(result):
                        while index+1 < len(result) and count != result[index+1]:
                            newList.append(frameNum)
                            count += 1
                    newList.append(result[-1])
                    return newList
            elif onlyMissing:
                result = list(set(result) - set(existingFrames))
                return result

    def convertListToRanges(self, frames):
        '''
        Convert an array of frame numbers into a string of frame ranges.
        Ex: 1,2,3,4,5,10 -> 1-5,10
        '''
        
        i = 0
        frameRanges = []
        frames.sort()
        if (len(frames) > 0):
            while(i+1 <= len(frames)):
                rangeStart = frames[i]

                while(i+2 <= len(frames)):
                    if (int(frames[i]) + 1 != int(frames[i+1])):
                        break
                    else:
                        i = i+1

                if (rangeStart != frames[i]):
                    rng = str(rangeStart) + "-" + str(frames[i])
                    frameRanges.append(rng)
                else:
                    rng = str(rangeStart)
                    frameRanges.append(rng)
                i = i+1

        return ','.join(frameRanges)

    def getFrameFilename(self, frame, includeFolder=True):
        '''
        Generate the filename associated with the supplied frame.
        '''
        
        currFrame = ''
        if includeFolder:
            currFrame += self.folder + '/'
        currFrame += self.prefix + self.padFrame(frame) + self.extension
        return currFrame
    
    def getFrameFilenames(self, frames, includeFolder=True):
        '''
        Generate the filename associated with the supplied frames.
        '''
        
        result = []
        for frame in frames:
            result.append(self.getFrameFilename(frame, includeFolder))
        return result

    def getBounds(self, update=False, frameRange=''):
        '''
        Get the start and end frames for the sequence.
        Uses the frameRange when the sequence was initialized
        unless Update is true.
        '''

        if frameRange != '':
            frames = loadFrameRange(self.frameRange)
    
        result = {}
        result['start'] = str(frames[0])
        result['end'] = str(frames[-1])
            
        return result

    def getMissingFrames(self, frameRange='ALL'):
        '''
        Get a list of missing frames for the entire sequence
        or just a frameRange.
        Returned as a list.
        * Uses getFrames, this is just for convience
        '''

        return self.getFrames(frameRange, onlyMissing=True)

    def getTemplate(self):
        '''
        Get a name template for the sequence.
        This replaces the numbers with number signs
        Ex: testSequence.#####.png
        '''

        return self.prefix + ('#' * self.padding) + self.extension

    def getSize(self, humanReadable=True):
        '''
        Get the total size for the sequence.
        Returns a string.
        '''
        
        result = 0
        allExistingFrames = self.getFrames()
        for frame in allExistingFrames:
            result += os.path.getsize(frame)
        
        if humanReadable:
            # Now make it a little easier to read
            for x in ['bytes','KB','MB','GB','TB']:
                    if result < 1024.0:
                        return "%3.1f %s" % (result, x)
                    result /= 1024.0
        else:
            return result

    def padFrame(self, frame, pad=''):
        '''
        Pad the input value
        Ex: 1 with a pad of 5 -> 00001
        '''

        # If no padding is supplied, use the sequence settings
        if not pad:
            pad = self.padding

        frame = int(round(float(frame)))
        return '0' * (pad - len(str(frame))) + str(frame)

    def getFramesFromFilenames(self, filenames):
        '''
        Given an array of sequence filenames, return a list of
        the corresponding frame numbers.
        '''
        frameNumbers = []
        for frame in filenames:
            frameNumbers.append(self.splitPath(frame)['currentFrame'])
        return frameNumbers

    def splitPath(self, path):
        '''
        Split the file path of a sequence into it's various parts
        Returns a dicitonary.
        '''

        result = {}

        # Sequence matching regex
        pattern = re.compile('(.+?)(\d\d+?)(\.\w+)')
        match = pattern.match(path)

        if not match:
            raise IOError("ERROR: Invalid Sequence " + str(path))

        name, number, ext  = match.groups()
        splitPath = os.path.split(name)

        result['Folder'] = splitPath[0]
        result['Prefix'] = splitPath[1]
        result['Padding'] = len(number)
        result['Extension'] = ext
        result['currentFrame'] = number

        return result

    '''
    Modification Time Methods
    Used to find changes in image sequences.
    '''

    def saveModTimes(self, filename, modTimeDict={}, frameRange='ALL'):
        '''
        Create or update an sqlite db of each frame and
        it's current modification time supplied as a dictionary
        for comparison next time.
        '''
        
        if modTimeDict == {}:
            modTimeDict = {}
            logger.debug('Loading modification times: No hash dictionary provided.\n')
            modTimeDict = self.getModTimes(frameRange)

        logger.info('Saving modification times...\n')
        conn = sqlite3.connect(filename)
        curs = conn.cursor()
        test = curs.execute('CREATE TABLE IF NOT EXISTS frames (name, modtime)')
        items = modTimeDict.items()

        logger.info("Writing " + str(len(items)) + " modification times\n")
        for item in items:
            curs.execute('INSERT OR REPLACE INTO frames (name, modtime) VALUES (?,?)', item)
            
        logger.info('Committing changes to database...\n')
        conn.commit()    
        conn.close()
        logger.info('Modification times saved.')
        
    def compare(self, databaseFile, frameRange='ALL', pastModTimes={}, currentModTimes={}):
        '''
        Compare the current sequence to a information
        about a previous version stored in the supplied database.
        Lists added, deleted, modified, and constant items.
        Changes are determined by:
            1) Find added and deleted frames.
            2) Find items with modification time differences.
        '''

        if pastModTimes == {}:
            pastModTimes = self.loadModTimesFromDB(databaseFile, frameRange)
        if currentModTimes == {}:
            currentModTimes = self.getModTimes(frameRange)

        diff = DictDifferences.DictDifferences(currentModTimes, pastModTimes)
        result = {}
        result['Added'] = list(sorted(diff.added()))
        result['Modified'] = list(sorted(diff.changed()))
        result['Deleted'] = list(sorted(diff.removed()))
        result['Constant'] = list(sorted(diff.unchanged()))
        
        return result
        
    def getModTimes(self, frameRange='ALL'):
        '''
        Generate a dictionary of every frames modification time.
        This is used to check for changes in an image sequence.
        Optionally supply a frame range to limit the scope.
        '''

        result = {}
        frames = sorted(self.getFrames(frameRange))

        for frame in frames:
            frameFilename = self.getFrameFilename(frame)
            modTime = os.stat(frameFilename).st_mtime
            frameName = os.path.basename(frameFilename)
            result[frameName] = modTime
        return result

    def loadModTimesFromDB(self, filename, frameRange='ALL'):
        '''
        Read the sqlite db of each frames hash codes to check
        for frames that have changed since last time.
        '''

        logger.debug('Retrieving hash codes from database...')
        conn = sqlite3.connect(filename)
        curs = conn.cursor()
        test = curs.execute('CREATE TABLE IF NOT EXISTS frames (name, modtime)')

        if str(frameRange).upper() == 'ALL':
            curs.execute('SELECT * from frames order by name')
        else:
            dbRange = []
            frameRange = self.loadFrameRange(frameRange)
            for frame in frameRange:
                dbRange.append('"' + self.getFrameFilename(frame, includeFolder=False) + '"')
            cmd = 'SELECT name,modtime FROM frames WHERE name IN(' + ','.join(dbRange) + ') order by name'
            curs.execute(cmd)

        '''
        Load the input into a dictionary.
        If a frame range was supplied, limit the dictionary to that range.
        '''
        result = {}
        for item in curs:
            frameName, modTime = item
            currentFrameNumber = int(self.splitPath(frameName)['currentFrame'])

            addToDict = False
            if str(frameRange).upper() == 'ALL':
                addToDict = True
            elif currentFrameNumber in frameRange:
                    addToDict = True

            if addToDict:
                result[frameName] = modTime

        conn.close()

        return result

    def __str__(self):
        return self.getTemplate()


# mySequence = Sequence('/Users/bchapman/Projects/Scripts+Apps/Qube/_testingGrounds/Image_Sequence_nth/blindness_00000.png')
# print "Final: " + str(mySequence.getFrames(fillMissing=True))
# print mySequence.getMissingFrames()