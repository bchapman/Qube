'''

Sequence Python Module
Author: Brennan Chapman
Date: 7/23/2011

Provides methods to assist in working with image sequences

'''

import os, sys, re, glob, hashlib, FileLock, DictDifferences
import sqlite3
import logging

'''
Set up the logging module.
'''
# seqLogger = logging.getLogger("main")
# ch = logging.StreamHandler()
# formatter = logging.Formatter("%(levelname)s: %(message)s")
# ch.setFormatter(formatter)
# seqLogger.addHandler(ch)
# seqLogger.setLevel(logging.DEBUG)
# ch.setLevel(logging.DEBUG)

class Sequence:
    def __init__(self, fileName):
        # Convert all wildcards in the fileName
        fileName = os.path.expanduser(fileName)

        seqData = self.splitPath(fileName)

        self.initFile = fileName
        self.folder = seqData.get('Folder', '')
        self.prefix = seqData.get('Prefix', '')
        self.padding = seqData.get('Padding', '')
        self.extension = seqData.get('Extension', '')
        self.currentFrame = seqData.get('currentFrame', '')

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
            

    def getDuration(self, frameRate=29.97):
        '''Get the time duration for the sequence in timecode'''
        bounds = self.getBounds()
        frames = (int(bounds['end']) - int(bounds['start']))
        dHours = padFrame(frames // (60*60*frameRate), 2)
        dMinutes = padFrame((frames // (60*frameRate)) % 60, 2)
        dSeconds = padFrame(((frames // (frameRate)) % 60) % 60, 2)
        dFrames = padFrame(frames % frameRate % 60 % 60, 2)
        result = dHours + ";" + dMinutes + ";" + dSeconds + ";" + dFrames
        return result

    def getFrames(self, frameRange='ALL'):
        '''
        Get a list of frames for the sequence returned in a list
        If a frame range is supplied, only those frames are returned
        '''
        
        if str(frameRange).upper() == 'ALL':
            # Generate a sequence path with wildcards to use with glob
            # Ex /path/to/sequence.*.png
            globPath = self.folder + '/' + self.prefix + '*' + self.extension
            result = glob.glob(globPath)
            result.sort() # Make sure they are sorted
            return result
        
        else:
            result = []
            for frameNum in self.loadFrameRange(frameRange):
                result.append(self.getFrame(frameNum))
            return result

    def getFrame(self, frame, includeFolder=True):
        '''Get the filename associated with a specific frame number'''
        
        result = ''
        if includeFolder:
            result += self.folder + '/'
        result += self.prefix + self.padFrame(frame) + self.extension
        return result


    def getBounds(self):
        '''Get the start and end frames for the sequence'''

        allExistingFrames = self.getFrames()
        result = {}
        result['start'] = self.splitPath(allExistingFrames[0])['currentFrame']
        result['end'] = self.splitPath(allExistingFrames[-1])['currentFrame']
        return result

    def getMissingFrames(self, frameRange='ALL'):
        '''
        Get a list of missing frames for the entire sequence
        or just a frameRange.
        Returned as a list.
        '''

        start = end = 0 # Initialize
        
        # Get the start and end frames based on the input frameRange
        if str(frameRange).upper() == 'ALL':
            bounds = self.getBounds()
            start = bounds.get('start')
            end = bounds.get('end')
        else:
            frameRange = self.loadFrameRange(frameRange)
            start = frameRange[0]
            end = frameRange[-1]

        missingFrames = []
        for f in range(int(start), int(end)+1):
            path = self.getFrame(f)
            if not os.path.exists(path):
                missingFrames.append(path)        

        return missingFrames

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


    def loadFrameRange(self, frameRange):
        '''
        Parse an input frame range into individual frame numbers
        Ex: 1,20-25,22,100 -> [1, 20, 21, 22, 23, 24, 25, 100]
        Input can also be a list of frames, to save time.
        Updated to be much faster!
        '''
        
        result = []
        if type(frameRange) is str:
            sys.stdout.write('Type: ' + str(type(frameRange)) + '\n')
            sys.stdout.write('Content: ' + str(frameRange) + '\n')
            result = list(set(sum(((list(range(*[int(j) + k for k,j in enumerate(i.split('-'))]))
                if '-' in i else [int(i)]) for i in frameRange.replace(' ','').split(',')), [])))
            return result
        else:
            return frameRange

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
            raise IOError("ERROR: Invalid Sequence")

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
        
        sys.stdout.write('Incoming modTimeDict: ' + str(modTimeDict) + '\n')
        sys.stdout.write('frameRange: ' + str(frameRange) + '\n')
        if modTimeDict == {}:
            modTimeDict = {}
            sys.stdout.write('Loading modification times: No hash dictionary provided.\n')
            modTimeDict = self.getModTimes(frameRange)

        sys.stdout.write('Saving modification times to database...\n')
        conn = sqlite3.connect(filename)
        curs = conn.cursor()
        test = curs.execute('CREATE TABLE IF NOT EXISTS frames (name, modtime)')
        items = modTimeDict.items()

        sys.stdout.write("Writing " + str(len(items)) + " modification times to the database...\n")
        for item in items:
            curs.execute('INSERT OR REPLACE INTO frames (name, modtime) VALUES (?,?)', item)
            
        sys.stdout.write('Committing changes to database...\n')
        conn.commit()    
        conn.close()
        
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
            # sys.stdout.write('Retrieving modTime for ' + str(frame) + '.\n')
            modTime = os.stat(frame).st_mtime
            frameName = os.path.basename(frame)
            result[frameName] = modTime
        return result

    def loadModTimesFromDB(self, filename, frameRange='ALL'):
        '''
        Read the sqlite db of each frames hash codes to check
        for frames that have changed since last time.
        '''

        # seqLogger.debug('Retrieving hash codes from database.')
        sys.stdout.write('getModTimesFromFile...\n')
        conn = sqlite3.connect(filename)
        curs = conn.cursor()
        test = curs.execute('CREATE TABLE IF NOT EXISTS frames (name, modtime)')
        if str(frameRange).upper() == 'ALL':
            curs.execute('SELECT * from frames order by name')
        else:
            dbRange = []
            frameRange = self.loadFrameRange(frameRange)
            for frame in frameRange:
                dbRange.append('"' + self.prefix + str(self.padFrame(frame)) + self.extension + '"')
            cmd = 'SELECT name,modtime FROM frames WHERE name IN(' + ','.join(dbRange) + ') order by name'
            curs.execute(cmd)

        '''
        Load the input into a dictionary.
        If a frame range was supplied, limit the dictionary to that range.
        '''
        result = {}
        for item in curs:
            frameName, modTime = item
            # sys.stdout.write('Loading from db: ' + frameName + '\n')
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