'''
Transcoder Classes and Tools
Author: Brennan Chapman

Can be easily imported into any other submission interface.
'''

PRESETSFOLDER = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets'

import wx, os, sys, gettext
import wx.lib.filebrowsebutton
from odict import OrderedDict
import logging
import pickle
import datetime
import re
import qb
import qbCache

sys.path.append('/Volumes/theGrill/.qube/Modules')
import sequenceTools


class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno != self.passlevel)
        else:
            return (record.levelno == self.passlevel)

'''
Set the root logging settings
'''
rootLogger = logging.getLogger()            

h1 = logging.StreamHandler(sys.stdout)
h1_formatter = logging.Formatter(
        "%(levelname)s: %(message)s")
h1.setFormatter(h1_formatter)
f1 = SingleLevelFilter(logging.INFO, False)
h1.addFilter(f1)
rootLogger.addHandler(h1)

h2 = logging.StreamHandler(sys.stderr)
h2_formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(funcName)s: %(message)s")
h2.setFormatter(h2_formatter)
f2 = SingleLevelFilter(logging.INFO, True)
h2.addFilter(f2)
rootLogger.addHandler(h2)

# rootLogger.setLevel(logging.DEBUG)

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TranscoderWidget(wx.Panel):
    '''
    Transcoder Job Widget
    Listbox with Add, Edit, and Remove Buttons
    '''
    buttonLabel='Browser'
    def __init__(self, parent, id=wx.ID_ANY, value=wx.EmptyString, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, *args, **kwargs):
        wx.Panel.__init__ (self, parent, id, pos, size, style)

        self.SetMinSize(size)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.listbox = wx.ListBox(self, -1) # size=(250, 110)
        sizer.Add( self.listbox, 1, wx.EXPAND|wx.ALL, 2)

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

        sizer.Add( btnPanel, 0, wx.RIGHT, 5)

        # Cleanup the layout
        self.SetAutoLayout(True)
        self.SetSizer( sizer )
        self.Layout()
        self.SetDimensions(-1, -1, size[0], size[1], wx.SIZE_USE_EXISTING)
        
        self.imageSequenceList = []
        self.audioFileList = []

    def setInputLists(self, imageSequenceList=[], audioFileList=[]):
        self.imageSequenceList = imageSequenceList
        self.audioFileList = audioFileList

    def loadTranscoderWindow(self, edit=False):
        if edit:
            sel = self.listbox.GetSelection()
            settings = self.listbox.GetClientData(sel)
        else:
            settings = {}
        inputs = {'imageSequences': self.imageSequenceList, 'audioFiles': self.audioFileList}
        transcoderDlg = FormDialog(self,
                     panel = TranscoderSettings,
                     title = 'Transcoder Settings',
                     sizes = (450, -1),
                     modal=True, data={'settings':settings,
                                         'inputs':inputs,
                                         'presetsFolder':PRESETSFOLDER})
        transcoderDlg.ShowModal()
        results = transcoderDlg.settings
        transcoderDlg.Destroy()
        if results:
            if edit:
                self.addItemToList(results, itemNum=sel)
            else:
                self.addItemToList(results)

    def getItemName(self, item):
        result = os.path.basename(item['outputMovie'])
        return result

    def addItemToList(self, item, itemNum=-1):
        if itemNum > -1:
            self.listbox.Delete(itemNum)
        else:
            itemNum = 0
        logging.info("Adding Item to list")
        logging.info(str(item))
        # if not item['outputPreset'].startswith(PRESETSFOLDER):
        #     item['outputPreset'] = PRESETSFOLDER + item['outputPreset'] + '.blend'
        self.listbox.Insert(self.getItemName(item), itemNum, item)
        self.listbox.SetSelection(itemNum)

    def AddButtonClick(self, event=None):
        self.loadTranscoderWindow()
        pass

    def EditButtonClick(self, event=None):
        self.loadTranscoderWindow(edit=True)
        pass

    def RemoveButtonClick(self, event=None):
        sel = self.listbox.GetSelection()
        if sel != -1:
            self.listbox.Delete(sel)

    def ClearButtonClick(self, event=None):
        self.listbox.Clear()

    def GetValue(self):
        result = []
        for index in range(self.listbox.GetCount()):
            result.append(self.listbox.GetClientData(index))
        return result
        
    def SetValue(self, items):
        for item in items:
            self.addItemToList(item)


# This installs gettext as _() for translation catalogs.
gettext.install('Demo', unicode = 1)

class FormDialog(wx.Dialog):
    def __init__(self, parent, id = -1, panel = None, title = _("Unnamed Dialog"),
               modal = False, sizes = (400, -1), refid = None, data = {}):
        wx.Dialog.__init__(self, parent, id, _(title),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if panel is not None:
            self._panel = panel(self, refid, data=data)

            self._panel.SetSizeHints(*sizes)

            ds = wx.GridBagSizer(self._panel._gap, self._panel._gap)

            ds.Add(self._panel, (0, 0), (1, 1), wx.EXPAND | wx.ALL, self._panel._gap)

            ds.Add(wx.StaticLine(self), (1, 0), (1, 1), wx.EXPAND | wx.RIGHT | wx.LEFT, self._panel._gap)

            self.bs = self.CreateButtonSizer(self._panel._form.get('Buttons', wx.OK | wx.CANCEL))

            ds.Add(self.bs, (2, 0), (1, 1), wx.ALIGN_RIGHT | wx.ALL, self._panel._gap)

            ds.AddGrowableCol(0)
            ds.AddGrowableRow(0)

            self.SetSizerAndFit(ds)

            self.Center()

            self.Bind(wx.EVT_BUTTON, self._panel.onOk, id = wx.ID_OK)
            self.Bind(wx.EVT_BUTTON, self._panel.onCancel, id = wx.ID_CANCEL)
            # self.Bind(wx.EVT_CLOSE, self._panel.onClose)

            # if modal:
            #   self.ShowModal()
            # else:
            #   self.Show()



class Form(wx.Panel):
    def __init__(self, parent = None, refid = None, id = -1, gap = 3, sizes = (-1, -1)):
        wx.Panel.__init__(self, parent, id)

        self.SetSizeHints(*sizes)

        self._gap = gap

        self.itemMap = {}

        if not hasattr(self, 'q'):
            self.q = getattr(self.GrandParent, 'q', None)

        if hasattr(self, '_form'):
            # Before building verify that several required elements exist in the form
            # definition object.
            self.loadDefaults()

            self._build()

            self._bind()

    def _build(self):
        """
        The Build Method automates sizer creation and element placement by parsing
        a properly constructed object.
        """

        # The Main Sizer for the Panel.
        panelSizer = wx.BoxSizer(wx.VERTICAL)

        # Parts is an Ordered Dictionary of regions for the form.
        for container, blocks in self._form['Parts'].iteritems():
            flags, sep, display = container.rpartition('-') #@UnusedVariable

            if 'NC' in flags:
                for block in blocks:
                    element, proportion = self._parseBlock(block)

                    panelSizer.Add(element, proportion, flag = wx.EXPAND | wx.ALL, border = self._gap)
            else:
                box = wx.StaticBox(self, -1, _(display))

                sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

                for block in blocks:
                    element, proportion = self._parseBlock(block)

                    sizer.Add(element, proportion, flag = wx.EXPAND | wx.ALL)

                if 'G' in flags:
                    sizerProportion = 1
                else:
                    sizerProportion = 0

                panelSizer.Add(sizer, sizerProportion, flag = wx.EXPAND | wx.ALL, border = self._gap)

        self.SetSizerAndFit(panelSizer)

    def _bind(self): pass

    def _parseBlock(self, block):
        """
          The form structure is a list of rows (blocks) in the form.  Each row
          consists of a single element, a row of elements, or a sub-grid of
          elements.  These are represented by dictionaries, tuples, or lists,
          respectively and are each processed differently.
        """
        proportion = 0

        if isinstance(block, list):
            item = self.makeGrid(block)

        elif isinstance(block, tuple):
            item = self.makeRow(block)

        elif isinstance(block, dict):
            proportion = block.pop('proportion', 0)

            item = self.makeElement(block)

        return item, proportion

    def makeElement(self, object):
        """
          In the form structure a dictionary signifies a single element.  A single
          element is automatically assumed to expand to fill available horizontal
          space in the form.
        """
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        flags = object.pop('flags', wx.ALL)

        element = self._makeWidget(object)

        sizer.Add(element, 1, border = self._gap,
                  flag = wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | flags)

        return sizer

    def makeRow(self, fields):
        """
          In the form structure a tuple signifies a row of elements.  These items
          will be arranged horizontally without dependency on other rows.  Each
          item may provide a proportion property which can cause that element to
          expand horizontally to fill space.
        """
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        for field in fields:
            proportion = field.pop('proportion', 0)

            sizer.Add(self.makeElement(field), proportion,
                      flag = wx.ALIGN_CENTER_VERTICAL | wx.ALL)

        return sizer

    def makeGrid(self, rows):
        """
          In the form structure a list signifies a grid of elements (equal width
          columns, rows with similar numbers of elements, etc).
        """

        sizer = wx.GridBagSizer(0, 0)

        for row, fields in enumerate(rows):
            for col, field in enumerate(fields):
                flags = field.pop('flags', wx.ALL)

                # Each item may specify that its row or column 'grow' or expand to fill
                # the available space in the form.
                rowGrowable, colGrowable = (field.pop('rowGrowable', False),
                                            field.pop('colGrowable', False))

                if rowGrowable:
                    sizer.AddGrowableRow(row)

                if colGrowable:
                    sizer.AddGrowableCol(col)

                span = field.pop('span', (1, 1))

                colpos = field.pop('colpos', col)

                rowpos = field.pop('rowpos', row)

                element = self._makeWidget(field)

                sizer.Add(element, (rowpos, colpos), span, border = self._gap,
                          flag = wx.ALIGN_CENTER_VERTICAL | flags)

        return sizer

    def _makeWidget(self, params):
        """
          This function actually creates the widgets that make up the form. In most
          cases these will be items from the wx libraries, though they may be
          'custom' elements which require delayed instantiation by leveraging
          lambdas.
        """

        type = params.pop('type')

        if type == 'Custom':
            lookup = params.pop('lookup')

            element = self._form[lookup](self)

            self.itemMap[lookup] = element
        else:
            # StaticText items may carry a bold attribute - retrieve it for use later.
            if type == 'StaticText':
                bold = params.pop('bold', False)

            # ComboBoxes need to have choices.
            if type == 'ComboBox':
                params['choices'] = self._form['Options'].get(params['name'], [])

            if "." in type:
                element = eval(type)(self, -1, **params)
            else:
                element = getattr(wx, type)(self, -1, **params)

            if type == 'ComboTreeBox':
                choices = self._form['Options'].get(params['name'], [])

                for category, options in choices:
                    id = element.Append(category)

                    for option in options:
                        element.Append(option, parent = id)

                    element.GetTree().Expand(id)

            # Require the user to use the browse buttons for File / Folder browsing.
            # if type in ('DirPickerCtrl', 'FilePickerCtrl'):
            #   element.GetTextCtrl().SetEditable(False)

            if params.has_key('name'):
                # Populate the itemMap - facilitates element retrieval / event bindings.
                self.itemMap[params['name']] = element

                # Default value assignment.  Must unfortunately do a dance to check
                # element type - some require ints / floats, while others are ok with
                # strings.  There is also a check against the Translations member -
                # this facilitates the Human Readable <-> Database Value conversion.
                value = self._form['Defaults'].get(params['name'], '')

                if self._form.has_key('Translations'):
                    if self._form['Translations'].has_key(params['name']):
                        value = self._form['Translations'][params['name']][0].get(value, value)

                if hasattr(element, 'SetValue'):
                    if type == 'SpinCtrl':
                        if value == '':
                            value = 0
                        element.SetValue(int(value))
                    elif type in ('CheckBox', 'RadioButton'):
                        element.SetValue(bool(value))
                    else:
                        element.SetValue(unicode(value))
                elif hasattr(element, 'SetPath'):
                    element.SetPath(value)
                elif type != 'Button':
                    print element

                # Check for elements we should disable at load time.
                if params['name'] in self._form['Disabled']:
                    element.Enable(False)

                # Check for a Validator and add it if required.
                try:
                    validator = self._form['Validators'][params['name']]()

                    element.SetValidator(validator)
                except KeyError: pass # No Validator Specified.

            # Take the bold attribute into account for StaticText elements.
            if type == 'StaticText' and bold:
                font = element.GetFont()

                font.SetWeight(wx.BOLD)

                element.SetFont(font)

        return element

    def loadDefaults(self):
        if not self._form.has_key('Defaults'): self._form['Defaults'] = {}

        if not self._form.has_key('Disabled'): self._form['Disabled'] = []

        if not self._form.has_key('Validators'): self._form['Validators'] = {}

        self.loadOptions()

    def loadOptions(self):
        if not self._form.has_key('Options'):
            self._form['Options'] = {}

    def onOk(self, evt):
        self.GetParent().settings = self.getOptions()
        self.onClose(evt)

    def getOptions(self):
        params = {}

        for name, field in self.itemMap.iteritems():
            try:
                value = field.GetValue()

                if self._form.has_key('Translations'):
                    if self._form['Translations'].has_key(name):
                        value = self._form['Translations'][name][1].get(value, value)

                if hasattr(value, 'isdecimal'):
                    try:
                        f = float(value)

                        i = int(f)

                        if i == f:
                            value = i
                        else:
                            value = f
                    except ValueError:
                        pass # No conversion to int / float - string value.

                params[name] = value
            except AttributeError, e:
                logger.debug(e)
                try:
                    params[name] = field.GetPath()
                except AttributeError:
                    print name

                    continue

        return params

    def onCancel(self, evt):
        self.GetParent().settings = None
        self.onClose(evt)

    def onClose(self, evt):
        self.GetParent().Hide()

class TranscoderSettings(Form):
    def __init__(self, parent, refid = None, data={}):
        
        self.initComplete = False
        settings = data.get('settings', {})
        inputs = data.get('inputs', {})
        presetsFolder = data.get('presetsFolder', None)

        self.recentSettings = []
        self.outputPresets = ['Choose an output preset...']
        self.loadPresets(presetsFolder)

        baseDefaults = {
          'outputPreset': self.outputPresets[0],
          'selfContained': True,
          'smartUpdate': True,
          'fillMissing': False,
          'interval': 3,
          'unit': 'Days',
          'printtasks': 5,
          'jobdrop': 'Copy Job to Queue',
          'recentSettings':'None'
        }
        
        self._form = {
        'Parts': OrderedDict([
            ('General', [
              [({'type': 'StaticText', 'label': 'Image Sequence', 'name':'imageSequenceLabel'},
                {'type': 'wx.lib.filebrowsebutton.FileBrowseButtonWithHistory', 'name': 'imageSequence', 'labelText':'', 'flags': wx.EXPAND | wx.ALL, 'changeCallback': self.onSequenceUpdate}),
               ({'type': 'StaticText', 'label': 'Recent Settings'},
                {'type': 'ComboBox', 'name': 'recentSettings', 'colGrowable': True, 'flags': wx.EXPAND | wx.ALL, 'style': wx.CB_READONLY}),
               ({'type': 'StaticText', 'label': 'Frame Range', 'name':'frameRangeLabel'},
                {'type': 'TextCtrl', 'name': 'frameRange', 'flags': wx.EXPAND | wx.ALL}),
               ({'type': 'StaticText', 'label': 'Audio File'},
                {'type': 'wx.lib.filebrowsebutton.FileBrowseButtonWithHistory', 'name': 'audioFile', 'labelText':'', 'fileMask': 'Wave Files (*.wav)|*.wav', 'flags': wx.EXPAND | wx.ALL}),
               ({'type': 'StaticText', 'label': 'Output Preset', 'name':'outputPresetLabel'},
                {'type': 'ComboBox', 'name': 'outputPreset', 'colGrowable': True, 'flags': wx.EXPAND | wx.ALL, 'style': wx.CB_READONLY}),
               ({'type': 'StaticText', 'label': 'Output Movie', 'name':'outputMovieLabel'},
                {'type': 'FilePickerCtrl', 'name': 'outputMovie', 'wildcard': 'Quicktime Movie (*.mov)|*.mov', 'style': wx.FLP_SAVE | wx.FLP_OVERWRITE_PROMPT | wx.FLP_USE_TEXTCTRL, 'flags': wx.EXPAND | wx.ALL})]
            ]),
            ('Advanced', [
              {'type': 'CheckBox', 'name': 'selfContained', 'label': 'Self-contained'},
              {'type': 'CheckBox', 'name': 'smartUpdate', 'label': 'Only update what\'s changed'},
              {'type': 'CheckBox', 'name': 'fillMissingFrames', 'label': 'Fill in missing frames.'}
            ]),
        ]),
        'Options': {
          'outputPreset': self.outputPresets,
          'unit': ['Hours', 'Days', 'Months'],
          'jobdrop': ['Copy Job to Queue', 'Move Job to Queue'],
          'recentSettings': ['None']
        },
        'Defaults': dict(baseDefaults.items() + settings.items())
        }

        Form.__init__(self, parent)
        
        if settings.has_key('imageSequence'):
            self.loadRecentSettings(settings['imageSequence'])
            self.applyRecentSetting()
                
        self.loadInputs(inputs)
        
        self.initComplete = True
        
    def applyRecentSetting(self, select=-1):
        if len(self.recentSettings) > 0 and select > -1:
            data = self.recentSettings[select]
            self.itemMap['recentSettings'].SetValue(self.getSettingName(data))
            self.itemMap['frameRange'].SetValue(data['frameRange'])
            self.itemMap['audioFile'].SetValue(data['audioFile'])
            logger.debug("Apply output preset: " + data['outputPreset'])
            self.itemMap['outputPreset'].SetValue(data['outputPreset'])
            self.itemMap['outputMovie'].SetPath(data['outputMovie'])
            self.itemMap['selfContained'].SetValue(data['selfContained'])
            self.itemMap['smartUpdate'].SetValue(data['smartUpdate'])
            self.itemMap['fillMissing'].SetValue(data['fillMissing'])

        # Put together the list of recent settings
        recSetCtrl = self.itemMap['recentSettings']
        recSetCtrl.Clear()
        recSetCtrl.Append("Choose a recent setting...")
        for setting in self.recentSettings:
            settingName = self.getSettingName(setting)
            recSetCtrl.Append(settingName)

        recSetCtrl.SetSelection(select+1)

        
    def _bind(self):
        self.Bind(wx.EVT_COMBOBOX, self.onRecentSettings, self.itemMap['recentSettings'])
        self.itemMap['imageSequence'].browseButton.Bind(wx.EVT_BUTTON, self.onSequenceBrowse)

    def compareSettings(self, settingA, settingB):
        logger.debug("SettingA: " + str(settingA))
        logger.debug("SettingB: " + str(settingB))
        result = True
        for item in settingA.items():
            logger.debug("Item: " + str(item))
            if item[0] not in ('date','recentSettings'):
                logger.debug("Not in date, recentSettings")
                if item[1] != settingB.get(item[0], ''):
                    logger.debug(str(item[1]) + ' != ' + str(settingB.get(item[0], '')))
                    result = False
        return result

    def getSettingName(self, setting):
        result = setting['date'] + ' ' + os.path.basename(setting['outputMovie'])
        return result

    def getRecentSettingsFilePath(self, imageSequenceFile):
        '''
        Return the file path of the recent settings file stored
        in the image sequence directory.
        '''

        imgSeqFile = os.path.split(imageSequenceFile)
        recSetFilePath = imgSeqFile[0]
        match = re.match('(.+?)(\d\d+?)(\.\w+)', imgSeqFile[1])
        recSetFilePath += '/.TRANSCODE.'
        if match:
            name, number, ext = match.groups()
            recSetFilePath += name + ('0'*len(number)) + ext
        else:
            recSetFilePath += imgSeqFile[1]

        logger.debug("recentSettingsFilePath: " + recSetFilePath)
        return recSetFilePath

    def loadInputs(self, inputs):
        if inputs:
            imageSequences = inputs.get('imageS equences', [])
            self.itemMap['imageSequence'].SetHistory(imageSequences)

            audioFiles = inputs.get('audioFiles', [])
            self.itemMap['audioFile'].SetHistory(audioFiles)            
        else:
            logger.debug("No inputs provided.")

    def loadPresets(self, presetsFolder):
        try:
            fileList = os.listdir(presetsFolder)
            # self.itemMap['outputPreset'].Clear()
            for item in fileList:
                if item.endswith('.blend'):
                    self.outputPresets.append(os.path.splitext(item)[0])
                    # self.itemMap['outputPreset'].Append()

            # self.itemMap['outputPreset'].SetSelection(0)
        except:
            logger.error("Unable to load presets from the presets folder. " + str(presetsFolder))

    def loadRecentSettings(self, imageSequencePath):
        '''
        Load recent settings from a data file
        in the image sequence folder if it exists.
        '''

        recSettings = []

        recSetFilePath = self.getRecentSettingsFilePath(imageSequencePath)

        logger.debug("recSetFilePath: " + recSetFilePath)
        if os.path.exists(recSetFilePath):
            recSetFile = open(recSetFilePath, 'r')
            recSettings = pickle.load(recSetFile)
            logger.debug("Loaded Settings: " + str(recSettings))

            recSetFile.close()

        logger.debug("Loaded Settings: " + str(recSettings))

        self.recentSettings = recSettings

    def onOk(self, evt):
        if self.validateForm():
            self.saveSettings()
            super(TranscoderSettings, self).onOk(evt)

    def onRecentSettings(self, evt=None):
        selection = self.itemMap['recentSettings'].GetSelection() - 1
        self.applyRecentSetting(selection)

    def onSequenceBrowse(self, evt=None):
        self.itemMap['imageSequence'].OnBrowse()
        self.onSequenceUpdate()

    def onSequenceUpdate(self, evt=None):
        if self.initComplete:
            self.loadRecentSettings(self.itemMap['imageSequence'].GetValue())
            if len(self.recentSettings) > 0:
                self.applyRecentSetting()

    def saveSettings(self):
        '''
        Save the current settings to a preset file
        in the image sequence folder. Limited to 10 entries.
        '''
        
        options = self.getOptions()
        unique = True
        if options['outputMovie']:
            for setting in self.recentSettings:
                if type(setting) == dict:
                    if self.compareSettings(options, setting):
                        unique = False

        if unique:
            logger.debug("New Setting")
            now = datetime.datetime.now()
            options['date'] = now.strftime("%b%d %H:%M")
            self.recentSettings.insert(0, options)
            self.recentSettings = self.recentSettings[:10] # Limit to 10 entries
            logger.debug("recentSettings: " + str(options))
        else:
            logger.debug("Setting used before")

        recSetFilePath = self.getRecentSettingsFilePath(self.itemMap['imageSequence'].GetValue())
        recSetFile = open(recSetFilePath, 'w')
        pickle.dump(self.recentSettings, recSetFile)
        recSetFile.close()

    def validateForm(self):
        result = True
        if not self.itemMap['frameRange'].GetValue():
            self.itemMap['frameRangeLabel'].SetForegroundColour(wx.RED)
            result = False
        else:
            self.itemMap['frameRangeLabel'].SetForegroundColour(wx.BLACK)
        try:
            startFrame, endFrame = self.itemMap['frameRange'].GetValue().split('-')
            if not startFrame.isdigit() or not endFrame.isdigit():
                self.itemMap['frameRangeLabel'].SetForegroundColour(wx.RED)
                result = False
            else:
                self.itemMap['frameRangeLabel'].SetForegroundColour(wx.BLACK)
        except:
            self.itemMap['frameRangeLabel'].SetForegroundColour(wx.RED)
            result = False
            
        if not self.itemMap['imageSequence'].GetValue():
            self.itemMap['imageSequenceLabel'].SetForegroundColour(wx.RED)
            result = False
        else:
            self.itemMap['imageSequenceLabel'].SetForegroundColour(wx.BLACK)
        if self.itemMap['outputPreset'].GetValue() == 'None':
            self.itemMap['outputPresetLabel'].SetForegroundColour(wx.RED)
            result = False
        else:
            self.itemMap['outputPresetLabel'].SetForegroundColour(wx.BLACK)
        if not self.itemMap['outputMovie'].GetPath():
            self.itemMap['outputMovieLabel'].SetForegroundColour(wx.RED)
            result = False
        else:
            self.itemMap['outputMovieLabel'].SetForegroundColour(wx.BLACK)
        
        return result

def chunkWithTolerance(inputList, chunkSize, tolerance):
    '''
    Generate chunks of a list. If the tolerance
    value isn't met, the remaining values are
    added to the last chunk.
    '''

    myList = list(inputList) # Make a copy

    logger.debug('Chunk With Tolerance: ' + str(locals()))
    if tolerance > chunkSize:
        tolerance = 0

    resultLists = []
    while len(myList) > 0:
        resultList = []
        count = 0
        while count < chunkSize and len(myList) > 0:
            resultList.append(myList.pop(0))
            count += 1

        if len(resultList) <= tolerance:
            resultLists[-1].extend(resultList)
        else:
            resultLists.append(resultList)

    logger.debug('Chunk with Tolerance Results: ' + str(resultLists))
    logger.debug('Chunk with Tolerance Results Length: ' + str(len(resultLists)))
    return resultLists

def splitPath(inputPath):
    '''
    Split an input path into:
        Folder
        File Name
        File Extension
    '''
    # logger.debug('Splitting Path: ' + str(locals()))
    folder, fullName = os.path.split(inputPath)
    name, extension = os.path.splitext(fullName)

    return folder + '/', name, extension

def setupSequenceJob(qubeJobTemplate, sequenceInitFile, outputFile, preset,
                        selfContained=True, frameRange='ALL', audioFile='',
                        smartUpdate=True, fillMissingFrames=True, transcoderFolder='',
                        segmentDuration=200, maxSegmentsPerOutput=-1, maxSegmentTolerance=5):
    '''
    Setup a qube job dictionary based on the input.
    Required Inputs:
        qubeJobTemplate (dictionary)
            Template qube job dictionary to build from.
        sequenceInitFile (string)
            One image from the input image sequence.
            Can be any image from the sequence.
        outputFile (string)
            The destination file for the output
            of the transcoder.
        preset (string)
            The blender file that serves as the template
            for the transcoding process.
    Optional:
        selfContained (boolean)
            Determines if the outputFile should be a
            reference quicktime movie or self-contained.
            Self-contained movies are much larger and take
            more time to create.  Referenced quicktimes
            are much smaller, and much faster to create.
            However, referenced quicktimes must maintain
            their connectiong their associated inputs.
        frameRange (string)
            The output frame range to render from the input
            image sequence. Ex: 1-10
        audioFile (string)
            The audio file to be added to the output file.
            This audio should match the exact timeline of
            the input image sequence.
        smartUpdate (boolean)
            Automatically update only the segments and outputs
            that have been changed since the last transcode.
        transcoderFolder (string)
            The folder in which to store all files related
            to the transcoding process.  This includes the
            segmented movies and the blender projects. If
            creating a referenced output file, these are
            the segments that movie will reference.
        fillMissingFrames (boolean)
            Automatically fill in missing frames with the
            last frame that exists.  This is useful for
            creating quicktimes from sequences rendered on
            every nth frame.
    Advanced:
        segmentDuration (integer)
            Frame count for each segment.
        maxSegmentsPerOutput (integer)
            Maximum number of segments that can be in each
            output file.  If the number of segments needed
            for the sequence exceeds this amount, the output
            file is split into multiple segments of this
            length.
        maxSegmentTolerance (integer)
            If the maxSegmentsPerOutput limit is reached,
            check that the input sequence exceeds this tolerance
            value as well. If not, keep the outputFile as one file.

    Agenda
        The agenda is setup in 3 main sections:
            Initialization:
                Purpose
                    This single subjobs loads the input sequence
                    into the provided blender scene preset.
                    This is done once, then all subsequent
                    jobs reference the resulting scene file.
                Package
                    None
                resultPackage
                    None
                Naming
                    Initialize
            Segments:
                Purpose
                    These subjobs each create their assigned
                    segment of the image sequence.
                Package
                    frameRange (string)
                        Range of frames to render for this segment.
                    segmentFile (string)
                        Destination path for the segment file.
                resultPackage
                    changes (boolean)
                        Returns if any changes were made for
                        this segment.
                    segmentFile (string)
                        Destination path for the segment file
                        that actually rendered.  Sometimes file
                        issues occur where the output file can't
                        be overwritten, so we automatically
                        compensate for this.
                Naming
                    Segment: (frameRange)
            Final Outputs:
                Purpose
                    These subjobs render the output files.
                    They are split up based on the number of segments
                    and the max segments per output.  They are placed
                    in the agenda right after their dependent segments
                    have been processed.
                Package
                    segmentSubjobs (list of strings)
                        List of the names of the dependant
                        segment subjobs.
                    outputFile (string)
                        destination for the output
                resultPackage
                    outputPaths (string)
                        Path to the final output file.
                Naming
                    Output: (outputFile)

    Callbacks
        Callbacks are added to unblock subjobs when they are
        ready to be processed.
            Initialization subjob completion
                Once the initialization is complete, all
                segment subjobs are unblocked.
            Segment subjobs complete.
                Once all segments that pertain to a final
                output are complete, that output subjob
                is unblocked.
            Job retried
                If the job is retried





    '''

    ''' Verify input types '''
    sequenceInitFile = str(sequenceInitFile)
    outputFile = str(outputFile)
    preset = str(preset)
    frameRange = str(frameRange)
    audioFile = str(audioFile)
    transcoderFolder = str(transcoderFolder)

    ''' ---- Pre-Processing For Agenda ---- '''

    logger.debug('Setup Sequence: ' + str(locals()))

    ''' General '''
    mySequence = sequenceTools.Sequence(sequenceInitFile, frameRange)
    if not transcoderFolder:
        transcoderFolder = os.path.join(os.path.dirname(outputFile), '_Transcoder/')

    ''' Initialize '''
    init = qb.Work()
    init['name'] = 'Initialize'


    ''' Segments

    Use the qube chunk method to split up the frame range.
    Then prep each segment:
        Add the frameRange to the package.
        Add the segmentFile to the package.
        Change the subjob name to Segment: (frameRange)
        Submit as blocked, because they will be unblocked
            once the initialize command is completed.
    '''
    segments = qb.genchunks(segmentDuration, '1-' + str(mySequence.getDuration()))
    for segment in segments:
        segment['package']= {}
        segment['package']['frameRange'] = segment['name']

        outputFolder, outputName, outputExtension = splitPath(outputFile)
        segmentFile = os.path.join(transcoderFolder, 'Segments/')
        segmentFile += outputName + '/'
        segmentFile += "Segment" + segment['name'].split('-')[0] + outputExtension
        segment['package']['segmentFile'] = segmentFile

        segment['status'] = 'blocked'
        segment['name'] = 'Segment:' + segment['name']
    logger.debug("Segments: " + str(segments))


    ''' Final Outputs '''
    if not selfContained:
        maxSegmentsPerOutput = -1
    
    if maxSegmentsPerOutput == -1:
        finalOutputSegments = [list(segments)]
    else:
        finalOutputSegments = chunkWithTolerance(segments, maxSegmentsPerOutput, maxSegmentTolerance)

    finalOutputs = []
    count = 1
    for outputSegment in finalOutputSegments:
        output = qb.Work()
        output['package'] = {}

        segmentSubjobs = []
        for segment in outputSegment:
            segmentSubjobs.append(segment['name'])
        output['package']['segmentSubjobs'] = segmentSubjobs

        outputFolder, outputName, outputExtension = splitPath(outputFile)
        finalOutputFile = outputFolder + outputName
        if len(finalOutputSegments) > 1:
            finalOutputFile += '_' + chr(64+count)
        finalOutputFile += outputExtension
        output['package']['outputFile'] = finalOutputFile

        output['status'] = 'blocked'
        output['name'] = 'Output:' + os.path.basename(finalOutputFile)

        count += 1

        finalOutputs.append(output)
    logger.debug("Final Outputs: " + str(finalOutputs))

    '''
    Callbacks
        1 - Unblock the segments when the initialize command is completed.
        2 - Unblock the outputs when the dependant segments are completed.
    '''

    callbacks = []

    ''' Unblock Segments '''
    callback = {}
    callback['triggers'] = 'complete-work-self-Initialize'
    callback['language'] = 'python'

    code = 'import qb\n'
    for segment in segments:
        code += '%s%s%s' % ('\nqb.workunblock(\'%s:', segment['name'], '\' % qb.jobid())')
    code += '\nqb.unblock(qb.jobid())'
    callback['code'] = code

    callbacks.append(callback)

    ''' Unblock Outputs '''
    for finalOutput in finalOutputs:
        callback = {}
        triggers = []

        for segment in finalOutput['package']['segmentSubjobs']:
            triggers.append('complete-work-self-' + segment)
        callback['triggers'] = ' and '.join(triggers)
        callback['language'] = 'python'

        code = 'import qb\n'
        code += '%s%s%s' % ('\nqb.workunblock(\'%s:', finalOutput['name'], '\' % qb.jobid())')
        code += '\nqb.unblock(qb.jobid())'
        callback['code'] = code

        callbacks.append(callback)


    ''' ---- Now put the job together ---- '''

    job = qubeJobTemplate.copy()

    ''' General '''
    job['name'] = 'Quicktime: ' + os.path.basename(outputFile)
    job['prototype'] = 'Submit Transcoder'

    ''' Package '''
    job['package'] = {}
    job['package']['sequence'] = sequenceInitFile
    job['package']['audioFile'] = audioFile
    job['package']['outputFile'] = outputFile
    job['package']['preset'] = os.path.join(PRESETSFOLDER,preset + ".blend")
    job['package']['selfContained'] = selfContained
    job['package']['smartUpdate'] = smartUpdate
    job['package']['fillMissingFrames'] = fillMissingFrames
    job['package']['frameRange'] = '1-' + str(mySequence.getDuration())
    job['package']['transcoderFolder'] = transcoderFolder

    ''' Agenda '''
    job['agenda'] = []
    job['agenda'].append(init)
    job['agenda'].extend(segments)
    logger.debug("Agenda: " + str(job['agenda']))

    ''' Place the final outputs after their last segment. '''
    for outputNum, output in enumerate(finalOutputs):
        lastSegmentName = output['package']['segmentSubjobs'][-1]
        lastSegmentIndex = None
        for index, segment in enumerate(segments):
            if segment['name'] == lastSegmentName:
                lastSegmentIndex = index
                break
        if lastSegmentIndex != None:
            job['agenda'].insert(lastSegmentIndex+2+outputNum, output) # +2 for Initialization and last segment
        else:
            logger.error("ERROR: Unable to find last segment for output " + output['name'])

    ''' Callbacks '''
    if not job.get('callbacks', None):
        job['callbacks'] = []
    job['callbacks'].extend(callbacks)

    return job

def prepareJobsFromDlg(qubejob):

    tJobs = qubejob.get('package', {}).get('transcodeJobs', [])

    jobsToSubmit = []
    for tJob in tJobs:    
        logger.info("job from array: " + str(tJob))
        sequenceFile = tJob['imageSequence']
        logger.info("imageSequence: " + str(sequenceFile))
        frameRange = tJob['frameRange']
        logger.info("frameRange: " + str(frameRange))
        outputFile = tJob['outputMovie']
        logger.info("outputMovie: " + str(outputFile))
        preset = tJob['outputPreset']
        logger.info("preset: " + str(preset))
        audioFile = tJob['audioFile']
        selfContained = tJob['selfContained']
        logger.info("selfContained: " + str(preset))
        smartUpdate = tJob['smartUpdate']
        logger.info("smartUpdate: " + str(smartUpdate))
        smartUpdate = tJob['smartUpdate']
        logger.info("smartUpdate: " + str(smartUpdate))
        fillMissingFrames = tJob['fillMissingFrames']
        logger.info("fillMissingFrames: " + str(fillMissingFrames))
        transcodeJob = setupSequenceJob(qubejob, sequenceFile, outputFile, preset, audioFile=audioFile, maxSegmentsPerOutput=5, frameRange=frameRange,
            fillMissingFrames=fillMissingFrames, maxSegmentTolerance=2, segmentDuration=100, selfContained=selfContained, smartUpdate=smartUpdate)
        logger.info("Setup Sequence Job: " + str(transcodeJob))
        jobsToSubmit.append(transcodeJob)

    submittedJobs = qb.submit(jobsToSubmit)

    request = qbCache.QbServerRequest(action="jobinfo", value=[i['id'] for i in submittedJobs], method='reload')
    qbCache.QbServerRequestQueue.put(request)

def addTranscodeWidgetToDlg(cmdjob):
    cmdjob.add_option( 'transcodeJobs', 'choice', label='Conversions', required=True,
                        editable=True, widget=TranscoderWidget)

if __name__ == "__main__":
    app = wx.PySimpleApp()

    settings = {'imageSequence': ''}
    inputs = {'audioFiles':['test1.wav','test2.wav'], 'imageSequences':['sequence1.png','sequence2.png']}
    presetsFolder = '/tmp/testPresets'
    
    transcoderDlg = FormDialog(None,
                 panel = TranscoderSettings,
                 title = 'Transcoder Settings',
                 sizes = (400, -1),
                 modal=True, data={'settings':settings,
                                    'inputs':inputs,
                                    'presetsFolder':presetsFolder})

    print transcoderDlg.ShowModal()
    print transcoderDlg.settings
