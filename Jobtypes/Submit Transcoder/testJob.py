#!/usr/bin/python

# ======================================================
# Sample script:
#   cmdrange job submit with outputPaths
#
# PipelineFX, 2007
#
# ======================================================

import os, sys

# Make sure that qb module is in the python path
if 'QBDIR' in os.environ:
    sys.path.append('%s/api/python' % os.environ['QBDIR']);
elif os.uname()[0] == 'Darwin':
    sys.path.append('/Applications/pfx/qube/api/python');
else:
    sys.path.append('/usr/local/pfx/qube/api/python');

import qb

def main():
    # Set basic job properties
    job = {}
    job['name']         = 'Transcoder Test'
    job['cpus']         = 1
    job['prototype']    = 'Submit Transcoder'
    job['requirements'] = ''

    # Set the package properties
    job['package'] = {}
    job['package']['sequenceFolder'] = '~/Projects/Scripts+Apps/Qube/Compressor/Testing/blindnessIS/'
    job['package']['audioFile'] = '~/Projects/Scripts+Apps/Qube/Compressor/Testing/blindness.wav'
    job['package']['outputFile'] = '/tmp/trancoderTest.mov'
    job['package']['preset'] = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    job['package']['resolution'] = '1280x720'
    job['package']['frameRate'] = '29.97'
    job['package']['selfContained'] = True
    job['package']['smartUpdate'] = True

    # Calculate agenda from range
    chunkSize = 100
    agendaRange = '1-500'
    
    segmentAgenda = qb.genchunks(chunkSize, agendaRange)
    for segment in segmentAgenda:
        folder, name = os.path.split(job['package']['outputFile'])
        name, extension = os.path.splitext(name)
        outputPath = folder + '/Segments/' + name + '_' + segment['name'].split('-')[0] + extension
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
    agenda.append(qb.Work({'name':'Finalize'}))
    
    print agenda

    # Set the job agenda
    job['agenda'] = agenda

    # Submit
    listOfSubmittedJobs = qb.submit([job])

    # Report on submit results
    for job in listOfSubmittedJobs:
        print job['id']

if __name__ == "__main__":
    main()
    sys.exit(0)
