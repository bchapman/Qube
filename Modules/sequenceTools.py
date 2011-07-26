'''

Sequence Python Module
Author: Brennan Chapman
Date: 7/23/2011

Provides methods to assist in working with image sequences

'''

import os, sys, re, glob, hashlib, FileLock, DictDifferences

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
        
        if frames.upper() == "ALL":
            framesToDelete = self.getFrames()
        else:
            for frameNumber in self.parseFrameRange(frames):
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

    def getFrames(self, frameRange='All'):
        '''
        Get a list of frames for the sequence returned in a list
        If a frame range is supplied, only those frames are returned
        '''
        
        if frameRange == 'All':
            # Generate a sequence path with wildcards to use with glob
            # Ex /path/to/sequence.*.png
            globPath = self.folder + '/' + self.prefix + '*' + self.extension
            result = glob.glob(globPath)
            result.sort() # Make sure they are sorted
            return result
        
        else:
            result = []
            for frameNum in self.parseFrameRange(frameRange):
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
        # print "All Existing Frames: " + str(allExistingFrames)
        result['start'] = self.splitPath(allExistingFrames[0])['currentFrame']
        result['end'] = self.splitPath(allExistingFrames[-1])['currentFrame']
        return result

    def getMissingFrames(self, frameRange='All'):
        '''
        Get a list of missing frames for the entire sequence
        or just a frameRange.
        Returned as a list.
        '''

        start = end = 0 # Initialize
        
        # Get the start and end frames based on the input frameRange
        if frameRange == 'All':
            bounds = self.getBounds()
            start = bounds.get('start')
            end = bounds.get('end')
        else:
            frameRange = self.parseFrameRange(frameRange)
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


    def parseFrameRange(self, frameRangeString):
        '''
        Parse an input frame range into individual frame numbers
        Ex: 1,20-25,22,100 -> [1, 20, 21, 22, 23, 24, 25, 100]
        '''
        
        numbers = str(frameRangeString)
        pattern = re.compile('[0-9,-]')
        possibles = ""

        if (numbers == ""):
            raise IOError("ERROR: No input range(s) given")

        if (len(pattern.findall(numbers)) == len(numbers)):
            possibles = str(numbers).split(",")
            numbers = []

            for possible in possibles:
                if "-" in possible:
                    values = possible.split("-")
                    if (len(values) == 2):
                        newRange = range(int(values[0]), int(values[1])+1)
                        numbers.extend(newRange)
                    else:
                        raise IOError("ERROR: Invalid Range (" + str(possible) + ")")
                        break
                else:
                    numbers.append(int(possible))
                    
            #  Remove Duplicates and sort the numbers
            numbers = sorted(set(numbers))
            return numbers

        else:
            raise IOError("ERROR: Invalid input numbers.")

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
    Hash Code Methods
    Used to find changes in image sequences
    '''

    def compareHashCodes(self, filename, frameRange='All'):
        '''
        Compare current hash codes with the contents of the supplied file.
        Returns a dictionary of Added, Modified, Deleted, and Constant Frames.
        Optionally supply a frame range to limit the scope of the comparison.
        '''

        # print "Loading past hash codes..."
        pastHashCodes = self.getHashCodesFromFile(filename, frameRange)
        # print "Loading current hash codes..."
        currentHashCodes = self.getHashCodes(frameRange)

        # print "Comparing hash codes..."
        diff = DictDifferences.DictDifferences(currentHashCodes, pastHashCodes)        
        result = {}
        result['Added'] = list(sorted(diff.added()))
        result['Modified'] = list(sorted(diff.changed()))
        result['Deleted'] = list(sorted(diff.removed()))
        result['Constant'] = list(sorted(diff.unchanged()))
        
        return result
        

    def getHashCodes(self, frameRange='All'):
        '''
        Generate a dictionary of every frames hash codes.
        This is used to check for changes in an image sequence.
        Optionally supply a frame range to limit the scope.
        '''
        
        result = {}
        frames = sorted(self.getFrames(frameRange))

        for frame in frames:
            # print "Getting hash code for " + str(frame) + "..."
            hashcode = hashlib.md5(open(frame, 'rb').read()).hexdigest()
            frameName = os.path.basename(frame)
            result[frameName] = hashcode
        return result

    def getHashCodesFromFile(self, filename, frameRange='All'):
        '''
        Load hash codes that were saved previously into a dictionary.
        Optionally supply a frame range to limit the scope.
        '''
        
        hashInput = []
        with FileLock.FileLock(filename, timeout=20):
            '''
            Acquire a lock on the hash code file so other processes
            don't mess up our operation.
            '''
            
            hashFile = open(filename, 'r')
            hashInput = hashFile.readlines()
            hashFile.close()
        
        '''
        Load the input into a dictionary.
        If a frame range was supplied, limit the dictionary to that range.
        '''
        result = {}
        for frame in hashInput:
            frameFile, frameHash = frame.split(' : ')
            currentFrameNumber = int(self.splitPath(frameFile)['currentFrame'])

            addToDict = False
            if frameRange.upper() == 'ALL':
                addToDict = True
            elif currentFrameNumber in self.parseFrameRange(frameRange):
                addToDict = True
            
            if addToDict:
                result[frameFile] = frameHash.replace('\n','')

        return result

    def saveHashCodes(self, filename):
        '''
        Save hash codes in a file to load again later.
        '''
        
        output = ''
        items = self.getHashCodes().items()
        for item in sorted(items):
            output += item[0] + ' : ' + item[1] + '\n'
        
        with FileLock.FileLock(filename, timeout=20):
            '''
            Acquire a lock on the hash code file so other processes
            don't mess up our operation.
            '''
            
            hashFile = open(filename, 'w')
            hashFile.write(output)
            hashFile.close()

    def __str__(self):
        return self.getTemplate()