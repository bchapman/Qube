## -------------------------------------------------------------------------
##   
##   Qube Submit After Effects (aerender)
##
##   Copyright: PipelineFX L.L.C. 
##
## -------------------------------------------------------------------------

DATAPREFIX = ".DATA."
QUBESUBMISSIONSFOLDERNAME = "_Qube_Submissions"

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

sys.path.append("/Users/bchapman/Projects/Scripts+Apps/_Qube/_localRepo/Modules/")

# --------------------------

from simplecmd import SimpleSubmit
import logging
import inspect
import wx
import wx.lib.filebrowsebutton
import AESubmitWidget


rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/_submodules/')
import Transcoder

class aeScriptsWidget(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, value=wx.EmptyString, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, *args, **kwargs):
        wx.Panel.__init__ (self, parent, id, pos, size, style)

        self.SetMinSize(size)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.listbox = wx.ListBox(self, -1) # size=(250, 110)

        btnPanel = wx.Panel(self, -1, style=0)
        # btnPanel.SetMinSize(wx.DefaultSize)
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.addButton = wx.Button(btnPanel, -1, "Add", size=(75, 24))
        self.editButton = wx.Button(btnPanel, -1, "Edit", size=(75, 24))
        self.removeButton = wx.Button(btnPanel, -1, "Remove", size=(75, 24))
        self.clearButton = wx.Button(btnPanel, -1, "Clear", size=(75, 24))

        self.addButton.Bind(wx.EVT_BUTTON, self.AddButtonClick)
        self.editButton.Bind(wx.EVT_BUTTON, self.EditButtonClick)
        self.removeButton.Bind(wx.EVT_BUTTON, self.RemoveButtonClick)
        self.clearButton.Bind(wx.EVT_BUTTON, self.ClearButtonClick)
        
        btnSizer.Add(self.addButton, 1, wx.Top, 5)
        btnSizer.Add(self.editButton, 1, wx.Top, 5)
        btnSizer.Add(self.removeButton, 1, wx.Top, 5)
        btnSizer.Add(self.clearButton, 1, wx.Top, 5)

        btnPanel.SetSizer(btnSizer)

        sizer.Add( self.listbox, 1, wx.EXPAND|wx.ALL, 2)
        sizer.Add( btnPanel, 0, wx.RIGHT, 5)
        self.SetSizer(sizer)

        self.SetAutoLayout(True)
        self.Layout()
        self.SetDimensions(-1, -1, size[0], size[1], wx.SIZE_USE_EXISTING)
        
        self.count = 0

    def AddButtonClick(self, event=None):
        pass

    def EditButtonClick(self, event=None):
        pass

    def RemoveButtonClick(self, event=None):
        sel = self.listbox.GetSelection()
        if sel != -1:
            self.listbox.Delete(sel)

    def ClearButtonClick(self, event=None):
        self.listbox.Clear()

    def GetValue(self):
        return None

    def SetValue(self, items):
        pass

def create():        
    cmdjob = SimpleSubmit('Submit After Effects v2', hasRange=False, canChunk=False, help='After Effects rendering with progress and more.', category="2D", preDialog=preDialog, controlChanged=controlChanged)

    # Project Information
    cmdjob.add_optionGroup('Main')
    cmdjob.add_option( 'rqItem', 'choice', label='\nProject Path\n\n\n\nRender Queue\nItems\n\n\n\nSelected Item\'s\nOutputs\n', required=True,
                        editable=True, widget=AESubmitWidget.AEProjectWidget)
        
    # Required
    cmdjob.add_optionGroup('Required')
    cmdjob.add_option( 'notes', 'string', 'Notes about render', label='Notes',
                        required=True, lines=3, default=' ')
    cmdjob.add_option( 'email', 'string', 'Notification Email Address(s)', label='Email', editable=True, required=True, multi=True, choices=["brennan.chapman","collin.brooks"])

    # Transcoder
    cmdjob.add_optionGroup('Transcoder', collapsed=False)
    Transcoder.addTranscodeWidgetToDlg(cmdjob)

    # Advanced
    cmdjob.add_optionGroup('Advanced')
    cmdjob.add_option( 'quality', 'choice', label="Quality", required=True, editable=True, choices=["High", "Medium", "Low"])
    cmdjob.add_option( 'script', 'choice', label="Scripts", required=False, editable=True, widget=aeScriptsWidget)
    cmdjob.add_option( 'multProcs', 'bool', 'Use Multiple Processors', label='Multiple Processors',
                        required=False, default=False)

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows
    
    # Set some default job options
    cmdjob.properties['hostorder'] = '+host.memory.avail'
    cmdjob.properties['reservations'] = 'host.processors=1+' # Reserve all cpus for the one job
    cmdjob.properties['retrysubjob'] = 3
    cmdjob.properties['retrywork'] = 3
    cmdjob.properties['cpus'] = 10
    cmdjob.properties['priority'] = 100
    cmdjob.package.setdefault('shell', '/bin/bash')
    
    return [cmdjob]


def controlChanged(cmdjob, values, optionName, value, dlg, container):
    logging.info("Value changed")


# Setup the submission dialog
def preDialog(cmdjob, values):
	# Clear our any saved dependencies
	values['dependency'] = ''


# Cleanup & create copy of project to render from
def postDialog(cmdjob, values):
    
    valuesPkg = values.setdefault('package', {})
    ctrl = cmdjob.ctrl

    #################################################################################################################
    #
    # Create a copy of the original project to render from
    #
    #################################################################################################################
    
    sourceFilePath = valuesPkg.get('projectPath', '')
	
    newFilePath = ctrl.makeCopyOfProject(sourceFilePath, QUBESUBMISSIONSFOLDERNAME)

    # Store the translated projectPaths
    valuesPkg['projectPath'] = ctrl.translatePath(sourceFilePath)
    valuesPkg['renderProjectPath'] = ctrl.translatePath(newFilePath)

    
    #################################################################################################################
    #
    # Add the email callbacks
    #
    #################################################################################################################
    
    mail = valuesPkg.get('email', '')
    # If there is no @ specified, supply @fellowshipchurch.com
    if not ("@" in mail):
        mail = mail + "@fellowshipchurch.com"
    values['mailaddress'] = mail
    values['callbacks'] = [{'triggers':'done-job-self', 'language':'mail'}]
    # logging.info("Callbacks: " + str(values['callbacks']))
    # If I delete the email here, the Qube GUI Submission dialog won't remember it for next time
    # if valuesPkg.has_key('email'):     del valuesPkg['email'] # Delete the original option for cleanlinesss

    # Use the email as the user in Qube
    values['user'] = mail.split('@')[0]

    #################################################################################################################
    #
    # Move the notes to the qube notes field
    #
    #################################################################################################################

    notes = valuesPkg.get('notes', '')
    values['notes'] = notes
    # If I delete the notes here, the Qube GUI Submission dialog won't remember it for next time
    # if valuesPkg.has_key('notes'):     del valuesPkg['notes'] # Delete the original option for cleanlinesss

    #################################################################################################################
    #
    # Set up the Agenda to record percent progress.
    # We'll use a percentage based of 1-100.
    # I've tried setting this to frames, but the backend was
    # having trouble keeping up with qb.reportwork() on fast renders
    #
    #################################################################################################################

    values['agenda'] = qb.genframes("1-100")
    
    # Load the output paths
    rqItem = ctrl.getRQIndex(valuesPkg['rqIndex'].split('.')[0])
    valuesPkg['outputs'] = str(rqItem.getOutputPaths())
    # Store the output paths in the first agenda item as well
    values['agenda'][0]['resultpackage'] = { 'outputPaths': str(rqItem.getOutputPaths()) }
    
    # Store the paths to aerender for mac and pc
    valuesPkg['aerenderwin'] = ctrl.getAERenderPath(sysOS='win32')
    valuesPkg['aerendermac'] = ctrl.getAERenderPath(sysOS='darwin')


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
