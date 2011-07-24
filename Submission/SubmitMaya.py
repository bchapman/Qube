## -------------------------------------------------------------------------
##   
##   Qube Submit Maya
##
##   Copyright: Pipelinefx L.L.C. 
##
## -------------------------------------------------------------------------

import sys
sys.path.append('..')

from simplecmd import SimpleSubmit, simpleSubmit_createSubmitDialog

import os
import os.path
import logging

# File-scoped variables (used for cwd workaround below)
qubegui_cwd = None

def create():        
    cmdjob = SimpleSubmit('Submit Maya', hasRange=True, canChunk=False, help='Front-end submission to Maya jobtype', category="3D", preDialog=preDialog, postDialog=postDialog,
                            postSubmit=postSubmit, controlChanged=controlChanged, install=install)

    cmdjob.add_optionGroup('Required')
    cmdjob.add_option( 'scenefile', 'file', 'Path to Maya scene (required)', label='Scene', mode='open', required=True)
    cmdjob.add_option( 'project', 'dir', 'Path to Maya project directory', label='Project', mode='open', required=True)

    # Elevate
    # Add quicker access to notes and email    
    cmdjob.add_optionGroup('General')
    cmdjob.add_option( 'notes', 'string', 'Notes about render', label='Notes',
                        required=True, lines=3, default=' ')
    cmdjob.add_option( 'email', 'string', 'Notification Email Address(s)', label='Email',
                        required=True, lines=1)

    cmdjob.add_optionGroup('Cameras/Layers/Lights')
    cmdjob.add_option( 'cameras', 'string', "List of cameras to render (space-separated)", label='Cameras', multi=True, multiDelimiter=' ') 
    cmdjob.add_option( 'layers', 'string', "List of layers to render (space-separated)", label='Layers', multi=True, multiDelimiter=' ')
    cmdjob.add_option( 'defaultRenderGlobals.enableDefaultLight', 'choice', '', label='EnableDefaultLight', choices=['', '0', '1'])
    
    cmdjob.add_optionGroup('Renderer')
    cmdjob.add_option('defaultRenderGlobals.currentRenderer' , 'string',
                      'Renderer Override', label='Renderer',
                      default='mentalRay')
    cmdjob.add_option('renderThreads', 'int', 'Number of threads that ' +
                      'each subjob should use. Set to -1 to sync with ' +
                      'host.processors, 0 to use all cores on the worker',
                      label='Render Threads', min=-1, max=16, default=-1)
    cmdjob.add_option( 'ignoreRenderTimeErrors' , 'bool', 'Ignore Render-time Errors: ignore error messages that are generated during render-time that would otherwise cause frame failure', label='Ignore Errors')
# commenting out the "batchmode" option-- batch renders should now be
# submitted from simpleCmd "Maya BatchRender"
#     cmdjob.add_option( 'batchmode', 'bool', "Set for batch mode (restart Maya with every frame and the render command)", label='Batch Mode') 
    cmdjob.add_option( 'mentalray_satellite' , 'choice', 'Note: only meaningful for layers rendered with mental ray', label='m-ray Satellite', choices=["None", "Unlimited (8 CPUs)", "Complete (2 CPUs)"], default="None")
    cmdjob.add_option( 'mayaExecutable', 'file', 'Specify path to the maya executable file (mayabatch.exe for Windows), if you want to override the auto-detected default. (optional)', label='Maya Executable', mode='open',
                        default='/usr/local/maya')

    cmdjob.add_optionGroup('Image File Output')
    cmdjob.add_option('renderDirectory', 'dir', 'Path to Maya output render directory', label='Render dir', mode='save')
    cmdjob.add_option('defaultRenderGlobals.imageFilePrefix' , 'string', 'Image file name prefix override', label='File Name Prefix')
    cmdjob.add_option('frameExt', 'choice', '', choices=['', '3', '4', '5', '6', '7'], label='Frame/Anim Ext',
                      choiceLabels={
                                    #'1': 'name',        # for single frame
                                    #'2': 'name.ext',    # for single frame
                                    '3': 'name.#.ext',
                                    '4': 'name.ext.#',
                                    '5': 'name.#',
                                    '6': 'name#.ext',
                                    '7': 'name_#.ext',
                                    #'8': 'namec',       # for multi-frame animation sequences
                                    #'9': 'namec.ext',   # for multi-frame animation sequences
                                    })
    
    # Image Formats
    outputFormats = {
        '0':'GIF',
        '1':'SI',
        '2':'RLA',
        '3':'Tiff',
        '4':'Tif16',
        '5':'SGI',
        '6':'Alias',
        '7':'IFF',
        '8':'JPEG',
        '9':'EPS',
        '10':'IFF16',
        '11':'Cineon',
        '12':'Quantel PAL',
        '13':'SGI16',
        '19':'TARGA',
        '20':'BMP',
        #'21':'SGIMV',
        #'22':'QT',
        #'23':'AVI',
        '30':'MACPAINT',
        '31':'PSD',
        '32':'PNG',
        '33':'QUICKDRAW',
        '34':'QTIMAGE',
        '35':'DDS',
        '36':'PSD Layered',
        #'50':'IMFplugin',
        #'51':'Custom',
        '60':'SWF',
        '61':'AI',
        '62':'SVG',
        '63':'SWFT',
    }
    # REVISIT: Commented out since not all image formats are usable by all renderers.
    #          Uncomment this section if that is not an issue.
    #          NOTE: The format types like OpenEXR all use custom (51).
    # sort keys numerically (if using python 2.4 or above can use sorted() to simplify)
    ##outputFormatSortedKeys = [int(i) for i in outputFormats.keys()]
    ##outputFormatSortedKeys.sort()
    ##outputFormatSortedKeys = [str(i) for i in outputFormatSortedKeys]
    ##cmdjob.add_option( 'defaultRenderGlobals.imageFormat', 'choice', 'output image format', label='Image Format', choices=['']+outputFormatSortedKeys, choiceLabels=dict([(k, '%s (%s)'%(v,k)) for k,v in outputFormats.iteritems()]))

    cmdjob.add_option( 'defaultRenderGlobals.extensionPadding' , 'string', 'Number of digits for frame number, e.g. 4 means name.XXXX.ext', label='Frame Padding', min=1, max=5)
    # NOTE: defaultRenderGlobals.modifyExtension set in postDialog callback
    #cmdjob.add_option( 'defaultRenderGlobals.modifyExtension'        , 'choice',
    #                  ('Should start and by output image filename extension modifiers be used?\n'
    #                  ' (false-> use the current frame value as the filename extension, true->use '
    #                  'startExtension + ((currentFrame-startFrame)/byFrame) * byExtension value as the filename extension).'),
    #                  choices=['', '0', '1'], label='Renumber Extension')
    cmdjob.add_option( 'defaultRenderGlobals.startExtension', 'string', 'The starting output image filename extension value.', label='Renumber StartFrame')
    cmdjob.add_option( 'defaultRenderGlobals.byExtension'   , 'string', "The output image filename extension step ('by' or increment) value. ", label='Renumber ByFrame')
    cmdjob.add_option( 'defaultRenderGlobals.outFormatExt', 'string',
                      "File extension name override. The string added at the end of the file name",
                      label='File extension') 
    # Handled in postDialog call
    #cmdjob.add_option( 'defaultRenderGlobals.animation'        , 'choice', '', choices=['', '0', '1'])
    #cmdjob.add_option( 'defaultRenderGlobals.periodInExt'      , 'choice', '', choices=['', '0', '1', '2'])
    #cmdjob.add_option( 'defaultRenderGlobals.putFrameBeforeExt', 'choice', '', choices=['', '0', '1'])
    #cmdjob.add_option( 'defaultRenderGlobals.outFormatControl', 'choice', '', choices=['', '0', '2'])

    cmdjob.add_optionGroup('Image Size')
    cmdjob.add_option( 'defaultResolution.width', 'string' , "Image width" , label='Image Width (pixels)') 
    cmdjob.add_option( 'defaultResolution.height', 'string', "Image height", label='Image Height (pixels)') 
    cmdjob.add_option( 'defaultResolution.aspectLock'      , 'choice', ''  , label='Maintain Aspect ratio', choices=['', '0', '1'])
    cmdjob.add_option( 'defaultResolution.lockDeviceAspectRatio', 'choice', '', label='Maintain ratio', choices=['', '0', '1'], choiceLabels={'0':'Pixel Aspect', '1':'Device Aspect'})
    cmdjob.add_option( 'defaultResolution.dotsPerInch'      , 'string', 'Resolution (Pixels/Inch)', label='Pixels/Inch')
    cmdjob.add_option( 'defaultResolution.deviceAspectRatio', 'string', '', label='Device Aspect Ratio')
    cmdjob.add_option( 'defaultResolution.pixelAspect'      , 'string', '', label='Pixel Aspect Ratio')
    
    # Scripts
    cmdjob.add_optionGroup('MEL Scripts')
    cmdjob.add_option( 'defaultRenderGlobals.preMel'             , 'string', 'The mel string to be executed before a scene is rendered', label='preRenderMel')
    cmdjob.add_option( 'defaultRenderGlobals.postMel'            , 'string', 'The mel string to be executed after a scene is rendered', label='postRenderMel')
    cmdjob.add_option( 'defaultRenderGlobals.preRenderLayerMel'  , 'string', 'The mel string to be executed before a render layer is rendered', label='preRenderLayerMel')
    cmdjob.add_option( 'defaultRenderGlobals.postRenderLayerMel' , 'string', 'The mel string to be executed after a render layer is rendered', label='postRenderLayerMel')
    cmdjob.add_option( 'defaultRenderGlobals.preRenderMel'       , 'string', 'The mel string to be executed before a frame is rendered', label='preRenderFrameMel')
    cmdjob.add_option( 'defaultRenderGlobals.postRenderMel'      , 'string', 'The mel string to be executed after a frame is rendered', label='postRenderFrameMel')
    # TODO: preFrame, postFrame
    
    cmdjob.properties['cpus'] = 10
    
    return [cmdjob]


# Used in preDialog and postDialog
# REFERENCE: createMayaSoftwareCommonGlobalsTab.mel
# animation, periodInExt, putFrameBeforeExt, outFormatControl (0=default, 1=none, 2=custom)
extensionParamDict = {
    #'1': (),
    #'2': (),
    '3': ('1','1','1', False),
    '4': ('1','1','0', False),
    '5': ('1','1','1', True),
    '6': ('1','0','1', False),
    '7': ('1','2','1', False),
    #'8': ('1','1','1', True),
    #'9': ('1','1','1', False),
    }
frameParamToFrameExtDict = dict([(v,k) for k,v in extensionParamDict.iteritems()])

defaultRendererList = ["", "mayaSoftware", "mayaHardware", "mayaVector",
                       "mentalRay", "turtle", "renderMan"]

def controlChanged(cmdjob, values, optionName, value, dlg, container):
    if optionName == 'scenefile':
        values['name'] = os.path.splitext(os.path.basename(value))[0]

def preDialog(cmdjob, values):
    # Set the frameExt value based on the 4 other parameters
    frameExtTuple = (
        values['package'].get('defaultRenderGlobals.animation', '1'),
        values['package'].get('defaultRenderGlobals.periodInExt', '1'),
        values['package'].get('defaultRenderGlobals.putFrameBeforeExt', '1'),
        values['package'].get('defaultRenderGlobals.outFormatControl', '0') == '1')
    frameExt = frameParamToFrameExtDict[ frameExtTuple ]
    values['frameExt'] = frameExt
    
    # Handle case where "cameras" or "layers" have the value "All Renderable".
    # Since this is a space delimited field and "All Renderable" has a space in it, then
    # it needs to be handled as a special case.  Use All_Renderable and then convert back to "All Renderable"
    values['package']['cameras'] =  values['package'].get('cameras', '').replace('All Renderable', 'All_Renderable')
    values['package']['layers'] =   values['package'].get('layers', '').replace('All Renderable', 'All_Renderable')

    # fill in layers, cameras, and renderer choice lists
    # (space-separated lists for cameras, layers, and renderers)
    cmdjob.options['cameras']['choices'] = ['All_Renderable', 'All'] + [i.strip() for i in values.get('package', {}).get('cameras_all', '').strip().split() if len(i) > 0]
    cmdjob.options['layers']['choices']  = ['All_Renderable', 'All']+[i.strip() for i in values.get('package', {}).get('layers_all', '').strip().split()  if len(i) > 0]
    rendererChoices = \
        values.get('package',{}).get('renderers_all', '').strip().split()
    if(len(rendererChoices) < 1):
        rendererChoices = defaultRendererList
    cmdjob.options['defaultRenderGlobals.currentRenderer']['choices'] = \
        rendererChoices

def postDialog(cmdjob, values):

    '''Modify the package parameters after getting values back from the dialog'''

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
    
    # Original stuff...
    
    # remove any leading or trailing whitespace 
    if values['package'].has_key('defaultRenderGlobals.outFormatExt'):
        values['package']['defaultRenderGlobals.outFormatExt'] = values['package']['defaultRenderGlobals.outFormatExt'].strip()

    if values['package'].get('frameExt', '') != '':
        (values['package']['defaultRenderGlobals.animation'],
         values['package']['defaultRenderGlobals.periodInExt'],
         values['package']['defaultRenderGlobals.putFrameBeforeExt'],
         values['package']['defaultRenderGlobals.outFormatControl']) = extensionParamDict[ values['package']['frameExt'] ]
    
    # Set the outFormatControl if a custom extension used
    if len(values['package'].get('defaultRenderGlobals.outFormatExt','')) > 0 and values['package'].get('defaultRenderGlobals.outFormatControl', False) != True:
        values['package']['defaultRenderGlobals.outFormatControl'] = 2
    #else:
    #    values['package']['defaultRenderGlobals.outFormatControl'] = 0 # ??? REVISIT: Prev set to 'None'

    # Set the modifyextension flag if the startExtension or byExtension parameters are set
    if (values['package'].get('defaultRenderGlobals.startExtension', '').strip() != '' or
        values['package'].get('defaultRenderGlobals.byExtension', '').strip() != ''):
        values['package']['defaultRenderGlobals.modifyExtension'] = '1'
    else:
        if values['package'].has_key('defaultRenderGlobals.modifyExtension'):
            del values['package']['defaultRenderGlobals.modifyExtension']

    # If "All" specified, then remove other values
    if 'All' in values['package'].get('cameras', '').split():
        values['package']['cameras'] =  'All'
    if 'All' in values['package'].get('layers', '').split():
        values['package']['layers'] =  'All'
    # Convert All_Renderable to All Renderable.
    if 'All_Renderable' in values['package'].get('cameras', '').split():
        values['package']['cameras'] =  'All Renderable'
    if 'All_Renderable' in values['package'].get('layers', '').split():
        values['package']['layers'] =  'All Renderable'
    
    
    # Set flags based on the mental ray satellite options
    flagItems = values['flagsstring'].split(',')
    flagItems = [i.strip() for i in flagItems]
    if values['package'].get('mentalray_satellite', 'None') == 'None':
        if 'grid' in flagItems: flagItems.remove('grid')
        if 'disable_cpu_limit' in flagItems: flagItems.remove('disable_cpu_limit')
    else:
        if not 'grid' in flagItems: flagItems.append('grid')
        if not 'disable_cpu_limit' in flagItems: flagItems.append('disable_cpu_limit')
    values['flagsstring'] = ','.join(flagItems)

    # WORKAROUND: Set the current working directory to the user's home directory.
    #     This addresses an issue noted with Maya 2009 on OSX when submitting jobs
    #     from the QubeGUI.  If the cwd submitted was the user's directory, then it worked.
    #     NOTE: More permenant solution to follow in the QubeGUI, likely for 5.5.
    global qubegui_cwd
    qubegui_cwd = os.getcwd()          # PUSH the cwd
    os.chdir(os.path.expanduser('~'))  # Temporarily set the cwd (value passed into qb.submit() automatically)


def postSubmit(cmd, submittedJobs):
    global qubegui_cwd
    os.chdir(qubegui_cwd)              # POP the cwd (restoring to original value)
    

def install():
    '''install the interface in Maya.  Requires QubeGUI 5.3.1 or later.'''
    
    qube_addUI = r'''
//
// Add Maya menu items for Qube rendering and launching QubeGUI
// PipelineFX
//

//
// To auto-install, put the following in userSetup.mel:
//	 qube_addUI_maya();
//
// Location of userSetup.mel:
//	  * Windows: (Users Documents Directory)\maya\<Version>\scripts
//	  * Mac OS X: ~/Library/Preferences/Autodesk/maya/<version>/scripts.
//	  * Linux: ~/maya/<version>/scripts.
//

global proc qube_removeUI_maya()
{
	// Remove MenuItems
	if (`menuItem -q -exists qube_div1`)
		deleteUI -mi qube_div1; 
	if (`menuItem -q -exists qube_submitRender`)
		deleteUI -mi qube_submitRender; 
	if (`menuItem -q -exists qube_launchQubeGUI`)
		deleteUI -mi qube_launchQubeGUI;
	if (`menuItem -q -exists qube_launchQubeGUI_OB`)
		deleteUI -mi qube_launchQubeGUI_OB;
}

global proc qube_remove_legacy_UI_maya()
{
	global string $gMainRenderMenu;

	// Make sure Render menu has been created
	eval(`menu -q -pmc $gMainRenderMenu`);

	// Remove MenuItems
	setParent -menu $gMainRenderMenu;
	if (`menuItem -q -exists qube_div1`)
		deleteUI -mi qube_div1; 
	if (`menuItem -q -exists qube_submitRender`)
		deleteUI -mi qube_submitRender; 
	if (`menuItem -q -exists qube_launchQubeGUI`)
		deleteUI -mi qube_launchQubeGUI;
	if (`menuItem -q -exists qube_launchQubeGUI_OB`)
		deleteUI -mi qube_launchQubeGUI_OB;
}

//
// qube_optionVarDlg()
//
global proc qube_optionVarDlg()
{
	// Get optionVar
	string $qube_qubeguiPath = "";
	if (`optionVar -exists "qube_qubeguiPath"`) {
		$qube_qubeguiPath = `optionVar -q "qube_qubeguiPath"`;
	}

	string $commandName = "QubeGUI";
	string $callback = ($commandName + "Callback");
	string $setup = ($commandName + "Setup");

	// Create OptionBox Dialog
	string $layout = getOptionBox();
	setParent $layout;
	setUITemplate -pushTemplate DefaultTemplate;
	tabLayout -tabsVisible 0 -scrollable 1;
	string $parent = `columnLayout -adjustableColumn 1`;
	string $macBrowseOptions = "";
	if (`about -macOS`) {
		// mac-specific flag to stop at the .app if specified
		$macBrowseOptions = " -app";
	}
	textFieldButtonGrp -label "QubeGUI Path" -fileName $qube_qubeguiPath
		-buttonLabel "Browse"
		-bc ("{string $result = `fileDialog -mode 0 " + $macBrowseOptions +
			 "`;  if ($result != \"\") textFieldButtonGrp -e -fi $result" +
			 " qube_addUI_optionVarDialog_textField; }")
		qube_addUI_optionVarDialog_textField;
	setUITemplate -popTemplate;
	// Buttons
	string $applyBtn = getOptionBoxApplyBtn();
	button -e
		-command ("optionVar -sv \"qube_qubeguiPath\"" +
				  "`textFieldButtonGrp -q -fi" +
				  " qube_addUI_optionVarDialog_textField`")
		$applyBtn;
	string $saveBtn = getOptionBoxSaveBtn();
	button -edit
		-command ("optionVar -sv \"qube_qubeguiPath\"" +
				  "`textFieldButtonGrp -q -fi" +
				  " qube_addUI_optionVarDialog_textField`; hideOptionBox")
		$saveBtn;
	string $resetBtn = getOptionBoxResetBtn();
	button -edit
		-command ("optionVar -sv \"qube_qubeguiPath\" \"\";" +
				  " textFieldButtonGrp -e -fi \"\"" +
				  " qube_addUI_optionVarDialog_textField;")
		$resetBtn;
	// Titling	  
	setOptionBoxTitle ("Qube Preferences");
	//setOptionBoxHelpTag( "Qube" );
	// Show
	showOptionBox();
}

//
// Add a top-level "Qube!" menu to the "Rendering" submenu
//
global proc string qube_add_qube_menu()
{
	// REVISIT: For some reason, the code below adds the "Qube!" menu
	// to all submenus, and not just the "Rendering" submenu. It used
	// to work properly in earlier versions of Maya...
	//
	// The following code to add Qube! menu only to the "Rendering"
	// submenu was contributed by anonymous@Animal Logic-- Mahalo!
	// <contrib>
	global string $gQubeMenu;
	if(`menu -q -exists $gQubeMenu` == 0) {
		print ("Creating top-level \"Qube!\" menu\n");
		global string $gMainWindow;
		global string $gRenderingMenus[];
		$gQubeMenu = `menu -label "Qube!" -aob true
			-to true -pmo true -parent $gMainWindow "newQubeMenu"`;
		$gRenderingMenus[size($gRenderingMenus)] = $gQubeMenu;
	}
	// </contrib>
	return $gQubeMenu;
}


//
// Get the QubeGUI path from the optionVar qube_qubeguiPath
//
global proc string qube_get_qubeguiPath()
{	
	// get the first 3 characters of the platform
	string $platform3 = python( "import sys; sys.platform[:3]" );

	// Get qubegui path from preferences
	string $qube_qubeguiPath = "";
	if (`optionVar -exists "qube_qubeguiPath"`) {
		$qube_qubeguiPath = `optionVar -q "qube_qubeguiPath"`;
	}

	switch ($platform3) {
	case "win": // Windows
		if($qube_qubeguiPath == "") {
			if(exists("C:/Program Files/pfx/qube/bin/qube.exe")) {
				$qube_qubeguiPath = "C:/Program Files/pfx/qube/bin/qube.exe";
			} else if(exists("C:/Program Files (x86)/pfx/qube/bin/qube.exe")) {
				$qube_qubeguiPath =
					"C:/Program Files (x86)/pfx/qube/bin/qube.exe";
			} else {
				$qube_qubeguiPath = "qube.exe";
			}
		}
		break;

	case "dar": // OSX
		if ($qube_qubeguiPath == "") {
			$qube_qubeguiPath = "/Applications/pfx/qube/qube.app";
		}
		break;

	case "lin": // Linux
		if ($qube_qubeguiPath == "") {
			$qube_qubeguiPath = "/usr/local/pfx/qube/bin/qube";
		}
		break;
	}
	// Verify path exists
	if (`filetest -x $qube_qubeguiPath` == 0) {
		error ("QubeGUI path not valid.  Set under Qube->Launch QubeGUI option box: "+$qube_qubeguiPath);
	}
	return $qube_qubeguiPath;
}


//
// qube_addUI_maya()
//
global proc qube_addUI_maya()
{
	// Skip adding UI if in non-interactive mode
	if (`about -batch` == 1) {
		return;
	}
	
	// Set Parameters
	// NOTE: Running python directly does not seem to work (likely
	// because of PYTHONPATH is being set by maya)
	// If Linux, add this to the command so that it launches
	string $qube_launchgui; 
	string $qube_launchgui_prefix1 = "";
	string $qube_launchgui_prefix2 = "";
	string $qube_launchgui_suffix;	 // instead of using "open"
	// get the first 3 characters of the platform
	string $platform3 = python( "import sys; sys.platform[:3]" );

	switch ($platform3) {
	case "win": // Windows
		$qube_launchgui_prefix1 = "start \\\"";
		$qube_launchgui_prefix2 = "\\\"";
		$qube_launchgui_suffix = "";
		break;

	case "dar": // OSX
		$qube_launchgui_prefix1 = "";
		$qube_launchgui_prefix2 = "/Contents/MacOS/qube";
		$qube_launchgui_suffix = " >/dev/null 2>&1 &";
		// ...instead of using "open"
		break;

	case "lin": // Linux
		$qube_launchgui_prefix1 = "";
		$qube_launchgui_prefix2 = "";
		$qube_launchgui_suffix = " >/dev/null 2>&1 &";
		break;
	}
	// Construct a string, statically filling in some fields, and
	// dynamically filling in others
	string $qube_cmdTemplate = ("system(\"" + $qube_launchgui_prefix1 +
                                            "\"+`qube_get_qubeguiPath`+\"" +
                                              $qube_launchgui_prefix2 +
								" QUBEGUI_ARGS " +
								$qube_launchgui_suffix+"\")");
    //print $qube_cmdTemplate;
	
	// Remove menuitems (if exist)
	qube_removeUI_maya();

	// Remove legacy menuitems under the "Render" menu
	qube_remove_legacy_UI_maya();
	
	// create top-level "Qube!" menu
	qube_add_qube_menu();

	// Add menuitems
	print ("Adding Qube menuitems to Qube! menu\n");
	global string $gQubeMenu;
	setParent -menu $gQubeMenu;

	string $qubegui_args = " --submitDict \\\"{'name':'maya render \"+" +
		"`file -q -sn -shn`+\"', 'prototype':'maya', 'package':{" +
		"'scenefile':'\"+`file -q -sn`+\"', " +
		"'project':'\"+`workspace -q -rd`+\"', " +
		"'range':'\"+`getAttr defaultRenderGlobals.startFrame`+\"-\"+" +
		"`getAttr defaultRenderGlobals.endFrame`+" +
	//	"\"x\"+`getAttr defaultRenderGlobals.byFrame`+" +
		"\"', " +
		"'cameras_all':'\"+stringArrayToString" +
		"(`listCameras -p -o`, \" \")+\"', " +
		"'renderers_all':'\"+stringArrayToString" +
		"(`renderer -q -ava`, \" \")+\"', " +
		"'layers_all':'\"+stringArrayToString" +
		"(`ls -type renderLayer`, \" \")+\"'}}\\\"";

	menuItem -label "Submit Render Job..."
		-c `substitute "QUBEGUI_ARGS" $qube_cmdTemplate ($qubegui_args)`
		-annotation ("Render current scene with current renderer through Qube"+
					 " using the Maya jobtype with Dynamic Frame Allocation")
		-echoCommand true
		qube_submitRender;
	// NOTE: Can use "--submitJobtype maya" if not want parameters

	menuItem -label "Launch Qube GUI..."
		-c `substitute "QUBEGUI_ARGS" $qube_cmdTemplate ""`
		-annotation "Launch the QubeGUI to monitor and manage distributed jobs"
		-echoCommand true
		qube_launchQubeGUI;
	menuItem -optionBox true -c "qube_optionVarDlg()" qube_launchQubeGUI_OB;
}
'''

    # Determine the user's maya scripts dir
    if sys.platform[:3] == 'win'    :
        import wx
        sp = wx.StandardPaths.Get()
        mayaScriptsDir = os.path.join( str(sp.GetDocumentsDir()), 'maya/scripts')
    elif sys.platform[:5] == 'linux': mayaScriptsDir = '~/maya/scripts'
    elif sys.platform  == 'darwin'  : mayaScriptsDir = '~/Library/Preferences/Autodesk/maya/scripts'
    else: raise "Unknown platform %s"%sys.platform
    mayaScriptsDir = os.path.expanduser(mayaScriptsDir)

    # Make directory if it does not exist
    if not os.path.exists(mayaScriptsDir):
        logging.info('Making directory path "%s"'%mayaScriptsDir)
        os.makedirs(mayaScriptsDir)
        
    # Write above text to <user's maya script dir>/qube_addUI_maya.mel
    filepath = '%s/qube_addUI_maya.mel'%mayaScriptsDir
    logging.warning("Writing %s"%filepath)
    f = file(filepath, 'w')
    f.write(qube_addUI)
    f.close()
    
    # Add to the userSetup.mel (if not present)
    lineToAdd = 'qube_addUI_maya();'
    # Check for presence
    has_qubeUI = False
    userSetupFile = '%s/userSetup.mel'%mayaScriptsDir
    if os.path.exists(userSetupFile):
        logging.warning( "Scanning '%s' for '%s'"%(userSetupFile, lineToAdd) )
        f = file(userSetupFile, 'r')
        for line in f.readlines():
            if line == '': break
            if line.rstrip() == lineToAdd.rstrip():
                has_qubeUI = True
                break
        f.close()
    if not has_qubeUI:
        logging.warning( "Adding to '%s' line '%s'"%(userSetupFile, lineToAdd) )
        f = file(userSetupFile, 'a')
        f.write("\n%s\n"%lineToAdd)
        f.close()
    logging.info( "Installed in-app interface for Maya jobtype" )



if __name__ == '__main__':
    import logging
    import simplecmd
    import submit
    logging.basicConfig(level=logging.DEBUG)
    app = simplecmd.TestApp(redirect=False)
    cmds = create()
    for cmd in cmds:
        simplecmd.createSubmitDialog(cmd)
    app.MainLoop()
