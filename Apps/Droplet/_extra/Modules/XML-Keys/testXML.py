import sys
import os
sys.path.append("/Users/bchapman/Projects/Scripts+Apps/xmeml")

import xmeml
# import sequenceTools

class Key:
    def __init__(self, id, file, frameRange):
        self.id = id
        self.file = file
        self.frameRanges = []
        self.frameRanges.append(frameRange)
        
    def addRange(self, frameRange):
        if frameRange not in self.frameRanges:
            self.frameRanges.append(frameRange)
        else:
            pass
            # print "Frame Range %s already in key %s" % (frameRange, self.id)

    def __str__(self):
        return "%s - %s" % (self.id, self.frameRanges)

def addKey(id, file, frameRange):
    if file:
        keys.append(Key(id.strip(), file, frameRange))
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

def processXML(sequence, keyfolder):
    keys = []
    
    for item in sequence.track_items:
        filePath = None
        try:
            if item.in_frame:
                for n in item.dom.childNodes:
                    if n.nodeType==1 and n.tagName in ('file'):
                        for t in n.childNodes:
                            if t.nodeType==1 and t.tagName in ('pathurl'):
                                filePath = xmeml.xml2dict(t).replace("file://localhost", "")
                addKey(item.id, filePath, "%s-%s" % (item.in_frame, item.out_frame))
        except:
            pass

    return keys


testSequence = xmeml.VideoSequence(file="/Users/bchapman/Projects/Scripts+Apps/Qube/_localRepo/Apps/Droplet/Modules/XML-Keys/GN_L1_Bible.xml")
print vars(testSequence)
keyFolder = "/Volumes/Xsan/ELEVATE/"
keys = processXML(testSequence, keyFolder)
for key in keys:
    print key
