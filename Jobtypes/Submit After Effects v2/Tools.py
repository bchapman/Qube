'''
Tools for monitoring the after effects render.
Author: Brennan Chapman
Date: 9/26
'''
import os
import sys
import re
import logging
import time

sys.path.append('/Applications/pfx/qube/api/python/')
import qb

sys.path.insert(0, '../../Modules')
import sequenceTools

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

class Tools:
    def __init__(self, agendaItem, outputs, logFilePath, startFrame, endFrame):
        self.mySequences = None
        self.corruptFrames = []
        self.agendaItem = agendaItem
        self.outputs = outputs
        self.startFrame = startFrame
        self.endFrame = endFrame
        self.duration = int(endFrame) - int(startFrame)

        self.logFilePath = logFilePath
        logger.info("LogFilePath: " + str(self.logFilePath))
        self.readLogFile = open(self.logFilePath,'r')
        # Find the size of the file and move to the end
        st_results = os.stat(self.logFilePath)
        st_size = st_results[6]
        self.readLogFile.seek(st_size)

        self.isOutputMovie = False
        for output in outputs:
            if output.endswith('.mov'):
                self.isOutputMovie = True
                self.deleteExistingMovies()

        self.progressPattern = re.compile('(?<=^PROGRESS:  )(?:\(Skipping \d+\)|\d+?|\d;.*?) \((.*?)\).*$')
        self.completePattern = re.compile('(Total Time Elapsed)')

        self.currFrame = None
        self.alreadyComplete = False
        
        self.chunkProgressDelay = 5 # Seconds

    def deleteExistingMovies(self):
        for output in self.outputs:
            if os.path.exists(output):
                logging.info("Deleting existing output. " + str(output))
                try:
                    os.remove(output)
                except:
                    logger.warning("Unable to delete existing output. " + str(output))

    def monitorRender(self, timeout=1800):
        logger.debug("Monitoring Render...")

        mainIdleTime = time.time()
        frameIdleTime = time.time()
        while True:
            where = self.readLogFile.tell()
            line = self.readLogFile.readline()
            if not line:
                time.sleep(.3)
                self.readLogFile.seek(where)
                if time.time() - mainIdleTime > timeout:
                    raise RuntimeError("Frame timeout reached.")
            else:
                '''
                Reset the idle time each time a new line is read.
                If the frame timeout is reached, raise an exception.
                '''
                mainIdleTime = time.time()
                
                ''' Retrieve the info from each line of output '''
                self.currFrame = self.reSearch(self.progressPattern, line)
                if self.currFrame != "":
                    self.currFrame = str(int(self.startFrame) + int(self.currFrame) - 1)
                    # logger.debug("Last Completed Frame: " + currFrame)
                    if not self.isOutputMovie:
                        self.verifyCurrFrame()
                    if not self.alreadyComplete:
                        if time.time() - frameIdleTime > self.chunkProgressDelay:
                            logger.debug("Chunk Progress: " + str(self.getChunkProgress()))
                            resultPackage = {'progress':str(self.getChunkProgress())}
                            self.agendaItem['resultpackage'] = resultPackage
                            qb.reportwork(self.agendaItem)
                            frameIdleTime = time.time()

                complete = self.reSearch(self.completePattern, line)
                if complete:
                    break
                

        self.deleteCorruptFrames()
        if self.corruptFrames:
            return False
        else:
            return True

    def getChunkProgress(self):
        myFrame = float(int(self.currFrame) - int(self.startFrame))
        myDuration = float(self.duration + 1)
        logger.info("Current Progress: " + str(round(myFrame / myDuration * 100)))
        return myFrame / myDuration

    def verifyCurrFrame(self):
        # logger.debug("Verifying frame " + str(frame))
        if not self.mySequences:
            self.setupSequences()
        for sequence in self.mySequences:
            if sequence.checkForCorruptFrame(self.currFrame):
                self.corruptFrames.append(self.currFrame)

    def deleteCorruptFrames(self):
        for frame in self.corruptFrames:
            for sequence in self.mySequences:
                framePath = sequence.getFrameFilename(frame)
                logger.debug("Deleting corrupt frame: " + os.path.basename(framePath))
                try:
                    os.remove(framePath)
                except:
                    logger.error("Unable to delete corrupt frame: " + os.path.basename(framePath))

    def setupSequences(self):
        self.mySequences = []
        for outputPath in self.outputs:
            logger.info("Output Path: " + str(outputPath))
            firstFrame = outputPath.replace("[", "").replace("]", "")
            firstFrame = firstFrame.replace("#", "0")
            self.mySequences.append(sequenceTools.Sequence(firstFrame))

    def getOutputPaths(self, startFrame, endFrame):
        outputPaths = []
        if not self.mySequences:
            self.setupSequences()
        for sequence in self.mySequences:
            paths = sequence.getFrameFilenames(range(int(startFrame), int(endFrame)+1), includeFolder=True)
            outputPaths.extend(paths)
        return outputPaths

    def reSearch(self, pattern, data):
        pattern = re.compile(pattern)
        match = pattern.search(data)    
        if (match != None):
            return match.group(1)
        else:
            return ""