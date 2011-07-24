import sys
sys.path.append('..')
import os
import logging
import re

from simplecmd import SimpleCmd

helpText = '''
Nuke5.1v2 --help
Usage: nuke <switches> <script> <argv> <ranges>
  -a       formats default to anamorphic
  -b       start in background (fork)
  -c size  limit cache memory usage. Size is in bytes, or append k, M, G or T
  -d name  set X display name
  -f       run full-size (turn off proxy)
  -help    print this help and exit
  -i       with -x or -t use interactive, not render, license
  -l       apply linear transfer to the file read in
  -m n     set threads to n
  -n       don't run postagestamps, don't open windows
  -p       turn on proxy mode
  -q       quiet (don't print stuff)
  -s n     sets the minimum stack size for each thread in bytes, this defaults
           to 16777216 (16MB) the smallest allowed value is 1048576 (1MB)
  -t       terminal only (no gui)
  -V       verbosity (print more stuff)
  -v       nukev (rest of command line is image files to view)
  -view v  only execute these views (comma-separated list: e.g. 'left,right')
  -version print version information and exit
  -x       execute the script (rather than edit it)
  -X nodes only execute these nodes (comma-seperated list)
  --       end switches, allowing script to start with a dash or be just - to read from stdin
<script>:
  name of a .nuke script to create, edit, or execute
  "-" means stdin
<argv>:
  All words between the script name and the frame ranges can be used by
  [argv n] expressions to provide changing arguments to the script.
  Each must start with a non-digit to avoid confusion with frame ranges.
<ranges>:
  (only if no -F switch) frame numbers to execute:
  A       single frame number A
  A-B     all frames from A through B
  A-B/C   every C'th frame from A to last one less or equal to B
'''

def create():
    def isNukeXSupported(nukeExec):
        # NukeX only supported in versions 6.x and up
        try:
            nukeMajorVer = re.search('Nuke(\d+)', nukeExec).group(1)
        except:
            nukeMajorVer = 0
        return bool(int(nukeMajorVer) >= 6)

    def cmdjob_controlChanged(cmd, values, optionName, value, dlg, container):
        #logLevel = logging.getLogger().level
        #logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("nuke cmdline:cmdjob_controlChanged: %s %s" % (optionName, value))

        if optionName == 'executable':
            if isNukeXSupported(value):
                dlg.packageControls['--nukeX'].Enable(True)
            else:
                dlg.packageControls['--nukeX'].Enable(True)  # to set the value to False below
                dlg.packageControls['--nukeX'].SetValue(False)
                dlg.packageControls['--nukeX'].Enable(False)
                values['package']['--nukeX'] = False
        
        if optionName == 'script':
            values['name'] = os.path.splitext(os.path.basename(value))[0]

        #logging.getLogger().setLevel(logLevel)

    def preDialog(cmdJob, values):
        if isNukeXSupported(values['package'].get('executable', '')):
            cmdJob.options['--nukeX']['editable'] = True
        else:
            cmdJob.options['--nukeX']['editable'] = False
            values.setdefault('package', {})['--nukeX'] = False

    def postDialog(cmdjob, values):
        
        valuesPkg = values.setdefault('package', {})
        
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

    # Create Nuke Render    
    cmdjob = SimpleCmd('Submit Nuke', hasRange=True, canChunk=True, help='Nuke Render JobType',
            preDialog=preDialog,
            postDialog=postDialog,
            controlChanged=cmdjob_controlChanged)

    cmdjob.category="2D"
    cmdjob.install = install  # COMPATIBILITY: As of Qube 5.3.1, "install" parameter specifyable in SimpleCmd.__init__()
    cmdjob.command = ('"%(executable)s" -t -x %(argv)s -- "%(script)s" %(scriptArgs)s QB_FRAME_START,QB_FRAME_END,QB_FRAME_STEP')

    cmdjob.add_optionGroup('Required')
    cmdjob.add_option( 'executable', 'file' , 'explicit path to Nuke executable', mode='open', default = '/usr/local/nuke',
                      choices=['Nuke5.0',
                               'Nuke5.1',
                               'Nuke5.2',
                               'Nuke6.0',
                               'C:/Program Files/Nuke5.0v1/Nuke5.0.exe',
                               'C:/Program Files/Nuke5.1v6/Nuke5.1.exe',
                               'C:/Program Files/Nuke5.2v2/Nuke5.2.exe',
                               'C:/Program Files/Nuke6.0v1/Nuke6.0.exe',
                               'C:/Program Files/Nuke6.0v5/Nuke6.0.exe',
                               'C:/Program Files/Nuke6.0v7/Nuke6.0.exe',
                               'C:/Program Files/Nuke6.1v1/Nuke6.1.exe',
                               '/Applications/Nuke5.0v1/Nuke5.0v1.app/Contents/MacOS/Nuke5.0v1',
                               '/Applications/Nuke5.1v6/Nuke5.1v6.app/Contents/MacOS/Nuke5.1v6',
                               '/Applications/Nuke5.2v2/Nuke5.2v2.app/Contents/MacOS/Nuke5.2v2',
                               '/Applications/Nuke6.0v1/Nuke6.0v1.app/Contents/MacOS/Nuke6.0',
                               '/Applications/Nuke6.0v5/Nuke6.0v5.app/Contents/MacOS/Nuke6.0',
                               '/Applications/Nuke6.0v7/Nuke6.0v7.app/Contents/MacOS/Nuke6.0',
                               '/Applications/Nuke6.1v1/Nuke6.1v1.app/Contents/MacOS/Nuke6.1',
                               '/usr/local/Nuke5.0v1/Nuke5.0',
                               '/usr/local/Nuke5.1v6/Nuke5.1',
                               '/usr/local/Nuke5.2v2/Nuke5.2',
                               '/usr/local/Nuke6.0v1/Nuke6.0',
                               '/usr/local/Nuke6.0v5/Nuke6.0',
                               '/usr/local/Nuke6.0v7/Nuke6.0',
                               '/usr/local/Nuke6.1v1/Nuke6.1',
                               ])
    cmdjob.add_option( '--nukeX', 'flag', label='load NukeX', editable=False, default=False )
    cmdjob.add_option( 'script'    , 'file' , 'nuke script to render', mode='open', default = '',  mask='Nuke Script (*.nk)|*.nk|All files (*.*)|*.*', required=True, label='Script')
    
    # Elevate
    # Add quicker access to notes and email
    cmdjob.add_optionGroup('General')
    cmdjob.add_option( 'notes', 'string', 'Notes about render', label='Notes',
                        required=True, lines=3, default=' ')
    cmdjob.add_option( 'email', 'string', 'Notification Email Address(s)', label='Email',
                        required=True, lines=1)
    
    cmdjob.add_optionGroup('Render Nodes and Script Args')
    cmdjob.add_option( 'executeViews', 'string', "only execute these views (comma-separated list: e.g. 'left,right')", arg='-view', label='execute views')
    cmdjob.add_option( 'executeNodes', 'string', 'execute only this node', arg='-X', label='execute nodes')
    cmdjob.add_option( 'scriptArgs', 'string', 'All words between the script name and the frame ranges can be used by [argv n] expressions to provide changing arguments to the script. Each must start with a non-digit to avoid confusion with frame ranges.', label='script args')
    cmdjob.add_optionGroup('Optional Switches')
    cmdjob.add_option( '-a', 'flag', 'formats default to anamorphic', label='anamorphic')
    cmdjob.add_option( '-b', 'flag', 'start in background (fork)', label='background')
    cmdjob.add_option( '-c', 'string', 'limit cache memory usage. Size is in bytes, or append k, M, G or T', label='cache size')
    # -d
    # -f
    # -help
    cmdjob.add_option( '-i', 'flag', 'with -x or -t use interactive, not render, license', label='interactive')
    cmdjob.add_option( '-l', 'flag', 'apply linear transfer to the file read in', label='linear transfer')
    cmdjob.add_option( '-m', 'int', 'set threads to n', label='threads')
    # -n
    cmdjob.add_option( '-p', 'flag', 'turn on proxy mode', label='proxy mode')
    cmdjob.add_option( '-q', 'flag', 'quiet (do not print stuff)', label='quiet')
    cmdjob.add_option( '-s', 'int', 'sets the minimum stack size for each thread in bytes, this defaults to 16777216 (16MB) the smallest allowed value is 1048576 (1MB)', label='stack size')
    # -t        (See command)
    cmdjob.add_option( '-V', 'flag', 'verbosity (print more stuff)', label='verbose')
    # -v
    # -view     (See parameter above)
    # -version
    # -x        (See command)
    # -X        (See parameter above)
    # --        (See command)

    cmdjob.properties['cpus'] = 10
    # Specify hardcoded package values
    #cmdjob.package.setdefault('regex_highlights', '\n'.join([r'Warning:', 'Error:', 'ERROR:']))
    #cmdjob.package.setdefault('regex_errors', '\n'.join([r'command not found']))
    cmdjob.package.setdefault('regex_outputPaths', '\n'.join([r'Writing (.*) took [0-9.\-]+ seconds']))
    
    return [cmdjob]

def install():
    '''install the interface in Nuke.  Requires QubeGUI 5.3.1 or later.'''

    # Determine the user's scripts dir
    scriptsDir = os.path.expanduser('~/.nuke')
    
    # Make directory if it does not exist
    if not os.path.exists(scriptsDir):
        logging.info('Making directory path "%s"'%scriptsDir)
        os.makedirs(scriptsDir)

    # == Write ~/.nuke/qube_menu.py ======
    qube_addUI = r"""
import os
import os.path
import sys
import nuke

def addMenuItems():
    menubar = nuke.menu('Nuke')
    renderMenu = menubar.findItem('Render')
    if renderMenu == False:
        renderMenu = menubar.addMenu('&Render')
    renderMenu.addCommand("+ Qube: Render All..."     , "import qube_menu; qube_menu.submitNuke_renderAll()")
    renderMenu.addCommand("+ Qube: Render Selected...", "import qube_menu; qube_menu.submitNuke_renderSelected()")
    renderMenu.addCommand("+ Qube: Launch GUI"        , "import qube_menu; qube_menu.launchgui()")

def launchgui(qubeguiPath='', submitDict={}, guiargs=''):
    '''launch the QubeGUI with the specified parameters'''
    # Construct parameter list
    cmdDict = {
                'qubeguiPath': qubeguiPath,
                'qubeguiArgString': '',
              }
    if len(submitDict) > 0:  cmdDict['qubeguiArgString'] += ' --submitDict "%s"'%submitDict
    if len(guiargs) > 0   :  cmdDict['qubeguiArgString'] += ' '+guiargs

    # Construct command for the specific platforms        
    if sys.platform[:3] == 'win':
        if cmdDict['qubeguiPath'] == '': cmdDict['qubeguiPath'] = 'C:/Program Files/pfx/qube/bin/qube.exe'
        if not os.path.exists(cmdDict['qubeguiPath']):
            cmdDict['qubeguiPath'] = 'C:/Program Files (x86)/pfx/qube/bin/qube.exe'
        cmd = r'start "QubeGUI Console" /B "%(qubeguiPath)s" %(qubeguiArgString)s'% cmdDict
    elif sys.platform == 'darwin':
        if cmdDict['qubeguiPath'] == '': cmdDict['qubeguiPath'] = '/Applications/pfx/qube/qube.app'
        cmd = r'%(qubeguiPath)s/Contents/MacOS/qube %(qubeguiArgString)s >/dev/null 2>&1  &'% cmdDict
    elif sys.platform[:5] == 'linux':
        if cmdDict['qubeguiPath'] == '': cmdDict['qubeguiPath'] = '/usr/local/pfx/qube/bin/qube'
        cmd = r'%(qubeguiPath)s %(qubeguiArgString)s >/dev/null 2>&1  &'% cmdDict
    else:
        raise "Unknown platform"
    
    # Run command
    print("COMMAND: %s"%cmd)
    nuke.tprint("COMMAND: %s"%cmd)
    #nuke.message("COMMAND: %s"%cmd)
    os.system(cmd)

    
def submitNuke_render(executeNodes=''):
    '''launch the qubegui submit dialog for nuke'''
    allNodes = nuke.allNodes()
    allNodes_Write  = [str(i.name()) for i in allNodes if i.Class() == 'Write'] 
    allNodes_Viewer = [str(i.name()) for i in allNodes if i.Class() == 'Viewer'] 
    nuke.tprint(allNodes_Write)
    nuke.tprint(allNodes_Viewer)
    range = '%s-%s' % (int(nuke.animationStart()), int(nuke.animationEnd()))
    rangeInc = int(nuke.animationIncrement())
    if rangeInc > 1:
        range += 'x%s' % rangeInc
    submitDict = {
        'name'      : 'nuke '+os.path.basename(str(nuke.root().name())),
        'prototype' : 'cmdrange',
        'package' : {
            'simpleCmdType': 'Nuke (cmdline)',
            'script': str(nuke.root().name()),
            'range' : range,
            'executeNodes' : executeNodes,
            'allNodes_Write' : ','.join(allNodes_Write),
            'allNodes_Viewer' : ','.join(allNodes_Viewer),
            }
        }
    return launchgui(submitDict=submitDict)


def submitNuke_renderAll():
    return submitNuke_render(executeNodes='')


def submitNuke_renderSelected():
    executeNodes = ','.join([i.name() for i in nuke.selectedNodes()])
    return submitNuke_render(executeNodes=executeNodes)
"""
    # Write file
    filepath = '%s/qube_menu.py'%scriptsDir
    logging.warning("Writing '%s'"%filepath)
    f = file(filepath, 'w')
    f.write(qube_addUI)
    f.close()
    
    # == Append text to ~/.nuke/menu.py ======
    textToAdd = '''
## === QUBE: BEGIN ===
qube_nukepath = os.path.expanduser('~/.nuke')
if qube_nukepath not in sys.path: sys.path.append( qube_nukepath )
import qube_menu
qube_menu.addMenuItems()
## === QUBE: END ===
'''
    #Note: Alteratively could use the following to determine the pwd of the .py file instead of explicitly setting to ~/.nuke
    #def addPwdToPythonpath():
    #    '''
    #    Add current directory (if not already there)
    #    Using indirect way to determine current directory that this code comes from,
    #    since __file__ seems to not be available from Nuke executable
    #    '''
    #    import os.path
    #    curDir = os.path.dirname(addPwdToPythonpath.func_code.co_filename)
    #    if curDir == '': curDir == '.'
    #    if not curDir in sys.path: sys.path.append( curDir )  #  ie. '/Users/<username>/.nuke'
    #addPwdToPythonpath()

    # Check for presence of menu.py
    has_qubeUI = False
    initFile = '%s/menu.py'%scriptsDir
    qube_searchToken = '## === QUBE: BEGIN ==='
    if os.path.exists(initFile):
        logging.warning( "Scanning '%s' for '%s'"%(initFile, qube_searchToken) )
        f = file(initFile, 'r')
        for line in f.readlines():
            if line == '': break
            if line.rstrip() == qube_searchToken:
                has_qubeUI = True
                break
        f.close()
    # If not have token, then append to file
    if not has_qubeUI:
        logging.warning( "Adding to '%s'"%(initFile) )
        f = file(initFile, 'a')
        f.write("\n%s\n"%textToAdd)
        f.close()
        
    # Report that completed
    logging.info( "Installed in-app interface for Nuke" )


if __name__ == '__main__':
    import wx
    import submit
    import logging
    import simplecmd
    logging.basicConfig(level=logging.DEBUG)
    app = simplecmd.TestApp(redirect=False)
    cmds = create()
    for cmd in cmds:
        simplecmd.createSubmitDialog(cmd)
    app.MainLoop()
