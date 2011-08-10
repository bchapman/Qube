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

FINALQUICKTIMEFRAMECOUNT = 5000 # Multiples of chunk size
CHUNKSIZE = 200

def setupSequenceJob(sequenceInitFile, outputFile, preset, selfContained, smartUpdate, transcoderFolder='', frameRange, audioFile=''):
    '''
    Setup a qube job dictionary based on the input.
    '''


def main():
    # Set basic job properties
    job = {}
    job['cpus']         = 100
    job['prototype']    = 'Submit Transcoder'
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1'
    job['flagsstring'] = 'auto_wrangling,expand'
    # job['hosts'] = 'bchapman.local'
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'

    # Set the package properties
    mySequence = sequenceTools.Sequence('/Volumes/theGrill/Elevate_Series/Power_Up/Kids/Art_Anim/_Renders_and_Exports/Image_Sequences/Bible_Stories/L1/PU_BS_L1_00000.png')
    # mySequence = sequenceTools.Sequence('/Volumes/theGrill/Staff-Directories/Brennan/testFrames/Sequence/testFrames_00000.png')
    bounds = mySequence.getBounds()
    outputFile = '/Volumes/theGrill/Staff-Directories/Brennan/testFrames/testFrames.mov'
    print bounds
    job['name'] = mySequence.prefix
    job['package'] = {}
    job['package']['sequence'] = mySequence.initFile
    job['package']['audioFile'] = '/Volumes/theGrill/Elevate_Series/Power_Up/Kids/Art_Anim/_Renders_and_Exports/Preliminary_Renders/Audio/Bible_Stories/L1/PU_BibleStory_Timeline_L1.wav'
    job['package']['outputFile'] = outputFile
    job['package']['preset'] = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    job['package']['resolution'] = '1280x720'
    job['package']['frameRate'] = '29.97'
    job['package']['selfContained'] = True
    job['package']['smartUpdate'] = True
    job['package']['frameRange'] = bounds['start'] + '-' + bounds['end']
    job['package']['transcoderFolder'] = os.path.dirname(outputFile) + '/Transcoder/'    

    '''
    Calculate agenda from range.
    Submit the segments as blocked, they will be unblocked once the initialize command is complete.
    Segments will be placed in the Transcoder folder under a subfolder with the name of the sequence.
    '''
    segmentAgenda = qb.genchunks(CHUNKSIZE, job['package']['frameRange'])
    for segment in segmentAgenda:
        folder, name = os.path.split(job['package']['outputFile'])
        name, extension = os.path.splitext(name)
        outputName = name + '/' + name + '_' + segment['name'].split('-')[0] + extension
        segment['status'] = 'blocked'
        segment.package({'outputName': outputName})

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
    
    job['callbacks'] = []
    for num in range (1, numFinalOutputs + 1):
        workDict = {}
        
        filePath, fileExt = os.path.splitext(os.path.basename(outputFile))
        letter = ''
        if numFinalOutputs > 1:
            letter = '_' + chr(64 + num)
        finalOutputFile = filePath + letter + fileExt
        
        startIndex = (num-1) * subjobsPerOutput
        if num != numFinalOutputs:
            endIndex = ((num) * subjobsPerOutput) - 1
        else:
            endIndex = startIndex + (len(segmentAgenda) - startIndex) - 1
        
        dependencies = []
        for segIndex in range(startIndex, endIndex + 1):
            dependencies.append(segmentAgenda[segIndex]['name'])
        
        myWork = qb.Work({'name':finalOutputFile, 'status':'blocked', 'package':{'Dependencies':','.join(dependencies)}})
        
        # Setup the callback to unblock the output work item
        callback = {}
        triggers = []
        for dependant in dependencies:
            triggers.append('complete-work-self-' + dependant)
        callback['triggers'] = ' and '.join(triggers)
        callback['language'] = 'python'
        
        code = 'import qb\n'
        code += '%s%s%s' % ('\nqb.workunblock(\'%s:', finalOutputFile, '\' % qb.jobid())')
        code += '\nqb.unblock(qb.jobid())'
        callback['code'] = code
        
        job['callbacks'].append(callback)

            
        # print "myWork: " + str(myWork)
        agenda.insert(endIndex+1+num, myWork)

    # agenda.append(qb.Work({'name':'Finalize', 'status':'blocked'}))

    # Set the job agenda
    job['agenda'] = agenda
    
    print job

    # Submit
    listOfSubmittedJobs = qb.submit([job])
    
    # Report on submit results
    for job in listOfSubmittedJobs:
        print job['id']

if __name__ == "__main__":
    main()
    sys.exit(0)
