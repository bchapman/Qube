'''
Qube Transcoder Submission Dialog
Author: Brennan Chapman
'''

import os, sys

from simplecmd import SimpleSubmit
import logging
import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/SubmitTranscoder_Files/')
import Transcoder

def create():        
    cmdjob = SimpleSubmit('Submit Transcoder', hasRange=False, canChunk=False, help='Cluster based transcoder using blender.', postDialog=postDialog, category="2D")

    # Project Information
    cmdjob.add_optionGroup('Transcoder')
    Transcoder.addTranscodeWidgetToDlg(cmdjob)

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows
    
    # Set some default job options
    cmdjob.properties['hostorder'] = '+host.memory.avail'
    cmdjob.properties['reservations'] = 'host.processors=2'
    cmdjob.properties['retrysubjob'] = 3
    cmdjob.properties['retrywork'] = 3
    cmdjob.package.setdefault('shell', '/bin/bash')
    
    return [cmdjob]

def postDialog(cmdjob, values):

    Transcoder.prepareJobsFromDlg(values)
    raise Exception, "There is hope in the red letters."

if __name__ == '__main__':
    import simplecmd
    # import logging
    # import sys
    # import submit
    logging.basicConfig(level=logging.DEBUG)
    app = simplecmd.TestApp(redirect=False)
    cmds = create()
    logging.info("Monkey")
    for cmd in cmds:
        simplecmd.createSubmitDialog(cmd)
    app.MainLoop()
