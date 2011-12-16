import sys
import os
import wx
import wx.lib.filebrowsebutton
import xml.dom.minidom
import uuid
from operator import itemgetter, attrgetter
import time

import xml2keys

def onDrop():
    # ----------------------------------------------------------------------
    # Grab all of the filenames from argv.
    # The first one will be the script file which we don't want.
    # ----------------------------------------------------------------------
    myFiles = {}
    for arg in sys.argv[1:]:
        
        # Gather the name
        myFile = {}
        
        myFile['path'] = arg
        path, ext = os.path.splitext(arg)
        myFile['name'] = os.path.basename(path)

        ext = ext[1:].lower() # Don't need the .        
        if not myFiles.has_key(ext):
            myFiles[ext] = []
        myFiles[ext].append(myFile)
    
    print myFiles
    
    if 'xml' in myFiles:
        paths = []
        for myFile in myFiles['xml']:
            paths.append(myFile['path'])
        xml2keys.load(paths)


# Go!
onDrop()
sys.exit(0)