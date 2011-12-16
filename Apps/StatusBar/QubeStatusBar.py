import objc
from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder, AppHelper
import subprocess
import time

start_time = NSDate.date()

QMASTERPREFS = "/usr/sbin/qmasterprefs"
QBADMIN = "/Applications/pfx/qube/sbin/qbadmin"


def startQmaster():
    cmd = '\"' + QMASTERPREFS + '\" -reset -startSharing'
    p = subprocess.Popen(cmd, shell=True)
    print "Qmaster Started"
    
def stopQmaster():
    cmd = '\"' + QMASTERPREFS + '\" -stopSharing'
    p = subprocess.Popen(cmd, shell=True)
    print "Qmaster Stopped"

class Timer(NSObject):
     '''
     Application delegate
     '''
     statusbar = None

     def applicationDidFinishLaunching_(self, notification):
         print 'timer launched'
         # Make the statusbar item
         statusbar = NSStatusBar.systemStatusBar()
         # if you use an icon, the length can be NSSquareStatusItemLength
         statusitem = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
         self.statusitem = statusitem  # Need to retain this for later
         self.imageA = NSImage.imageNamed_("on.png")
         self.imageB = NSImage.imageNamed_("off.png")
         statusitem.setImage_(self.imageA)
         #statusitem.setMenu_(some_menu)
         statusitem.setToolTip_('Elevate Qube Status')
         statusitem.setAction_('terminate:') # must have some way to exit
         # statusitem.setTitle_('Hello')
         self.timer = NSTimer.alloc().initWithFireDate_interval_target_selector_userInfo_repeats_(\
             start_time,\
             1.0,\
             self,\
             'display:',\
             None,\
             True\
         )
         NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSDefaultRunLoopMode)
         self.timer.fire()

     def display_(self, notification):
         print 'display:'
         if int(elapsed()) % 2 == 1:
             self.statusitem.setImage_(self.imageA)
         else:
             self.statusitem.setImage_(self.imageB)


def elapsed():
     return str(int(NSDate.date().timeIntervalSinceDate_(start_time)))

if __name__ == "__main__":
     # app = NSApplication.sharedApplication()
     # delegate = Timer.alloc().init()
     # app.setDelegate_(delegate)
     # AppHelper.runEventLoop()
     startQmaster()
     time.sleep(15)
     stopQmaster()