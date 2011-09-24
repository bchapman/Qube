## -------------------------------------------------------------------------
##   
##   Qube Submit After Effects (aerender)
##
##   Copyright: PipelineFX L.L.C. 
##
## -------------------------------------------------------------------------

import os, sys

# == import qb ==
# Determine qbdir (currently used for locating qb module and docs)
if os.environ.get('QBDIR', '') != '':  # if QBDIR exists and is not empty
    qbdir = os.environ['QBDIR'].strip()
    print "Qube location (from QBDIR): '%s'" % qbdir
else:
    # Determine QBDIR from platform defaults
    if sys.platform == 'darwin': # mac
        qbdir = '/Applications/pfx/qube'
    elif sys.platform[:5] == 'linux': # matches linux*
        qbdir = '/usr/local/pfx/qube'
    elif sys.platform[:3] == 'win':
        qbdir = 'c:/Program Files/pfx/qube'
    else:
        print ("ERROR: Unknown platform %s" % sys.platform)
        sys.exit(-1)
    print "Qube location (default): %s" % qbdir
sys.path.append('%s/api/python' % qbdir)
print 'Appending to python path "%s/api/python"' % qbdir
import qb
import qbCache

# --------------------------

from simplecmd import SimpleSubmit
import logging
import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/SubmitTranscoder_Files/')
import Transcoder

def create():        
    cmdjob = SimpleSubmit('Submit Transcoder', hasRange=False, canChunk=False, help='Cluster based transcoder using blender.', postDialog=postDialog, category="2D")

    # Initialize the AE Data Class
    # cmdjob.ctrl = SubmitAfterEffectsClasses.Controller(logging)

    # Project Information
    cmdjob.add_optionGroup('Transcoder')
    Transcoder.addTranscodeWidgetToDlg(cmdjob)
    # cmdjob.add_option( 'transcodeJobs', 'choice', label='Transcoder Jobs', required=True,
    #                     editable=True, widget=Transcoder.TranscoderWidget)

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows
    
    # Set some default job options
    cmdjob.properties['hostorder'] = '+host.memory.avail'
    cmdjob.properties['reservations'] = 'host.processors=2' # Reserve all cpus for the one job
    cmdjob.properties['retrysubjob'] = 3
    cmdjob.properties['retrywork'] = 3
    cmdjob.package.setdefault('shell', '/bin/bash')
    
    return [cmdjob]

# Cleanup & create copy of project to render from
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
