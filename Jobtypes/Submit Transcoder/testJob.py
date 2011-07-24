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
    job['package']['blenderScenePreset'] = '/Volumes/theGrill/.qube/Staging/Transcoder/Presets/Animation/Final_QT_4444.blend'
    job['package']['resolution'] = '1280x720'
    job['package']['frameRate'] = '29.97'
    job['package']['selfContained'] = True

    # Calculate agenda from range
    agendaRange = '1-500'
    agenda = qb.genchunks(100, agendaRange)
    
    # Set the outputPaths in the resultpackage for each agenda item
    for i in agenda:
        i.package({'outputPath': 'SampleSegmentPath', 'startFrame': '1', 'endFrame': '100'})

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
