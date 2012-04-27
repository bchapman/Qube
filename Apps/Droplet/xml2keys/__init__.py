import os
import time
import sys
import wx
import wx.lib.filebrowsebutton
import xmeml
from operator import itemgetter, attrgetter
import shutil
import subprocess
import re

import inspect

class FrameRange:
    def __init__(self, frameRangeString):
        self.frameRange = []
        self.addRange(frameRangeString)
    
    def addRange(self, frameRange):
        '''
        Parse an input frame range into individual frame numbers
        Ex: 1,20-25,22,100 -> [1, 20, 21, 22, 23, 24, 25, 100]
        Input can also be a list of frames, to save time.
        Updated to be much faster!
        '''

        result = []
        if type(frameRange) is str:
            newRange = list(set(sum(((list(range(*[int(j) + k for k,j in enumerate(i.split('-'))]))
                if '-' in i else [int(i)]) for i in frameRange.replace(' ','').split(',')), [])))
            result = list(set(newRange + self.frameRange))
            self.frameRange = result
        else:
            self.frameRange = frameRange

    def convertListToRanges(self, frames):
        '''
        Convert an array of frame numbers into a string of frame ranges.
        Ex: 1,2,3,4,5,10 -> 1-5,10
        '''

        i = 0
        frameRanges = []
        frames.sort()
        if (len(frames) > 0):
            while(i+1 <= len(frames)):
                rangeStart = frames[i]

                while(i+2 <= len(frames)):
                    if (int(frames[i]) + 1 != int(frames[i+1])):
                        break
                    else:
                        i = i+1

                if (rangeStart != frames[i]):
                    rng = str(rangeStart) + "-" + str(frames[i])
                    frameRanges.append(rng)
                else:
                    rng = str(rangeStart)
                    frameRanges.append(rng)
                i = i+1

        return ','.join(frameRanges)
    
    def addPadding(self, padding):

        padding = int(padding)
        i = 0
        frames = self.frameRange
        newFrameRanges = []
        frames.sort()
        if (len(frames) > 0):
            while(i+1 <= len(frames)):
                rangeStart = frames[i]

                while(i+2 <= len(frames)):
                    if (int(frames[i]) + 1 != int(frames[i+1])):
                        break
                    else:
                        i = i+1

                rngMin = 0
                rngMax = 0
                if (rangeStart != frames[i]):
                    rngMin = int(rangeStart)
                    rngMax = int(frames[i])
                else:
                    rngMin = rngMax = int(rangeStart)

                newMin = rngMin - padding
                if newMin < 0:
                    newMin = 0
                newMax = rngMax + padding
                newFrameRanges.append("%s-%s" % (newMin, newMax))
                i = i+1

        self.addRange(','.join(newFrameRanges))

    def __str__(self):
        return self.convertListToRanges(self.frameRange)

class Key:
    def __init__(self, id, footageFile, frameRange, xmlFile):
        self.id = id
        self.footageFile = footageFile
        self.frameRange = FrameRange(frameRange)
        self.xmlFile = xmlFile
        
    def getProjectPath(self, projectFolder):
        print "projectFolder: %s" % projectFolder
        print "footageFile: %s" % self.footageFile
        print "frameRange: %s" % self.frameRange
        print "id: %s" % self.id
        patt = re.compile("Capture.Scratch", re.IGNORECASE)
        subpath = patt.split(self.footageFile)[1]
        print "subpath: %s" % subpath
        print "xmlFile: %s" % os.path.basename(self.xmlFile)
        subpath, ext = os.path.splitext(subpath)
        result = projectFolder +"/" + os.path.basename(self.xmlFile) + "/" + subpath + ".nk"
        print "getProjectPath result: %s" % result
        return result

    def addRange(self, frameRange):
        self.frameRange.addRange(frameRange)

    def __str__(self):
        return "%s - %s" % (self.id, self.frameRange)
 
class XMLDialog(wx.Dialog):
 
    def __init__(self, title='XML 2 Keys', xmlFiles=[]):
        wx.Dialog.__init__(self, None, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
 
        # Add a panel so it looks correct on all platforms
        self.panel = wx.Panel(self, wx.ID_ANY)
 
        print "PATH: %s" % sys.path
        imageFile = "xml2keys.jpg"
        print "Exists: %s" % os.path.exists(imageFile)
        jpg = wx.Image(imageFile, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        title = wx.StaticBitmap(self.panel, wx.ID_ANY, jpg, (10 + jpg.GetWidth(), 5), (jpg.GetWidth(), jpg.GetHeight()))
        # title = wx.StaticText(self.panel, wx.ID_ANY, title)

        loadBtn = wx.Button(self.panel, wx.ID_ANY, 'Load XML', size=(195, -1))
        clearBtn = wx.Button(self.panel, wx.ID_ANY, 'Clear List', size=(195, -1))
        self.Bind(wx.EVT_BUTTON, self.onLoad, loadBtn)
        self.Bind(wx.EVT_BUTTON, self.onClear, clearBtn)

        self.listBox = wx.ListBox(self.panel, -1, style=wx.LB_MULTIPLE, size=(400, 250))

        # Setup Panel
        self.setupTemplateFile = wx.lib.filebrowsebutton.FileBrowseButton(self.panel, wx.ID_ANY)
        self.setupTemplateFile.SetLabel("Template File")
        self.setupProjectFolder = wx.lib.filebrowsebutton.DirBrowseButton(self.panel, wx.ID_ANY)
        self.setupProjectFolder.SetLabel("Nuke Projects Folder")
        setupBtn = wx.Button(self.panel, wx.ID_ANY, 'Setup Projects', size=(300, -1))
        self.Bind(wx.EVT_BUTTON, self.onSetup, setupBtn)
        
        # Qube Panel
        qubePaddingLbl = wx.StaticText(self.panel, wx.ID_ANY, 'Padding')
        self.qubePadding = wx.TextCtrl(self.panel, wx.ID_ANY, '30')
        qubeSubmitBtn = wx.Button(self.panel, wx.ID_ANY, 'Submit to Qube', size=(300, -1))
        self.Bind(wx.EVT_BUTTON, self.onQubeSubmit, qubeSubmitBtn)

        closeBtn = wx.Button(self.panel, wx.ID_ANY, 'Close', size=(400, -1))
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
        qubePadSizer.Add(self.qubePadding, 0, wx.ALL|wx.EXPAND, 5)
 
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
        
        self.keys = []
        for xmlFile in xmlFiles:
            self.loadXML(xmlFile)
 
    def onClose(self, event):
        self.closeProgram()
 
    def closeProgram(self):
        self.Close()
    
    def onLoad(self, event):
        dlg = wx.FileDialog(self, message="Open an Image...", defaultFile="", style=wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            xmlFile = dlg.GetPath()
            self.loadXML(xmlFile)
    
    def onClear(self, event):
        self.listBox.Clear()
        self.keys = []
    
    def onSetup(self, event):
        keyTemplate = self.setupTemplateFile.GetValue()
        projectFolder = self.setupProjectFolder.GetValue()
        selectedKeys = self.listBox.GetSelections()
        keys = []
        for key in selectedKeys:
            keys.append(self.listBox.GetClientData(key))
        if not keyTemplate:
            self.messageDialog("Missing Key Template", "Please supply a nuke key template.")
        elif not projectFolder:
            self.messageDialog("Missing Project Folder", "Please provide the folder to store all the nuke projects.")
        elif len(keys) < 1:
            self.messageDialog("Select Keys", "Please select which keys to setup.")
        else:
            dlg = wx.ProgressDialog("Setting Up Keys", "Progress", len(keys),
                    style=wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME | wx.PD_AUTO_HIDE | wx.PD_SMOOTH | wx.PD_APP_MODAL, parent=self)
            
            count = 0
            keepGoing = True
            for key in keys:
                count += 1
                projPath = key.getProjectPath(projectFolder)
                print "projPath: %s" % projPath
                if not os.path.exists(projPath):
                    print "Creating file %s" % projPath
                    # try:
                    self.createFoldersToPath(str(projPath))
                    shutil.copy2(str(keyTemplate), str(projPath))
                    # except:
                    #     print "Error creating file %s" % projPath
                keepGoing, skip = dlg.Update(count)
                if not keepGoing:
                    break

            dlg.Destroy()
    
    def messageDialog(self, title, msg):
        dlg = wx.MessageDialog(self, msg, title, wx.OK)
        result = dlg.ShowModal()
        dlg.Destroy()
        
    def onQubeSubmit(self, event):
        padding = self.qubePadding.GetValue()
        projectFolder = self.setupProjectFolder.GetValue()
        selectedKeys = self.listBox.GetSelections()
        keys = []
        for key in selectedKeys:
            keys.append(self.listBox.GetClientData(key))
        if not padding:
            self.messageDialog("Missing Padding", "Please enter the number of frames to pad the keys with.")
        elif not projectFolder:
            self.messageDialog("Missing Project Folder", "Please provide the folder to store all the nuke projects.")
        elif len(keys) < 1:
            self.messageDialog("Select Keys", "Please select which keys to setup.")
        else:
            dlg = wx.ProgressDialog("Submitting to Qube", "Progress", len(self.keys),
                    style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_SMOOTH | wx.PD_APP_MODAL, parent=self)
            
            count = 0
            keepGoing = True
            for key in keys:
                
                key.frameRange.addPadding(padding)
                cmd = '''/Applications/pfx/qube/qube.app/Contents/MacOS/qube --submitDict \
"{'name':'%s', 'prototype':'cmdrange', 'cpus':'15', 'reservations':'host.processors=1+', \
'groups':'Nuke', 'retrywork':'3', 'retrysubjob':'3', 'package':{'threads':'16', \
'executable':'/Applications/Nuke6.3v5/Nuke6.3v5.app/Nuke6.3v5', 'simpleCmdType': \
'Nuke (cmdline)', 'script': '%s', 'rangeExecution':'chunks:5', 'rangeChunkSize':'5', 'range':'%s'}}
"''' % (key.id, key.getProjectPath(projectFolder), str(key.frameRange))

            	p = subprocess.Popen(cmd, shell=True)
            	while p.poll():
            	    time.sleep(.1)
                    keepGoing, skip = dlg.Update(count)
                    if not keepGoing:
                        break
            	
            	count += 1
                keepGoing, skip = dlg.Update(count)
                if not keepGoing:
                    break
            
            dlg.Destroy()
    
    def loadXML(self, xmlFile):
        self.keys = self.processXML(xmlFile)
        count = 0
        for key in self.keys:
            self.listBox.Insert(str(key), count, key)
            self.listBox.SetSelection(count)
            count += 1

    def addKey(self, id, file, frameRange, keys, xmlFile):
        print "addKey\nid:%s\nfile:%s\nframeRange:%s\nkeys:%s" % (id, file, frameRange, keys)
        if file:
            keys.append(Key(id.strip(), file, frameRange, xmlFile))
            # print "ADD KEY - ID: %s  File: %s : %s" % (id, file, frameRange)
        else:
            newID = id.rsplit(" ",1)[0]
            found = False
            for key in keys:
                if newID == key.id:
                    key.addRange(frameRange)
                    # print "ADD RANGE - %s to key %s" % (frameRange, key.id)
                    found = True
            if not found:
                print "Unable to find match for key %s" % newID

    def processXML(self, xmlFile):
        
        keys = []
        
        sequence = xmeml.VideoSequence(file=xmlFile)

        for item in sequence.track_items:
            filePath = None
            try:
                if item.in_frame:
                    for n in item.dom.childNodes:
                        if n.nodeType==1 and n.tagName in ('file'):
                            for t in n.childNodes:
                                if t.nodeType==1 and t.tagName in ('pathurl'):
                                    filePath = xmeml.xml2dict(t).replace("file://localhost", "")
                                    filePath = filePath.replace("%20", " ")
                    self.addKey(item.id, filePath, "%s-%s" % (item.in_frame, item.out_frame), keys, xmlFile)
            except:
                pass

        keys = sorted(keys, key=attrgetter('id'))
        return keys
    
    def createFoldersToPath(self, path):
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
 
# Run the program
def load(xmlFiles):
    app = wx.PySimpleApp()
    frame = XMLDialog(xmlFiles=xmlFiles).ShowModal()
