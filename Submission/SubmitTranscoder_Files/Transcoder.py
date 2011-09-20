'''
Transcoder Dialog for the Qube Submission Interface
'''

import wx, os, sys, gettext
from odict import OrderedDict
import logging

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

rootLogger.setLevel(logging.DEBUG)

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)


# This installs gettext as _() for translation catalogs.
gettext.install('Demo', unicode = 1)

class FormDialog(wx.Dialog):
    def __init__(self, parent, id = -1, panel = None, title = _("Unnamed Dialog"),
               modal = False, sizes = (400, -1), refid = None, settings = {}):
        wx.Dialog.__init__(self, parent, id, _(title),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.settings = settings

        if panel is not None:
            self._panel = panel(self, refid, settings=settings)

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
            self.Bind(wx.EVT_BUTTON, self._panel.onClose, id = wx.ID_CANCEL)
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
        self.onClose(evt)

    def onClose(self, evt):
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
        self.GetParent().settings = params
        self.GetParent().Hide()

class ActionForm(Form):
    def __init__(self, parent, refid = None):
        self.refid = refid

        Form.__init__(self, parent)

    def onOk(self, evt = None):
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
                print e
                try:
                    params[name] = field.GetPath()
                except AttributeError:
                    print name

                    continue

        # Something here to store in the database.

        evt.Skip()

class TransformForm(Form):
    def __init__(self, parent, refid = None):
        self.refid = refid

        Form.__init__(self, parent)

    def addByte(self, f, b):
        p, s = f.GetInsertionPoint(), f.GetSelection()

        f.Remove(*s)

        v = f.GetValue()

        f.SetValue(v[0:p] + b + v[p:])

        f.SetInsertionPoint(p + len(b))

        f.SetFocus()

    def addESC(self, f):
        self.addByte(f, r'\x1B')

    def addCR(self, f):
        self.addByte(f, r'\r')

    def addLF(self, f):
        self.addByte(f, r'\n')

    def addFF(self, f):
        self.addByte(f, r'\f')

    def addTAB(self, f):
        self.addByte(f, r'\t')

    def onOk(self, evt = None):
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
            except AttributeError:
                try:
                    params[name] = field.GetPath()
                except AttributeError:
                    print name

                    continue

        # Something here to store in the database / config file.

        evt.Skip()

class TranscoderSettings(Form):
    def __init__(self, parent, refid = None, settings={}):        
        baseDefaults = {
          'preset': '1280x720',
          'selfContained': True,
          'smartUpdate': True,
          'fillMissing': False,
          'interval': 3,
          'unit': 'Days',
          'printtasks': 5,
          'jobdrop': 'Copy Job to Queue'
        }
        
        self._form = {
        'Parts': OrderedDict([
            ('Required', [
              [({'type': 'StaticText', 'label': 'Job Name:'},
                {'type': 'TextCtrl', 'name': 'jobName', 'colGrowable': True, 'flags': wx.EXPAND | wx.ALL}),
               ({'type': 'StaticText', 'label': 'Preset'},
                {'type': 'ComboBox', 'name': 'preset', 'colGrowable': True, 'flags': wx.EXPAND | wx.ALL, 'style': wx.CB_READONLY}),
               ({'type': 'StaticText', 'label': 'Image Sequence:'},
                {'type': 'FilePickerCtrl', 'name': 'imageSequence', 'flags': wx.EXPAND | wx.ALL}),
               ({'type': 'StaticText', 'label': 'Output Movie:'},
                {'type': 'FilePickerCtrl', 'name': 'outputMovie', 'wildcard': 'Quicktime Movie (*.mov)|*.mov', 'style': wx.FLP_SAVE | wx.FLP_OVERWRITE_PROMPT | wx.FLP_USE_TEXTCTRL, 'flags': wx.EXPAND | wx.ALL}),
               ({'type': 'StaticText', 'label': 'Audio File:'},
                {'type': 'FilePickerCtrl', 'name': 'audioFile', 'wildcard': 'Wave Files (*.wav)|*.wav', 'flags': wx.EXPAND | wx.ALL })]
            ]),
            ('Advanced', [
              {'type': 'CheckBox', 'name': 'selfContained', 'label': 'Self Contained'},
              {'type': 'CheckBox', 'name': 'smartUpdate', 'label': 'Only update what\'s changed'},
              {'type': 'CheckBox', 'name': 'fillMissing', 'label': 'Fill in missing frames.'}
            ]),
        ]),
        'Options': {
          'preset': ['1280x720','1920x1080'],
          'unit': ['Hours', 'Days', 'Months'],
          'jobdrop': ['Copy Job to Queue', 'Move Job to Queue']
        },
        'Defaults': dict(baseDefaults.items() + settings.items())
        }

        Form.__init__(self, parent)

    def onOk(self, evt):
        self.onClose(evt)


if __name__ == "__main__":
    app = wx.PySimpleApp()


    transcoderDlg = FormDialog(None,
                 panel = TranscoderSettings,
                 title = 'Transcoder Settings',
                 sizes = (400, -1),
                 modal=True, settings={'imageSequence': '/tmp/test.png'})

    results = transcoderDlg.ShowModal()
    for setting in transcoderDlg.settings:
        print setting
