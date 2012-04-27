import os
import logging
import wx
import wx.lib.filebrowsebutton
import simplejson as json
import hashlib

import AESocket

DATAPREFIX = ".DATA."

class aeProjectBrowseButton(wx.lib.filebrowsebutton.FileBrowseButtonWithHistory):
    def __init__(self, *arguments, **namedarguments):
        wx.lib.filebrowsebutton.FileBrowseButtonWithHistory.__init__(self, *arguments, **namedarguments)
    
    def OnBrowse(self, ev=None):
        '''
        Add the changeCallback to the onBrowse button.
        '''
        super(wx.lib.filebrowsebutton.FileBrowseButtonWithHistory, self).OnBrowse(ev)
        if self.changeCallback:
            self.changeCallback(ev)
        
class AEDataError(Exception):
    '''
    Errors from processing the data file.
    '''
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr("After Effects Data File returned an error.\n%s" % self.value)


class AEProjectWidget(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, value=wx.EmptyString, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, projectPathCallback=None):
        wx.Panel.__init__ (self, parent, id, pos, size, style)

        logging.debug("Project Path Callback: %s" % projectPathCallback)
        
        self.SetMinSize(size)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.projectFile = aeProjectBrowseButton(self, -1, labelText="", labelWidth=0, buttonText="Browse", startDirectory="/", toolTip="Choose After Effects Project.", dialogTitle="Choose your After Effects Project", fileMask="*.aep", fileMode=1, changeCallback=self.updateProjectFile)

        self.rqItemList = wx.CheckListBox(self, -1, choices=['Choose a project file.'], size=(-1, 100))
        self.rqItemList.Disable()
        
        self.outputList = wx.ListBox(self, -1, choices=['Select a render queue item.'], size=(-1, 50), style=wx.LB_SINGLE|wx.LB_NEEDED_SB)
        self.outputList.Disable()
        
        sizer.Add( self.projectFile, 0, wx.EXPAND|wx.ALL, 2)
        sizer.Add( self.rqItemList, 0, wx.EXPAND|wx.ALL, 2)
        sizer.Add( self.outputList, 1, wx.EXPAND|wx.ALL, 2)
        self.SetSizer(sizer)

        # Cleanup the layout
        self.SetAutoLayout(True)
        self.Layout()
        self.SetDimensions(-1, -1, size[0], size[1], wx.SIZE_USE_EXISTING)
        
        # Bind the events from the rqItemList
        self.Bind(wx.EVT_LISTBOX, self.updateOutputModules)
        
        self.projectPathCallback = projectPathCallback
        
        self.changeCallback = None

    def createDataFile(self, projectPath):
        '''
        Launch AERender and create the data file needed for the project.
        '''

        pValue = 0
        pIncrement = 10
        pDlg = wx.ProgressDialog ( 'Loading Project Data...', 'Lauching After Effects...', maximum = 100, style=wx.PD_SMOOTH)
        pDlg.SetSize((300, -1))

        try:

            s = AESocket.AESocket()        

            # ----------------------------------------------
            pDlg.Update(pValue, "Starting After Effects...")
        
            result = s.launchAERender()
            logging.debug("Launch AERender Result: %s" % result)
        
            pValue += pIncrement
            pDlg.Update(pValue, "After Effects Loaded")
            # ----------------------------------------------
            pDlg.Update(pValue, "Loading project...")

            result = s.runScript("app.openFast(new File(\"%s\"));\"Project Loaded\";" % projectPath)
            logging.debug("Loading Project Result: %s" % result)
        
            pValue += pIncrement
            pDlg.Update(pValue, "Project Loaded")
            # ----------------------------------------------
            pDlg.Update(pValue, "Creating Data File...")
        
            result = s.runScriptFile("/Volumes/Grill/.qube/Jobtypes/Submit After Effects v2/Scripts_Remote/createDataFile.jsx")
            logging.debug("Creating Data File Result: %s" % result)
        
            pValue += pIncrement
            pDlg.Update(pValue, "Data File Created")
            # ----------------------------------------------
            pDlg.Update(pValue, "Closing After Effects...")

            result = s.terminateConnection()
            logging.debug("Closing AE Result: %s" % result)
        
            pValue += pIncrement
            pDlg.Update(pValue, "After Effects Closed")
            # ----------------------------------------------
            pDlg.Update(100, "Complete!")
            pDlg.Destroy()
        
        except AESocket.AESocketError, e:
            self.errorMessage(str(e))
            pDlg.Destroy()

    def loadAEData(self, dataFile):
        '''
        Load the data stored in the dataFile from AFter Effects.
        '''
        try:
            fileData = open(dataFile, 'r')
            
            jsonData = json.load(fileData)
            logging.debug("Data from DATA File: %s" % jsonData)

            return jsonData
        except Exception, e:
            raise AEDataError("Unable to load data file.%s" % e)
            
    def processAEData(self, data):
        '''
        Process the data loaded from After Effects into the dialog.
        '''
        logging.debug("Processing Data: %s" % data)
        self.rqItemList.Clear()
        if len(data['rqItems']) > 0:                
            for item in data['rqItems']:
                r = self.rqItemList.Append("%s) %s" % (item['index'], item['comp']), clientData=item)

                # 2615 is the id for a queued rq item from AE
                if str(item['status']).strip() == "2615":
                    self.rqItemList.Check(r)
                    
                self.rqItemList.Enable()
        else:
            self.rqItemList.Append("No items in project's render queue.")        

    def errorMessage(self, msg):
        '''
        Display an error message.
        '''
        dlg = wx.MessageDialog(None, msg, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()

    def compareHash(self, fileA, fileB):
        # Get the hash of fileA
        fileAContents = open(fileA, 'rb').read()
        fileAHash = hashlib.md5(fileAContents).hexdigest()

        # Get the hash of the server script
        fileBContents = open(fileB, 'rb').read()
        fileBHash = hashlib.md5(fileBContents).hexdigest()

        if (fileAHash == fileBHash):
            return True
        else:
            return False

    def getProjectHash(self, filePath):
        fileData = open(filePath, 'rb').read()
        fileHash = hashlib.md5(fileData).hexdigest()
        return fileHash

    def updateProjectFile(self, itm):
        '''
        Callback for when the project file value is changed.
        '''
        projPath = self.projectFile.GetValue()

        if os.path.exists(projPath):
            logging.debug("Project File Exists")
            
            # Ensure that the file is in the history
            currHistory = list(set(self.projectFile.GetHistory()))
            if projPath not in currHistory:
                logging.debug("Adding project file to history. %s" % projPath)
                currHistory.append(projPath)
                self.projectFile.SetHistory(currHistory)
            else:
                logging.debug("Project file already in history. %s" % projPath)

            # Load the data file
            dataFile = "%s/%s%s" % (os.path.dirname(projPath), DATAPREFIX, os.path.basename(projPath))

            createdDataFile = False
            if not os.path.exists(dataFile):
                self.createDataFile(projPath)
                createdDataFile = True
            if not os.path.exists(dataFile):
                raise AEDataError("Data File unable to be created.")
                
            # Load the AEData
            data = self.loadAEData(dataFile)
            
            # Check the hashes if we didn't just create it
            if not createdDataFile:
                dataHash = data['project']['hash']
                projHash = self.getProjectHash(projPath)
                if dataHash == projHash:
                    logging.debug("Hash codes are the same.")
                else:
                    logging.info("Data file out of date. Creating new data file...")
                    self.createDataFile(projPath)
                    createdDataFile = True
                    data = self.loadAEData(dataFile)
            
            self.processAEData(data)

            # Widget must be of the type 'file' to activate this.
            self.changeCallback(None)

        else:
            self.rqItemList.Clear()
            c = self.rqItemList.Append("Project File Not Found.")
            self.rqItemList.Disable()

    def updateOutputModules(self, evt):
        '''
        Update the output module list when a selection
        is made in the rqItem list.
        '''
        try:
            sel = self.rqItemList.GetSelection()
            data = self.rqItemList.GetClientData(sel)
            self.outputList.Clear()
            for output in data['outFilePaths']:
                self.outputList.Append(os.path.basename(output))
            self.outputList.Enable()
        except:
            self.outputList.Clear()
            self.outputList.Disable()

    def GetValue(self):
        '''
        Return a dictionary of the widgets content for submission.
        
        Contents:
        projectPath
        projectHistory - Limited to 10 items
        rqItems - with clientData
        '''
        result = {}
        projectFile = self.projectFile.GetValue()
        if os.path.exists(projectFile):
            result['projectPath'] = projectFile
        else:
            result['projectPath'] = None
        result['projectHistory'] = self.projectFile.GetHistory()[0:9]
        
        result['rqItems'] = []
        items = self.rqItemList.GetChecked()
        for item in items:
            result['rqItems'].append(self.rqItemList.GetClientData(item))
        
        logging.debug("GetValue Result: %s" % result)

        return result

    def SetValue(self, data):
        '''
        Set the values of the widget based on a dictionary.
        Only sets the actual projectPath when ['setProjectPath'] is set.
        We only want to auto load if this is submitted using AE.
        Otherwise the user selects the file to load from the history.
        '''
        try:
            self.projectFile.SetHistory(data['projectHistory'])
            if data.has_key('setProjectPath'):
                self.projectFile.SetValue(data['setProjectPath'])
                self.updateProjectFile(None)
        except Exception, e:
            logging.warning("Unable to load previous settings. %s" % e)