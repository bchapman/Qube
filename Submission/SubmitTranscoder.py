'''
Qube Transcoder Submission Dialog
Author: Brennan Chapman
'''

import os, sys

from simplecmd import SimpleSubmit
import logging

sys.path.append("/Users/bchapman/Projects/Scripts+Apps/_Qube/_localRepo/Modules/")
import Transcoder

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def create():        
    cmdjob = SimpleSubmit('Submit Transcoder', hasRange=False, canChunk=False, help='Cluster based transcoder using blender.', postDialog=postDialog, category="2D")

    # Project Information
    cmdjob.add_optionGroup('Transcoder')
    Transcoder.addTranscodeWidgetToDlg(cmdjob)

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows
    
    # Set some default job options
    cmdjob.package.setdefault('shell', '/bin/bash')
    
    return [cmdjob]

def preDialog(cmdjob, values):
    '''
    Set required defaults.
    '''
    values['hostorder'] = '+host.memory.avail'
    values['reservations'] = 'host.processors=2'
    values['retrysubjob'] = 3
    values['retrywork'] = 3
    values['cpus'] = 50
    values['priority'] = 100


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
