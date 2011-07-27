#!/usr/bin/python

# ======================================================
# Sample script:
#   cmdrange job submit with outputPaths
#
# PipelineFX, 2007
#
# ======================================================

import os, sys
import math

# Make sure that qb module is in the python path
if 'QBDIR' in os.environ:
    sys.path.append('%s/api/python' % os.environ['QBDIR']);
elif os.uname()[0] == 'Darwin':
    sys.path.append('/Applications/pfx/qube/api/python');
else:
    sys.path.append('/usr/local/pfx/qube/api/python');

import qb

sys.path.append('/Volumes/theGrill/.qube/Modules')
import sequenceTools

FINALQUICKTIMEFRAMECOUNT = 2000 # Multiples of 100
CHUNKSIZE = 100

def main():
    # Set basic job properties
    job = {}
    job['cpus']         = 10
    job['prototype']    = 'Submit Transcoder'
    job['requirements'] = ''
    job['reservations'] = 'host.processors=2'
    job['flagsstring'] = 'auto_wrangling,expand'
    job['hosts'] = 'bchapman.local'
    job['priority'] = 100

    # Set the package properties
    mySequence = sequenceTools.Sequence('/Volumes/theGrill/Staff-Directories/Brennan/testFrames/Sequence/testFrames_00000.png')
    bounds = mySequence.getBounds()
    outputFile = '/Volumes/theGrill/Staff-Directories/Brennan/testFrames/testFrames.mov'
    print bounds
    job['name'] = mySequence.prefix
    job['package'] = {}
    job['package']['sequence'] = mySequence.initFile
    job['package']['audioFile'] = '/Volumes/theGrill/Staff-Directories/Brennan/testFrames/testAudio.wav'
    job['package']['outputFile'] = outputFile
    job['package']['preset'] = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    job['package']['resolution'] = '1280x720'
    job['package']['frameRate'] = '29.97'
    job['package']['selfContained'] = True
    job['package']['smartUpdate'] = True
    job['package']['frameRange'] = bounds['start'] + '-' + bounds['end']
    

    '''
    Calculate agenda from range.    
    Submit the segments as blocked, they will be unblocked once the initialize command is complete.
    '''
    segmentAgenda = qb.genchunks(CHUNKSIZE, job['package']['frameRange'])
    for segment in segmentAgenda:
        folder, name = os.path.split(job['package']['outputFile'])
        name, extension = os.path.splitext(name)
        outputPath = folder + '/Segments/' + name + '_' + segment['name'].split('-')[0] + extension
        segment['status'] = 'blocked'
        segment.package({'outputPath': outputPath})

    '''
    Setup the agenda
        1 - First subjob is the initialization to setup the blender scene
        2-n - Subsequent subjobs are for the sections of the sequence
        n+1 - Last subjob is for the finalizing to merge the segments together
    '''
    agenda = []
    agenda.append(qb.Work({'name':'Initialize'}))
    agenda.extend(segmentAgenda)
    
    '''
    Submit the finalize command as blocked.
    It will be unblocked once the segments are completed.
    '''
    
    subjobsPerOutput = FINALQUICKTIMEFRAMECOUNT / CHUNKSIZE
    numFinalOutputs = int(math.ceil(int(bounds['end']) / FINALQUICKTIMEFRAMECOUNT)) + 1
    print "numFinalOutputs: " + str(numFinalOutputs)
    
    for num in range (1, numFinalOutputs + 1):
        workDict = {}
        
        filePath, fileExt = os.path.splitext(os.path.basename(outputFile))
        finalOutputFile = filePath + '_' + chr(64 + num) + fileExt
        
        startIndex = (num-1) * subjobsPerOutput
        if num != numFinalOutputs:
            endIndex = ((num) * subjobsPerOutput) - 1
        else:
            endIndex = startIndex + (len(segmentAgenda) - startIndex) - 1
        
        dependencies = []
        for segIndex in range(startIndex, endIndex + 1):
            dependencies.append(segmentAgenda[segIndex]['name'])
        
        # workDict['package'] = {'Dependencies':','.join(dependencies)}
        
        # print workDict
        myWork = qb.Work({'name':finalOutputFile, 'status':'blocked', 'package':{'Dependencies':','.join(dependencies)}})
        # print "myWork: " + str(myWork)
        agenda.append(myWork)

    # agenda.append(qb.Work({'name':'Finalize', 'status':'blocked'}))
    


    # Set the job agenda
    job['agenda'] = agenda

    print agenda

    # Submit
    listOfSubmittedJobs = qb.submit([job])
    
    # Report on submit results
    for job in listOfSubmittedJobs:
        print job['id']

if __name__ == "__main__":
    main()
    sys.exit(0)
