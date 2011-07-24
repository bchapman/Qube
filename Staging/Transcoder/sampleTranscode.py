# Sample Transcode to test the import and render process

import bpy, os, sys


# Open the template scene
# templateScene = "/Volumes/theGrill/.qube/Staging/Transcoder/Presets/ProRes4444_RGBA.blend"
# bpy.ops.wm.open_mainfile(filepath=templateScene)


dir="/Users/bchapman/Projects/Scripts+Apps/Qube/Compressor/Testing/blindnessIS"

# Load the Image Sequence files into a dictionary
file=[]
for i in os.listdir(dir):
    frame={"name":i}
    file.append(frame)

# Add the files into an image strip
bpy.ops.sequencer.image_strip_add( \
        directory = dir, \
        files = file, \
        frame_start=0, \
        channel=2, \
        filemode=9)

# Locate the sequence
mystrip = bpy.data.scenes[0].sequence_editor.sequences[file[0].get("name")]

# Set the length of the scene to the length of the sequence
bpy.data.scenes[0].frame_end = mystrip.frame_final_duration

# Set the output file
bpy.data.scenes[0].render.filepath = "/tmp/output.mov"

sys.stdout.write(str(sys.argv))

# Render
# bpy.ops.render.render(animation=True)