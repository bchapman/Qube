#!/usr/bin/python

"""
Submit Transcoder
Author: Brennan Chapman
Date: 7/12/2011

Purpose:
    Run the transcoder jobs using blender
    to cluster transcode image sequences
    to separate quicktime movies.
    Then use qttools to merge them together.
    *Only works on Mac render nodes

Features:
    Uses blender which is free!
    Can use an unlimited # of computers
    Low memory usage...around 200MB per instance
"""

import os, sys
import inspect
import logging
sys.path.append('/Applications/pfx/qube/api/python/')
import qb

# Gotta be a better way to do this.  Suggestions?
sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
print 'PATH: ' + str(sys.path) + "\n"
import PreFlight
import Job
import Render
import signal

# ---------------------------------------------------------------------------
# Set up the logger module
# ---------------------------------------------------------------------------

# Create logger
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# Create a formatter
formatter = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(formatter)
# Add ch to logger
logger.addHandler(ch)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def initJob():
    # Get the job object
    jobObject = qb.jobobj()
    job = Job.Job(logger) # Create our own Job Object
    job.loadOptions(jobObject) # Load the Qube Job into our job template

    return job


def executeJob(job):
    global render
    jobstate = 'complete'

    # Run the job independently of the subjobs.
    # We will update the subjobs based on frames completed
    render = Render.Render(job)
    render.startRender()

    return jobstate


def cleanupJob(job, state):
    # jobObject = job.qubejob
    qb.reportjob(state)


def main():
    # First run the preflight to determine if worker is ready
    preflight = PreFlight.PreFlight(logger)
    if (preflight.check()):
        # Preflight has succeeded, now for the job
        job      = initJob()
        print "Job Loaded"
        print str(job)
        work = qb.requestwork()
        print "Init Command: \n" + job.getInitCMD() + "\n"
        print "Segment Command: \n" + job.getSegmentCMD(work) + "\n"
        print "Finalize Command: \n" + job.getFinalizeCMD() + "\n"
        print "Work-Command: \n" + job.getCMD(work)
        # state    = executeJob(job)
        # cleanupJob(job, state)
    
if __name__ == "__main__":
    main()