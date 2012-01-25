###########################################################################
#
# Copyright (c) PipelineFX L.L.C. All rights reserved.
#
###########################################################################
#
# Filename: README.txt
#
# Description:
#
#  This is the README file for the maya jobtype for Qube!  It contains 
#  the latest information about this package.
#
###########################################################################

!!!! IMPORTANT !!!!

As of version 5.5-0 of the maya jobtype, the binary plugin (qb.mll,
qb.so, qb.bundle) and the various mel scripts that were used to build
the in-app submission dialog for Maya have been depricated.  The
submission dialog is now shared with the Qube GUI.  You will still be
able to submit jobs from inside Maya, but you will need to install
Qube GUI, and follow the simple one-time instruction found in the
[INSTALLATION] section below to enable the in-app submission.


[REQUIREMENTS]

* Maya 7 or above (on submission clients and workers)
* Qube! Core (on clients and workers)
* Qube! Worker (on workers)
* Qube GUI 5.5-x or above (on clients)


[INSTALLATION]

* Uninstall any previous version of the jobtype.

* Install the jobtype on the clients and workers.

* Install Qube GUI on the clients.

* To add the in-app submission for Maya render jobs, launch Qube GUI,
  then choose: "File > Install App UI > Install 'Maya' App UI...".

* To add the in-app submission for Maya batch render jobs, launch Qube
  GUI, then choose:
  "File > Install App UI > Install 'Maya Batch Render' App UI...".

* Restart Maya, and you will find a "Submit Render Job..." menu item
  under the "Qube!" menu.


[USAGE]

* Launch Maya and load a Maya scene file

* Under the "Qube!" menu, choose:

  * "Submit Render Job..." to submit a render, or

  * "Submit Batch Currnet Render ..." to submit a batch render using
    the current renderer, or

  * one of the sub menu items under "Submit Batch Render" to submit a
    batch render using a specific renderer

* Alternatively, you can submit jobs from the Qube GUI.

* Monitor job progress from the QubeGUI


[KNOWN ISSUES]

* Since Maya is notorious for generating "Error:" messages during
  loading of a scene file even if the errors are non-fatal (i.e., they
  should really be "Warning:" messages), our code ignores any "Error:"
  messages generated during scene file loading.

* mental ray for Maya, due to its multi-threaded nature, mixes up its
  stdout and stderr output messages, especially on Windows platforms.
  This makes it very difficult for our output parsing engine to
  reliably detect the output image file name from mental ray renders,
  and sometimes affects the frame's completion status-- the users are
  advised to not solely rely on the frame complete/failed status from
  Qube!, but to also check the stdout/stderr logs and their image
  files to determine if the frames completed OK or not.

