## -------------------------------------------------------------------------
##   
##   Qube Submit After Effects (aerender)
##
##   Copyright: PipelineFX L.L.C. 
##
## -------------------------------------------------------------------------

DATAPREFIX = ".DATA."
QUBESUBMISSIONSFOLDERNAME = "_Qube_Submissions"
ELEVATEPREFSFILE = "~/Library/Preferences/qube/Elevate_AfterEffects.plist"

import os, sys

ELEVATEPREFSFILE = os.path.expanduser(ELEVATEPREFSFILE)

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

# --------------------------

from simplecmd import SimpleSubmit
import logging
import wx
import wx.lib.filebrowsebutton
import time
import shutil
import plistlib
import qbCache
import copy
import re
import traceback

# sys.path.append("/Users/bchapman/Projects/Scripts+Apps/_Qube/_localRepo/Modules/")
sys.path.append("/Volumes/theGrill/.qube/Modules/")

import AESubmitWidget
import Transcoder
import sequenceTools

rootLogger = logging.getLogger()
# rootLogger.setLevel(logging.DEBUG)

class aeScriptsWidget(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, value=wx.EmptyString, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, *args, **kwargs):
        wx.Panel.__init__ (self, parent, id, pos, size, style)

        self.SetMinSize(size)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.listbox = wx.ListBox(self, -1)

        btnPanel = wx.Panel(self, -1, style=0)
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
    cmdjob = SimpleSubmit('Submit After Effects v2', hasRange=False, canChunk=False, help='After Effects rendering with progress and more.', category="2D", preDialog=preDialog, postDialog=postDialog, controlChanged=controlChanged)

    # Project Information
    cmdjob.add_optionGroup('Main')
    cmdjob.add_option( 'aeProject', 'file', label='\nProject Path\n\n\n\nRender Queue\nItems\n\n\n\nSelected Item\'s\nOutputs\n', required=True, editable=True, widget=AESubmitWidget.AEProjectWidget)

    # Required
    cmdjob.add_optionGroup('Required')
    cmdjob.add_option( 'notes', 'string', 'Notes about render', label='Notes',
                        required=True, lines=3, default=' ')
    cmdjob.add_option( 'email', 'string', 'Notification Email Address(s)', label='Email', editable=True, required=True, multi=False, choices=[])

    # Transcoder
    # cmdjob.add_optionGroup('Transcoder', collapsed=False)
    # Transcoder.addTranscodeWidgetToDlg(cmdjob)

    # Advanced
    cmdjob.add_optionGroup('Advanced')
    cmdjob.add_option( 'quality', 'choice', label="Quality", required=True, editable=True, choices=["High", "Medium", "Low"])
    cmdjob.add_option( 'complexity', 'choice', label="Complexity", required=True, editable=True, choices=["Complex", "Normal", "Simple"], default="Normal")
    # cmdjob.add_option( 'scripts', 'choice', label="Scripts", required=False, editable=True, widget=aeScriptsWidget)
    # cmdjob.add_option( 'multProcs', 'bool', 'Use Multiple Processors', label='Multiple Processors', required=False, default=False)
    # cmdjob.add_option( 'chunkSize', 'int', 'Chunk size for agenda.', label='Frames Per Task', default=10, required=True)

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows

    return [cmdjob]


def preDialog(cmdjob, values):
    valuesPkg = values.setdefault('package', {})
	# Clear our any saved dependencies
    values['dependency'] = ''
    
    # Set required defaults, we don't want previous settings
    # to mess with these.
    values['retrysubjob'] = 3
    values['retrywork'] = 3
    values['priority'] = 100
    values['cpus'] = 10
    values['hostorder'] = '+host.memory.avail'
    values['reservations'] = 'host.processors=1+' # Reserve all cpus for the one job
    cmdjob.package.setdefault('shell', '/bin/bash')
    values['cluster'] = "/Animation"
    values['group'] = "AfterEffects"
	
    aeProjPkg = {}
	
    try:
        elevatePrefs = plistlib.readPlist(ELEVATEPREFSFILE)
        
        cmdjob.options['email']['choices'] = elevatePrefs['emailHistory']
        projectHistory = set(elevatePrefs['projectHistory'])
        logging.debug("Found Project History in Prefs: %s" % projectHistory)
        if valuesPkg.has_key('sourceProjectPath'):
            projectHistory.add(valuesPkg['sourceProjectPath'])
            logging.debug("Found sourceProjectPath: %s" % valuesPkg['sourceProjectPath'])
        
        projectHistory = list(projectHistory)
        projectHistory.reverse()
        aeProjPkg['projectHistory'] = projectHistory
        
        valuesPkg['notes'] = values['notes']
        
        logging.warning("Loaded Elevate Prefs.")
        
    except Exception, e:
        logging.warning("Unable to load Elevate Prefs. %s" % e)

    if valuesPkg.has_key('setProjectPath'):
        logging.debug("Found setProjectPath: %s" % valuesPkg['setProjectPath'])
        aeProjPkg['setProjectPath'] = valuesPkg['setProjectPath']
        valuesPkg['gui'] = False
    else:
        valuesPkg['gui'] = True
        logging.debug("Did not find setProjectPath.")
    valuesPkg['aeProject'] = aeProjPkg



def controlChanged(cmdjob, values, optionName, value, dlg, container):
    logging.debug("Value changed. %s" % optionName)
    
    if optionName == "aeProject":
        newName = os.path.splitext(os.path.basename(value['projectPath']))[0]
        logging.debug("New Job name: %s" % newName)
        values['name'] = newName


def postDialog(cmdjob, values):
    '''
    Prepare the output of the dialog.
    Each rqitem is separated into its own job.
    Store all history related info to a separate plist file
        Project History
        Email History
    
    Contents of each job:
        Universal:
            sourceProjectPath - original AE project file
            renderProjectPath - AE Project to render from
            user - set to email address contents before @
            email - set to @fellowshipchurch.com if @ not specified.
            notes - user specified notes for the job
            chunkSize - chunk size for the agenda
            quality - render quality for the project, based on a custom script
            callbacks:
                mail

        RQ Item Specific:
            rqIndex - rqIndex to render
            cpus - based on output type (only 1 if mov)
            outputFiles - list of outputFiles for that rqItem
            agenda - frames split up based on chunkSize for the job
            frameCount - total number of frames to render
    '''
    valuesPkg = values.setdefault('package', {})

    pValue = 0
    pIncrement = 10
    maxProgress = len(valuesPkg['aeProject']['rqItems']) * pIncrement * 2 + 50
    pDlg = wx.ProgressDialog ( 'Submitting Project...', 'Saving prefs...', maximum = maxProgress)
    pDlg.SetSize((300, -1))
    
    try:
        '''
        ----------------------------------------------------------------------------------------
        First, save any history related items to the Elevate Plist
        ----------------------------------------------------------------------------------------
        '''
        elevatePrefs = {}

        elevatePrefs['projectHistory'] = valuesPkg['aeProject']['projectHistory']
        emailList = set(cmdjob.options['email']['choices'])
        emailList.add(valuesPkg['email'])
        if len(emailList) > 10:
            emailList = emailList[0:9]
        elevatePrefs['emailHistory'] = list(emailList)
        logging.debug("emailHistory: %s" % elevatePrefs['emailHistory'])
        plistlib.writePlist(elevatePrefs, ELEVATEPREFSFILE)

        '''
        ----------------------------------------------------------------------------------------
        Second, setup everything that will apply to all the rqItems
        ----------------------------------------------------------------------------------------
        '''
        pValue += pIncrement
        pDlg.Update(pValue, "Copying original project...")

        '''
        Create a copy of the original project to render from
        '''
        sourceProjPath = valuesPkg['aeProject']['projectPath']
    
        logging.debug("Making a copy of the project for rendering...")

        #Create the time string to be placed on the end of the AE file
        fileTimeStr = time.strftime("_%m%d%y_%H%M%S", time.gmtime())

        #Copy the file to the project files folder and add the time on the end
        sourceFolderPath, sourceProjName = os.path.split(sourceProjPath)
        newFolderPath = os.path.join(sourceFolderPath, QUBESUBMISSIONSFOLDERNAME)
        newProjName = os.path.splitext(sourceProjName)[0] + fileTimeStr + '.aep'
        newProjPath = os.path.join(newFolderPath, newProjName)

        try:
            if not (os.path.exists(newFolderPath)):
                os.mkdir(newFolderPath)
        except:
            raise("Unable to create the folder %s" % newFolderPath)

        try:
            shutil.copy2(sourceProjPath, newProjPath)
            logging.info("Project file copied to %s" % newProjPath)
        except:
            raise("Unable to create a copy of the project under %s" % newProjPath)

        valuesPkg['sourceProjectPath'] = str(sourceProjPath)
        logging.debug("sourceProjectPath: %s" % valuesPkg['sourceProjectPath'])
        valuesPkg['renderProjectPath'] = str(newProjPath)
        logging.debug("renderProjectPath: %s" % valuesPkg['renderProjectPath'])

        '''
        Setup the email, user, notes, chunkSize, quality, and callbacks.
        '''
        pValue += pIncrement
        pDlg.Update(pValue, "Setting up qube jobs...")
    
        if "@" not in valuesPkg['email']:
            valuesPkg['email'] += "@fellowshipchurch.com"
        values['mailaddress'] = valuesPkg['email']
        values['user'] = valuesPkg['email'].split("@")[0]
        values['notes'] = valuesPkg.get('notes', '').strip()
        values['callbacks'] = [{'triggers':'done-job-self', 'language':'mail'}]    

        '''
        ----------------------------------------------------------------------------------------
        Third, setup each rqItem's job
        ----------------------------------------------------------------------------------------
        '''
    
        '''
        Setup the name, rqIndex, outputFiles, agenda and cpus.
        '''
        rqJobs = []
        seqPattern = re.compile("\[#+\]")        
        for rqItem in valuesPkg['aeProject']['rqItems']:

            outPaths = []
            for item in rqItem['outFilePaths']:
                outPaths.append(str(item))

            sequence = True
            if ".mov" in ",".join(outPaths):
                sequence = False

            pValue += pIncrement
            pDlg.Update(pValue, "Setting up RQ Item: %s..." % rqItem['comp'])
            
            rqiValues = copy.deepcopy(values)
            rqiPkg = rqiValues.setdefault('package', {})
            rqiPkg['rqIndex'] = str(rqItem['index'])
            rqiValues['name'] = "%s %s-%s" % (values['name'], rqItem['index'], rqItem['comp'])
            rqiPkg['outputFiles'] = ",".join(outPaths)
            logging.debug("Output File Paths: %s" % rqItem['outFilePaths'])
            agendaRange = str("%s-%s" % (rqItem['startTime'], int(rqItem['stopTime'])-1))
            logging.debug("Agenda Range: %s" % agendaRange)
            chunkSize = 30
            if not sequence:
                rqiValues['cpus'] = 1
                chunkSize = 1000000
            rqiValues['agenda'] = qb.genchunks(chunkSize, agendaRange)
            logging.debug("Agenda: %s" % rqiValues['agenda'])
            rqiValues['agenda'][-1]['resultpackage'] = {'outputPaths':",".join(outPaths)}
            rqiPkg['frameCount'] = int(rqItem['stopTime']) - int(rqItem['startTime']) - 1

            '''
            If it's a sequence, mark all existing frames as complete.
            '''
            if sequence:
                
                for path in outPaths:
                    pValue += pIncrement
                    pDlg.Update(pValue, "Finding missing frames for %s..." % os.path.basename(path))
                
                    seqPad = len(seqPattern.findall(path)[-1]) - 2
                    initFrame = sequenceTools.padFrame(rqItem['startTime'], seqPad)
                    initPath = seqPattern.sub(initFrame, path)
                    logging.debug("initPath: %s" % initPath)
                    seq = sequenceTools.Sequence(initPath, frameRange=agendaRange)
                    missingFrames = seq.getMissingFrames()
                    logging.debug("Missing Frames: %s" % missingFrames)

                    for task in rqiValues['agenda']:
                        logging.debug("Name: %s" % task['name'])
                        if "-" in task['name']:
                            tStart, tEnd = task['name'].split("-")
                        else:
                            tStart = tEnd = task['name']
                        tRange = range(int(tStart), int(tEnd) + 1)
                        found = False
                        for frame in tRange:
                            if frame in missingFrames:
                                found = True
                        if not found:
                            task['status'] = 'complete'
                            if task.has_key("resultPackage"):
                                task['resultpackage']['progress'] = '1' # 100% chunk progress
                            else:
                                task['resultpackage'] = {'progress':'1'}
                            logging.debug("Marking task as complete: %s" % task)

            '''
            Delete any unecessary attributes
            '''
            rqiPkg['aeProject'] = None
            del rqiPkg['aeProject']
            rqiPkg['notes'] = None
            del rqiPkg['notes']
            rqiPkg['gui'] = None
            del rqiPkg['gui']
        
            rqJobs.append(rqiValues)
    
        logging.debug("rqJobs: %s" % rqJobs)

        pValue += pIncrement
        pDlg.Update(pValue, "Submitting Jobs to qube...")

        submittedJobs = qb.submit(rqJobs)
        logging.debug("Submitted Jobs: %s" % submittedJobs)

        pValue += pIncrement
        pDlg.Update(pValue, "Refreshing Qube...")

        # Update the Qube GUI
        request = qbCache.QbServerRequest(action="jobinfo", value=[i['id'] for i in submittedJobs], method='reload')
        qbCache.QbServerRequestQueue.put(request)

        pDlg.Update(maxProgress, "Complete!")
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        dlg = wx.MessageDialog(None, "Unable to submit jobs %s" % e, "Error", wx.OK | wx.ICON_ERROR)
        logging.error(repr(traceback.format_exception(exc_type, exc_value,exc_traceback)))
        dlg.ShowModal()

    pDlg.Destroy()

    # Cancel the rest of submission because we already submitted the jobs.
    if valuesPkg['gui']:
        # Raise an exception if submittion via gui
        raise Exception, "All jobs submitted successfully."
    else:
        # If submitting elsewhere, exit
        sys.exit(0)

if __name__ == '__main__':
    import simplecmd
    logging.basicConfig(level=logging.DEBUG)
    app = simplecmd.TestApp(redirect=False)
    cmds = create()
    for cmd in cmds:
        simplecmd.createSubmitDialog(cmd)
    app.MainLoop()
