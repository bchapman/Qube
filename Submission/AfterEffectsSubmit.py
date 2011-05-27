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

# --------------------------

from simplecmd import SimpleSubmit
import logging

import AEData


def create():        
    cmdjob = SimpleSubmit('AfterEffects', hasRange=False, canChunk=False, help='After Effects rendering with progress and more.', category="2D", controlChanged=controlChanged, preDialog=preDialog, postDialog=postDialog)

    # Initialize the AE Data Class
    cmdjob.ctrl = AEData.Controller(logging)

    # Project Information
    cmdjob.add_optionGroup('Info')
    cmdjob.add_option( 'projectPath', 'file' , 'Project Name', label='Project File',
                        mode='open', required=True, editable=True)
    cmdjob.add_option( 'rqIndex', 'choice', 'RQ Item index and comp name.', label='RQ Item',
                        required=True, editable=True)
    cmdjob.add_option( 'outputs', 'choice', 'Output Paths.', label='Outputs',
                        required=True, editable=False, multi=True, choices=['None'])
    
    # Required
    cmdjob.add_optionGroup('Required', collapsed=False)
    cmdjob.add_option( 'notes', 'string', 'Notes about render', label='Notes',
                        required=True, lines=4, default=' ')
    cmdjob.add_option( 'email', 'string', 'Notification Email Address(s)', label='Email',
                        required=True, lines=1, default='')

    # Additional properties to set
    cmdjob.properties['flagsstring'] = 'disable_windows_job_object'  # Needs to be disabled for Windows
    
    # Set some default job options
    cmdjob.properties['hostorder'] = '+host.memory.avail'
    cmdjob.properties['reservations'] = 'host.processors=1+' # Reserve all cpus for the one job
    cmdjob.package.setdefault('shell', '/bin/bash')
    
    return [cmdjob]

# Custom method to update the choices for listboxes
# The SimpleCMD framework only supports updating values directly
def updateChoiceList(dlg, valuesPkg, optName, newChoices, selection):
        logging.debug("Updating ChoiceList: " + str(optName) + " Selection: " + str(selection))
        for s in dlg.propertyBoxSizers:
            if (optName in s.optionNames):
                s.options[optName]['choices'] = newChoices
                s.widgets[optName]['entry'].Clear() # Clear the current choices
                s.widgets[optName]['entry'].AppendItems(newChoices)
                if isinstance(selection, list):
                    if (len(selection) > 0):
                        for sel in selection:
                            s.widgets[optName]['entry'].Check(sel)
                else:
                    s.widgets[optName]['entry'].SetSelection(selection)


# Updates dialog when controls are changed
def controlChanged(cmdjob, values, optionName, value, dlg, container):

    # Pointers
    valuesPkg = values.setdefault('package', {})
    ctrl = cmdjob.ctrl
    
    sequence = False

    # Project Path Updates
    if (optionName == "projectPath"):
        # Make sure the file exists and is an after effects project before updating
        if (os.path.exists(value) and os.path.splitext(value)[1] == '.aep'):
            
            projectPath = value

            # Set the qube job name to the name of the ae project without extension
            values['name'] = os.path.splitext(os.path.basename(projectPath))[0]
            
            # Determing the path to the AE Data File
            projectPathSplit = os.path.split(projectPath)
            dataPath = os.path.join(projectPathSplit[0], DATAPREFIX + projectPathSplit[1])

            makeDataFile = False # Sentinel to check if we need to make a new data file
            
            # Check whether the data file exists or not
            if os.path.exists(dataPath):
                logging.debug("Data file found:\n" + dataPath)
        
                # Load the data and check the hash
                if not ctrl.loadDataFile(dataPath):
                    makeDataFile = True
                    logging.info('Invalid Data File.')
        
                # Calculate the hash of the project file
                projHash = ctrl.getFileHash(projectPath)
                logging.debug("Project Hash Code: " + projHash)

                # Compare this hash to the hash stored in the file
                dataHash = ctrl.getDataHash()
                logging.debug("Data Hash Code: " + str(dataHash))
                if (str(projHash) != str(dataHash)):
                    makeDataFile = True
                    logging.info("Hash Codes don't match between the project and data file.")
                    
            else:
                makeDataFile = True
                logging.info("No data file found for project.")

            if (makeDataFile):
                ctrl.makeDataFile()
                if not ctrl.loadDataFile(dataPath):
                    logging.error('Unable to load data file.')

            # If specified, get the rqIndex passed from After Effects
            rqIndex = valuesPkg.get('rqIndex', '1').strip()
            if not rqIndex.isdigit():
                rqIndex = 1
            
            # Override with settings from After Effects if present
            if (ctrl.data.selRQIndex != ''):
                rqIndex = int(ctrl.data.selRQIndex[0])
                # Remove it now that we've used it
                ctrl.data.selRQIndex = ''
            
            # Load the RQ Item Choices into the dialog
            rqChoices = ctrl.getRQChoices()
            logging.debug("Updating Render Choices: " + str(rqChoices))
            updateChoiceList(dlg, valuesPkg, 'rqIndex', rqChoices, int(rqIndex)-1)

            # Locate the rqItem with the specified index
            rqItem = ctrl.getRQIndex(rqIndex)
            
            # Load the outputs list box
            outputs = rqItem.getOutputNames()
            # Make all outputs selected
            selection = []
            for i in range(0, len(outputs)):
                selection.append(i)
            updateChoiceList(dlg, valuesPkg, 'outputs', outputs, selection)
            
            # Use expand flag if the output is a sequence
            sequence = False
            for item in outputs:
                if ctrl.isSequence(item):
                    sequence = True
            
        else:
            valuesPkg = values.setdefault('package', {})
            # Prompt user that there was an error loading the project file
            updateChoiceList(dlg, valuesPkg, 'rqIndex', ['Invalid Project File'], 0)
            # Clear the outputs field
            updateChoiceList(dlg, valuesPkg, 'outputs', ['None'], [])

    # rqItem dropdown
    elif (optionName == "rqIndex"):
        # Check first character of the list box value to make sure it's a valid RQ Item
        if value[0].isdigit():
            rqIndex = value[0]
            rqItem = ctrl.getRQIndex(rqIndex)
            outputs = rqItem.getOutputNames()
            
            # Make all outputs selected
            selection = []
            for i in range(0, len(outputs)):
                selection.append(i)
            updateChoiceList(dlg, valuesPkg, 'outputs', outputs, selection)
            
            # Use expand flag if the output is a sequence
            sequence = False
            for item in outputs:
                if ctrl.isSequence(item):
                    sequence = True

    if sequence:
        values['flagsstring'] = values['flagsstring'] + ",expand"
    else:
        values['flagsstring'] = values['flagsstring'].replace(',expand', '')
        


# Setup the submission dialog
def preDialog(cmdjob, values):
    
    # Store the rqIndex that After Effects sends
    rqIndex = values.setdefault('package', {}).get('rqIndex', '');
    if (rqIndex != ''):
        cmdjob.ctrl.data.selRQIndex = rqIndex
    
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
    logging.info("Callbacks: " + str(values['callbacks']))
    if valuesPkg.has_key('email'):     del valuesPkg['email'] # Delete the original option for cleanlinesss

    #################################################################################################################
    #
    # Move the notes to the qube notes field
    #
    #################################################################################################################

    notes = valuesPkg.get('notes', '')
    values['notes'] = notes
    if valuesPkg.has_key('notes'):     del valuesPkg['notes'] # Delete the original option for cleanlinesss

    #################################################################################################################
    #
    # Set up the Agenda to record percent progress.
    # We'll use a percentage based of 1-100.
    # I've tried setting this to frames, but the backend was
    # having trouble keeping up with qb.reportwork() on fast renders
    #
    #################################################################################################################

    values['agenda'] = qb.genframes("1-100")
    
    # Store the paths to aerender for mac and pc
    valuesPkg['aerenderwin'] = ctrl.getAERenderPath(sysOS='win32')
    valuesPkg['aerendermac'] = ctrl.getAERenderPath(sysOS='darwin')
    
## ======================================================================


if __name__ == '__main__':
    import logging
    import sys
    import simplecmd
    import submit
    logging.basicConfig(level=logging.DEBUG)
    app = simplecmd.TestApp(redirect=False)
    cmds = create()
    logging.info("Monkey")
    for cmd in cmds:
        simplecmd.createSubmitDialog(cmd)
    app.MainLoop()
