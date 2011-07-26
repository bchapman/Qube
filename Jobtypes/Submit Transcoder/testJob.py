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

sys.path.append('/Volumes/theGrill/.qube/Modules')
import sequenceTools

def main():
    # Set basic job properties
    job = {}
    job['name']         = 'Transcoder Test'
    job['cpus']         = 10
    job['prototype']    = 'Submit Transcoder'
    job['requirements'] = ''
    job['reservations'] = 'host.processors=2'
    job['flagsstring'] = 'auto_wrangling,expand'
    job['hosts'] = 'bchapman'
    job['priority'] = 100

    # Set the package properties
    job['package'] = {}
    job['package']['sequence'] = '/Volumes/theGrill/Elevate_Series/Power_Up/Kids/Art_Anim/_Renders_and_Exports/Image_Sequences/Skit/L7/PU_Skit_L7_p1/PU_Skit_L2_p1_00000.png'
    job['package']['audioFile'] = '/Volumes/theGrill/Elevate_Series/Power_Up/Kids/Art_Anim/Skit/Assets/Audio/PU_L7_Skit_Part_1.wav'
    job['package']['outputFile'] = '/Volumes/theGrill/Elevate_Series/Power_Up/Kids/Art_Anim/_Renders_and_Exports/Preliminary_Renders/Skit/PU_Skit_L7_p1.mov'
    job['package']['preset'] = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    job['package']['resolution'] = '1280x720'
    job['package']['frameRate'] = '29.97'
    job['package']['selfContained'] = True
    job['package']['smartUpdate'] = True
    job['package']['frameRange'] = '0-4218'
    
    # Calculate agenda from range
    chunkSize = 100
    
    # Submit the segments as blocked, they will be unblocked once the initialize command is complete.
    segmentAgenda = qb.genchunks(chunkSize, job['package']['frameRange'])
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
    agenda.append(qb.Work({'name':'Finalize', 'status':'blocked'}))
    
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
