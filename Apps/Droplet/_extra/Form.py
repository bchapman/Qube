import os
import wx
import wx.lib.filebrowsebutton
 
class XMLWindow(wx.Dialog):
 
    def __init__(self, title='XML 2 Keys', data={}):
        wx.Dialog.__init__(self, None, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
 
        # Add a panel so it looks correct on all platforms
        self.panel = wx.Panel(self, wx.ID_ANY)
 
        # bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))
        # titleIco = wx.StaticBitmap(self.panel, wx.ID_ANY, bmp)
        title = wx.StaticText(self.panel, wx.ID_ANY, title)

        loadBtn = wx.Button(self.panel, wx.ID_ANY, 'Load XML', size=(195, -1))
        clearBtn = wx.Button(self.panel, wx.ID_ANY, 'Clear List', size=(195, -1))
        self.Bind(wx.EVT_BUTTON, self.onLoad, loadBtn)
        self.Bind(wx.EVT_BUTTON, self.onClear, clearBtn)

        self.listBox = wx.ListBox(self.panel, -1, style=wx.LB_MULTIPLE, size=(400, 250))
        self.listBox.Insert("Test", 0, "Test2")
        self.listBox.Insert("Test", 0, "Test2")
        self.listBox.Insert("Test", 0, "Test2")
        self.listBox.Insert("Test", 0, "Test2")
        self.listBox.Select(0)
        self.listBox.Select(1)

        # Setup Panel
        self.setupTemplateFile = wx.lib.filebrowsebutton.FileBrowseButton(self.panel, wx.ID_ANY)
        self.setupTemplateFile.SetLabel("Template File")
        self.setupProjectFolder = wx.lib.filebrowsebutton.DirBrowseButton(self.panel, wx.ID_ANY)
        self.setupProjectFolder.SetLabel("Nuke Projects Folder")
        setupBtn = wx.Button(self.panel, wx.ID_ANY, 'Setup Projects', size=(300, -1))
        self.Bind(wx.EVT_BUTTON, self.onSetup, setupBtn)
        
        # Qube Panel
        qubePaddingLbl = wx.StaticText(self.panel, wx.ID_ANY, 'Padding')
        self.qubePaddingTxt = wx.TextCtrl(self.panel, wx.ID_ANY, '30')
        qubeSubmitBtn = wx.Button(self.panel, wx.ID_ANY, 'Submit to Qube', size=(300, -1))
        self.Bind(wx.EVT_BUTTON, self.onQubeSubmit, qubeSubmitBtn)

        closeBtn = wx.Button(self.panel, wx.ID_ANY, 'Close')
        self.Bind(wx.EVT_BUTTON, self.onClose, closeBtn)
 
        topSizer        = wx.BoxSizer(wx.VERTICAL)
        titleSizer      = wx.BoxSizer(wx.HORIZONTAL)
        listCtrlSizer   = wx.BoxSizer(wx.HORIZONTAL)
        listBoxSizer    = wx.BoxSizer(wx.HORIZONTAL)
        qubePadSizer    = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer        = wx.BoxSizer(wx.HORIZONTAL)
 
        titleSizer.Add(title, 0, wx.ALL, 5)
        
        listCtrlSizer.Add(loadBtn, 0, wx.ALL, 5)
        listCtrlSizer.Add(clearBtn, 0, wx.ALL|wx.EXPAND, 5)
 
        listBoxSizer.Add(self.listBox, 0, wx.ALL|wx.EXPAND, 5)
        
        qubePadSizer.Add(qubePaddingLbl, 0, wx.ALL, 5)
        qubePadSizer.Add(self.qubePaddingTxt, 0, wx.ALL|wx.EXPAND, 5)
 
        btnSizer.Add(closeBtn, 0, wx.ALL, 5)
 
        topSizer.Add(titleSizer, 0, wx.CENTER)
        topSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(listCtrlSizer, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(listBoxSizer, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(self.setupTemplateFile, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(self.setupProjectFolder, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(setupBtn, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(qubePadSizer, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(qubeSubmitBtn, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(btnSizer, 0, wx.ALL|wx.CENTER, 5)
 
        self.panel.SetSizerAndFit(topSizer)
        topSizer.Fit(self)
 
    def onClose(self, event):
        self.closeProgram()
 
    def closeProgram(self):
        self.Close()
    
    def onLoad(self, event):
        dlg = wx.FileDialog(self, message="Open an Image...", defaultFile="", style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            xmlFile = dlg.GetPath()
            self.loadKeys([xmlFile])
    
    def onClear(self, event):
        self.listBox.Clear()
    
    def onSetup(self, event):
        pass
    
    def onQubeSubmit(self, event):
        pass
    
    def loadKeys(self, keys):
        for key in keys:
            self.listBox.Insert(key, 0, key)
            self.listBox.Select(0)
 
 
# Run the program
def load():
    app = wx.PySimpleApp()
    frame = XMLForm().ShowModal()