###########################################################################
#
# Copyright (c) PipelineFX L.L.C. All rights reserved.
#
###########################################################################
#
# Filename: README-satellite.txt
#
# Description:
#
#  This file describes how to use mental ray for Maya satellite rendering
#  with Qube! 
#  
#  Please read this file carefully, if you would like to take advantage
#  of mental ray satellite rendering for Maya with Qube!
#
###########################################################################

[REQUIREMENTS]

* Qube! Core 5.1 or above (on submission clients and workers)
* Qube! Worker 5.1 or above (workers)
* Qube! GUI 5.5-x or above (clients)
* Qube! Maya Jobtype 5.2 or above (clients and workers)
* Maya 7.0 or above (workers)
* mental ray satellite for Maya (proper version for your Maya, on workers)

First and foremost, mental ray satellite for Maya rendering must be
setup and tested to be working properly, outside of Qube!  Please
consult your Maya documentation for details on setting up satellite
slave nodes.


[INSTALLATION]

The satellite support is built into the jobtype, so no special
installation needs to be done, other than making sure that all the
requirements listed above are satisfied.


[USAGE]

* Open or create a scene.

* Make sure the scene's (or layer's) renderer is set to "mental ray".

* Save the scene if changes were made.

* Open the Qube! Submission dialog.  From Maya, "Qube! > Submit
  Render...", or from the QubeGUI "Submit > Maya Job..."

* Find the "m-ray Satellite" pull-down menu (for pre-5.5, this is
  labeled "mental ray Satellite" and is found in the "Render Settings
  Override" tab).  Specify either "Unlimited (8 CPUs)" or "Complete (2
  CPUs)".  This will check out the "Unlimited" or "Complete" Mayatomr
  license, respectively.

* In the "CPUs" box (for pre-5.5, found in the "Qube Options" tab),
  specify the proper number of CPUs.  This should usually be 2 for
  "Complete", and 8 for "Unlimited", but could be set to smaller
  numbers.

* In the "reservations" box, specify "host.processors=1+", so that
  your subjobs will each occupy the entire node that it lands on

When the job is submitted, the Qube supervisor will choose and reserve
N (the number you specified in the "CPUs" field) workers for your job
automatically, and make the first node (subjob 0) be the "master" node
to initiate and book-keep the satellite job, and the rest of the
chosen nodes to be the "slaves".

You don't have manually write a "maya.rayhosts" file, as the system
will automatically generate one for you, after allocating the
machines.


[USAGE NOTES]

Side-Effects:

The jobtype will re-write your [maya.rayhosts] file in the following
locations, on the master node (i.e., where subjob 0 runs):

Linux:
  $HOME/maya/<ver>/prefs/maya.rayhosts

Windows:
  $USERPROFILES/My Documents/maya/<ver>/prefs/maya.rayhosts

MacOSX:
  $HOME/Library/Preferences/Autodesk/maya/<ver>prefs/maya.rayhosts

The jobtype will try to back up the original rayhosts file, if it
exists, before the execution of the job, and then restore it
afterwards, but if the job dies in the middle, the restore may not
work properly.


[KNOWN ISSUES]

* Workers will wait idle until the specified number of CPUs are
  collected for the job.  For example, if a job specified 8 CPUs, the
  job will not start processing until all 8 CPUs are available--
  sometimes the first 7 CPUs can wait for a long time before the 8th
  one becomes available.

* If different renderers are designated for different layers, only
  those layers whose renderer is set to "mental ray" will take
  advantage of the multiple render nodes.  The job will render the
  other layers as well, but only using the master node.

* Due to the inherent dependency on "maya.rayhosts" file of mental ray
  satellite renders, attempts to run more than one satellite job
  concurrently by the same user may cause serious instability in the
  system, and thus is unsupported.

* Mixed-Platform satellite renders may work, but are not recommended.

* Using the 'Use "batch mode"' option will conflict with the satellite
  rendering option, and the behavior is undefined.

* All limitations of the Maya jobtype apply to satellite rendering on
  Qube.  For example, the scenefile must be located on a shared
  file-server path where all workers may uniformly access.

* All limitations of mental ray for Maya and mental ray satellite for
  Maya inherently apply.  For example, if a satellite node becomes
  inaccessible during a render, the entire job may crash, due to the
  nature of the mental ray satellite software.

