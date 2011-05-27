'''
Render Class (Controller)

Author: Brennan Chapman
Date: 5/24
Version: 1.0

Class to store all methods to needed to control the render.
'''

import sys
sys.path.insert(0, '/Volumes/theGrill/.qube/Jobtypes/AERenderX/')
import Queue
import re
import shlex, subprocess

import Reporter

REPORTERTHEADS = 1
STATUSFREQUENCY = 20 # Frames

class Render():

    def __init__(self, job):
        self.job = job
        self.logger = job.logger
        self.proc = ''
        self.qubeProgress = 0

    # Convert the time() value to timecode
    def convertSecToTime(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    def getAERenderPath(self):
        result = ''
        if (sys.platform == 'win32'):
            result = self.job.aerenderwin
        elif (sys.platform == 'darwin'):
            result = self.job.aerendermac
        else:
            self.logger.error("Unspupported OS for rendering.")
            sys.exit(64)
        return result
        
    # Compile the command
    def getCMD(self):
        job = self.job
        cmd = '\"' + self.getAERenderPath() + '\"'
        cmd += " -project \"" + job.projectPath + "\""
        if (job.getDataFile):
            cmd += " -getdatafile"
        else:
            if (job.rqIndex != ""):
                cmd += " -rqindex " + job.rqIndex
            if (job.multProcs == True):
                cmd += " -mp"
        return cmd

    # Monitor the render, print a status bar at a specified frequency,
    # and report the progress to Qube
    def monitorRender(self):
        statusbar = ""
        
        # Start the Reporter Thread for Qube
        queue = Queue.Queue() # Store the qube updates to be processed
        # Start 1 threads for now
        for i in range(0, 1):
            reporter = Reporter.Reporter(queue)
            reporter.setDaemon(True) # Set it to run continuosly
            reporter.start() # Spawn the thread
        self.logger.info("Reporter Thread Started")

        while True:
            # Read the input
            stdOut = self.proc.stdout.readline()
            if not stdOut: break
    
            # Write the actual output line
            sys.stdout.write(stdOut)
            sys.stdout.flush()
            
            # ------------------------------------------------------------------------------
            # Retrieve the info from each line of output
            # ------------------------------------------------------------------------------
        
            # Get the current frame, if unavailable, check for other parameters
            self.job.prevFrame = self.job.currFrame
            result = self.reSearch('(?<=^PROGRESS:  )(?:\(Skipping \d+\)|\d+?|\d;.*?) \((.*?)\).*$', stdOut)
            if result != "": self.job.currFrame = result
        
            # Get the start Frame
            if self.job.start == "":
                self.job.start = self.reSearch('(?<=PROGRESS:  Start: )(.+?)\n', stdOut)

            # Get the end Frame                                                                                   
            elif self.job.end == "":
                self.job.end = self.reSearch('(?<=PROGRESS:  End: )(.+?)\n', stdOut)
    
            # Get the duration
            elif self.job.duration == "": self.job.duration = self.reSearch('(?<=PROGRESS:  Duration: )(.+?)\n', stdOut)
        
             # Print the status bar every # of frames
            if (self.job.currFrame != "" and (int(self.job.currFrame) % STATUSFREQUENCY) == (STATUSFREQUENCY-1) and self.job.currFrame != self.job.prevFrame):

                # ----------------------------------------------------------------------------------
                # Write the statusbar
                # 
                # % CURRFRAME/TOTALFRAMES - Avg: FRAMEAVG - Elapsed: ELAPSED - Remaining: REMAINING
                # ----------------------------------------------------------------------------------

                statusbar = "PROGRESS:  " + str(self.job.getPercentComplete()) + "%"
                statusbar +=  " " + str(self.job.currFrame) + "/" + str(self.job.duration)
                statusbar += " - Avg:" + self.convertSecToTime(self.job.getFrameAvg())
                statusbar += " - Elapsed:" + self.convertSecToTime(self.job.getElapsedTime())
                statusbar += " - Remaining:" + self.convertSecToTime(self.job.getRemainingTime())
                statusbar += "\n"

                sys.stdout.write(statusbar)
                sys.stdout.flush()

            # Update Qube if frames have changed
            if (self.job.prevFrame != self.job.currFrame):
                queue.put(self.job.getPercentComplete())
        
        # Wait for the Qube Updates to be processed
        queue.join()
        
        self.job.setComplete() # Store the end time
        
        self.logger.info("Exit Code: " + str(self.proc.returncode))
        sys.exit(self.proc.returncode)

    # Search for a regular expression and return the first match
    def reSearch(self, pattern, data):
        pattern = re.compile(pattern)
        match = pattern.search(data)    
        if (match != None):
            return match.group(1)
        else:
            return ""

    # Start the render
    def startRender(self):
        self.logger.info("Starting render...")
        
        renderCMD = self.getCMD()
        self.logger.info("Render CMD: " + renderCMD)
        
        self.proc = subprocess.Popen(shlex.split(renderCMD), bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.monitorRender()