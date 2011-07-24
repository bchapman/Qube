# Blender Initialize
# Author: Brennan Chapman
# Date: 7/11/2011
#
# Initliaze the transcoder blender file.
# Setup the project to render the sequence with the requested settings.


import bpy, os, sys

# Parse the command line arguments for the conversion settings
# NOTE: The actual output settings(ProRes, etc.) will be the command line argument for the scene file
# Settings:
#   1-Sequence Folder
#   2-Output File
#   3-Resolution
#   4-Frame Rate(ex: 100x100)
#   5-Where to save blender file

version = 1.0
sys.stdout.write("\nBlender_Initiliaze.py - Version " + str(version) + "\n")

args = sys.argv[(sys.argv.index('--')+1):] # Only the arguments after the -- separator
sys.stdout.write("\nArguments: \n\t" + '\n\t'.join(args) + "\n")

try:
    seqFolder = args[0]
    outFile = args[1]
    res = args[2]
    rate = args[3]
    sceneFile = args[4]
except:
    sys.stdout.write("\nInvalid Input Parameters.")

if (rate):
    # Load the Image Sequence files from the folder into a dictionary
    sys.stdout.write("INFO: Loading sequence...")
    myfiles=[]
    for i in os.listdir(seqFolder):
        # If there are files, make sure they are images
        if (i != None and i.endswith(('.jpg','.jpeg','.png','.tga','.gif','.tiff','.exr','.iff','.dpx'))):
            frame={"name":i}
            myfiles.append(frame)

    if (len(myfiles) < 1):
        sys.stdout.write("\nERROR: No sequences in folder.")
        sys.exit(1)
        
    sys.stdout.write("\nINFO: Sequence loaded!")

    sys.stdout.write("\nINFO: Setting up blender scene...")
    # Add the files to an image strip
    bpy.ops.sequencer.image_strip_add( \
            directory = seqFolder, \
            files = myfiles, \
            frame_start=0, \
            channel=1, \
            filemode=9)

    # Locate the new image strip
    stripName = myfiles[0].get("name")
    # Image Strip names are limited to 21 characters
    if (len(stripName) > 21): stripName = stripName[0:21]
    mystrip = bpy.data.scenes[0].sequence_editor.sequences[stripName]

    myscene = bpy.data.scenes[0]

    # Set the length of the scene to the length of the sequence
    myscene.frame_end = mystrip.frame_final_duration

    # Apply the settings from the input
    res = res.split('x')
    myscene.render.resolution_x = int(res[0])
    myscene.render.resolution_y = int(res[1])
    myscene.render.filepath = outFile

    # Frame rate is a bit trickier
    rate = float(rate)
    if rate == 29.97:
        myscene.render.fps = 30
        myscene.render.fps_base = 1.001
    elif rate == 23.98:
        myscene.render.fps = 24
        myscene.render.fps_base = 1.001
    else:
        myscene.render.fps = int(rate)
        myscene.render.fps_base = 1


    # Save the scene for rendering the segments
    bpy.ops.wm.save_mainfile(filepath=sceneFile,compress=True)
    sys.stdout.write("\nINFO: Blender Scene Saved to " + sceneFile + "\n")
    
    sys.stdout.write("\nInitlialization Complete!\n")

    # Render
    # bpy.ops.render.render(animation=True)