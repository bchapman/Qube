import sys
import os
for arg in sys.argv:
    file = '/tmp/test.aep'
    fileName = os.path.basename(file)
    fileExt = os.path.splitext(file)[1]
    if fileExt == '.nk':
    	cmd = '''/Applications/pfx/qube/qube.app/Contents/MacOS/qube --submitDict "{'name':'%s', 'prototype':'cmdrange', 'cpus':'15', 'package':{'executable':'/Applications/Nuke6.2v2/Nuke6.2v2.app/Nuke6.2v4', 'simpleCmdType': 'Nuke (cmdline)', 'script': '%s'}}"''' % (fileName, file)
    	os.popen(cmd)
    elif fileExt == '.aep':
        cmd = '''/Applications/pfx/qube/qube.app/Contents/MacOS/qube --submitDict "{'name':'%s', 'prototype':'Submit After Effects', 'cpus':'15', 'package':{'projectPath': '%s', 'simpleCmdType': 'Submit After Effects'}}"''' % (fileName, file)
        os.popen(cmd)