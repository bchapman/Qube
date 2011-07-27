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
  (5-Audio File)
'''

import bpy, os, sys
import logging

sys.path.append('/Volumes/theGrill/.qube/Modules/')
import sequenceTools

'''
Set up the logging module.
'''
logger = logging.getLogger("main")
ch = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)
# logger.setLevel(logging.DEBUG)
# ch.setLevel(logging.DEBUG)

def main():
    logger.info("Blender Loaded, Processing...")

    ''' Get the arguments after the '--' separator. '''
    args = sys.argv[(sys.argv.index('--')+1):]
    logger.info("Arguments: \n\t" + '\n\t'.join(args))

    try:
        sequence = args[0]
        res = args[1]
        rate = args[2]
        sceneFile = args[3]
        if len(args) > 4:
            audioFile = args[4]
        else:
            logger.info('No Audio File Supplied.')
            audioFile = None
    except:
        logger.error('Invalid Input Parameters.')

    if (rate):
        ''' Load the Image Sequence files from the folder into a dictionary. '''
        logger.info("Loading sequence...")
        mySequence = sequenceTools.Sequence(sequence)
    
        '''
        Create an array containing dictionaries for each frame.
        {'name':frameFileName}
        '''
        myFiles = []
        for pathToFrame in mySequence.getFrames():
            myFrame = {'name':os.path.basename(pathToFrame)}
            myFiles.append(myFrame)

        logger.debug('Image Sequence File List: ' + str(myFiles))

        if (len(myFiles) < 1):
            logger.error('No sequence files in folder.')
            sys.exit(1)
        else:
            ''' Check for missing frames. '''
            missingFrames = mySequence.getMissingFrames()
            if len(missingFrames) > 0:
                logger.error('Missing Frames')
                for frame in missingFrames:
                    logger.error('Missing Frames: ' + frame)
        
            else:
                logger.info('Sequence loaded!')

                logger.info('Setting up blender scene...')
    
                ''' Setup an Image Strip for the input image sequence. '''
                bpy.ops.sequencer.image_strip_add( \
                        directory = mySequence.folder, \
                        files = myFiles, \
                        frame_start = 0, \
                        channel = 1, \
                        filemode = 9)

                '''
                Check the premultiply checkbox so the alpha
                from the image sequence to show up properly on the quicktime.
                '''
                myscene = bpy.data.scenes[0]
                stripName = myFiles[0].get("name")
                if (len(stripName) > 21): stripName = stripName[0:21]  # Image Strip names are limited to 21 characters
                mystrip = myscene.sequence_editor.sequences[stripName]
                mystrip.use_premultiply = True 

                ''' Set the length of the scene to the length of the sequence. '''
                myscene.frame_end = mystrip.frame_final_duration


                ''' If an audio file was supplied, add a sound track strip. '''
                if audioFile:
                    if os.path.exists(audioFile):
                        bpy.ops.sequencer.sound_strip_add( \
                                filepath = audioFile, \
                                filemode = 9, \
                                channel = 0, \
                                frame_start = 0)

                # Save the scene for rendering the segments
                bpy.ops.wm.save_mainfile(filepath=sceneFile,compress=True)
                logger.info('Blender Scene Saved to ' + sceneFile)
    
                logger.info('Blender Scene Complete!')

if __name__ == '__main__':
    main()