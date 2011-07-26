# Blender Initialize
# Author: Brennan Chapman
# Date: 7/11/2011
'''
Initliaze the transcoder blender file.
Setup the project to render the sequence with the requested settings.

Parse the command line arguments for the conversion settings.
NOTE: The actual output settings(ProRes, etc.) will be the command line argument for the scene file
Settings:
  1-Sequence
  2-Resolution
  3-Frame Rate(ex: 100x100)
  4-Where to save blender file
'''

import bpy, os, sys
sys.path.append('/Volumes/theGrill/.qube/Modules/')
import sequenceTools

sys.stdout.write("\nINFO: Blender Loaded, Processing...\n")

args = sys.argv[(sys.argv.index('--')+1):] # Only the arguments after the -- separator
sys.stdout.write("\nArguments: \n\t" + '\n\t'.join(args) + "\n")

try:
    sequence = args[0]
    res = args[1]
    rate = args[2]
    sceneFile = args[3]
except:
    sys.stdout.write("\nInvalid Input Parameters.")

if (rate):
    ''' Load the Image Sequence files from the folder into a dictionary. '''
    sys.stdout.write("INFO: Loading sequence...")
    mySequence = sequenceTools.Sequence(sequence)
    
    '''
    Create an array containing dictionaries for each frame.
    {'name':frameFileName}
    '''
    myFiles = []
    for pathToFrame in mySequence.getFrames():
        myFrame = {'name':os.path.basename(pathToFrame)}
        myFiles.append(myFrame)

    # sys.stdout.write("\n"+str(myFiles)+"\n")

    if (len(myFiles) < 1):
        sys.stdout.write("\nERROR: No sequence files in folder.")
        sys.exit(1)
    else:
        ''' Check for missing frames. '''
        missingFrames = mySequence.getMissingFrames()
        if len(missingFrames) > 0:
            sys.stdout.write("\nERROR: Missing Frames")
            for frame in missingFrames:
                sys.stdout.write("\nMissing Frames: " + frame)
        
        else:
            sys.stdout.write("\nINFO: Sequence loaded!")

            sys.stdout.write("\nINFO: Setting up blender scene...")
    
            # Add the files to an image strip
            bpy.ops.sequencer.image_strip_add( \
                    directory = mySequence.folder, \
                    files = myFiles, \
                    frame_start=0, \
                    channel=1, \
                    filemode=9)

            stripName = myFiles[0].get("name")  # Locate the new image strip
    
            if (len(stripName) > 21): stripName = stripName[0:21]  # Image Strip names are limited to 21 characters
            myscene = bpy.data.scenes[0]
            mystrip = myscene.sequence_editor.sequences[stripName]
            mystrip.use_premultiply = True

            # Set the length of the scene to the length of the sequence
            myscene.frame_end = mystrip.frame_final_duration

            # Apply the settings from the input
            # res = res.split('x')
            # myscene.render.resolution_x = int(res[0])
            # myscene.render.resolution_y = int(res[1])

            # Frame rate is a bit trickier
            # rate = float(rate)
            # if rate == 29.97:
            #     myscene.render.fps = 30
            #     myscene.render.fps_base = 1.001
            # elif rate == 23.98:
            #     myscene.render.fps = 24
            #     myscene.render.fps_base = 1.001
            # else:
            #     myscene.render.fps = int(rate)
            #     myscene.render.fps_base = 1

            # Save the scene for rendering the segments
            bpy.ops.wm.save_mainfile(filepath=sceneFile,compress=True)
            sys.stdout.write("\nINFO: Blender Scene Saved to " + sceneFile + "\n")
    
            sys.stdout.write("\nINFO: Blender Scene Complete!\n")