class FrameRange:
    def __init__(self, frameRangeString):
        self.frameRange = []
        self.addRange(frameRangeString)
    
    def addRange(self, frameRange):
        '''
        Parse an input frame range into individual frame numbers
        Ex: 1,20-25,22,100 -> [1, 20, 21, 22, 23, 24, 25, 100]
        Input can also be a list of frames, to save time.
        Updated to be much faster!
        '''

        result = []
        if type(frameRange) is str:
            newRange = list(set(sum(((list(range(*[int(j) + k for k,j in enumerate(i.split('-'))]))
                if '-' in i else [int(i)]) for i in frameRange.replace(' ','').split(',')), [])))
            result = list(set(newRange + self.frameRange))
            self.frameRange = result
        else:
            self.frameRange = frameRange

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
    
    def __str__(self):
        return self.convertListToRanges(self.frameRange)

    def addPadding(self, padding):

        padding = int(padding)
        # Split up the frame ranges and get max and min values
        i = 0
        frames = self.frameRange
        newFrameRanges = []
        frames.sort()
        if (len(frames) > 0):
            while(i+1 <= len(frames)):
                rangeStart = frames[i]

                while(i+2 <= len(frames)):
                    if (int(frames[i]) + 1 != int(frames[i+1])):
                        break
                    else:
                        i = i+1

                rngMin = 0
                rngMax = 0
                if (rangeStart != frames[i]):
                    rngMin = int(rangeStart)
                    rngMax = int(frames[i])
                else:
                    rngMin = rngMax = int(rangeStart)

                newMin = rngMin - padding
                if newMin < 0:
                    newMin = 0
                newMax = rngMax + padding
                newFrameRanges.append("%s-%s" % (newMin, newMax))
                i = i+1


        self.addRange(','.join(newFrameRanges))

        

test = FrameRange("1-10, 12")
test.addPadding(30)
print test