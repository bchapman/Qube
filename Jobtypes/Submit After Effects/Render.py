'''
Render Class (Controller)

Author: Brennan Chapman
Date: 5/24
Version: 1.0

Class to store all methods to needed to control the render.
'''

import os, sys
sys.path.insert(0, '/Volumes/theGrill/.qube/Jobtypes/AERenderX/')
import Queue
import re
import shlex, subprocess
import shutil
import inspect
import time
import hashlib

import Reporter

REPORTERTHEADS = 1
STATUSFREQUENCY = 20 # Frames

SCRIPTS = {}
SCRIPTS['commandLineRenderer.jsx'] = 'Startup/commandLineRenderer.jsx'
SCRIPTS['Qube_Tools.jsx'] = 'Startup/Qube_Tools.jsx'

class Render():

    def __init__(self, job):
        self.job = job
        self.logger = job.logger
        self.proc = ''
        self.qubeProgress = 0

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


    # Convert the time() value to timecode
    def convertSecToTime(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s)

    # Get each aerendercore process and the open files associated with them
    def getAERenderCoreProcesses(self):
        # Command to list all Process IDs (PID) of aerendercore processes
        cmd = "ps A | grep 'aerendercore'"
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        # Search through the output and gather the PIDs
        pids = []
        for line in p.stdout.readlines():
            if ('aerendercore -noui' in line):
                pids.append(line.split(' ')[0])
    
        # List all open files for each pid
        processes = {}
        for pid in pids:
            cmd = "lsof -p " + str(pid)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            processes[str(pid)] = p.stdout.readlines()
        
        return processes

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

    # Kill AERenderCore Processes for the specified project.
    #
    # The aerendercore process isn't directly tied to aerender.
    # It is spawned by launchd.
    #
    # So to find which aerendercore process correlates to each render
    # we sort through open files, the log files are most always open.
    # By default, these carry the name of the project.
    # We search for these to associate each aerendercore process
    # with it's project.
    def killAERenderCoreProcesses(self, projectFile):
    
        processes = self.getAERenderCoreProcesses()
    
        # Scan each process for open files matching the project file
        relatedPIDs = []
        for pid,files in processes.iteritems():
            for f in files:
                found = False
                if projectFile in f:
                    found = True
                if found:
                    relatedPIDs.append(pid)

        # Kill each of these processes
        for pid in relatedPIDs:
            self.logger.info('Killing AERenderCore (' + str(pid) + ')')
            os.kill(int(pid), 9)

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
        
        # Make sure the AEScripts are up to date
        if not self.checkAEScripts():
            raise('Error updating render scripts.  Check permissions on the After Effects Scripts folder.')
        
        renderCMD = self.getCMD()
        self.logger.info("Render CMD: " + renderCMD)
        
        self.proc = subprocess.Popen(shlex.split(renderCMD), bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.monitorRender()