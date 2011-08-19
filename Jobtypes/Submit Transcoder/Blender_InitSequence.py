# Blender Initialize
# Author: Brennan Chapman
# Date: 7/11/2011
'''
Initliaze the transcoder blender file.
Setup the project to render the sequence with the requested settings.

Parse the command line arguments for the conversion settings.
NOTE: The actual output settings(ProRes, etc.) will be the command line argument for the scene file
Settings:
  1-(string) Sequence
  2-(string) Where to save blender file
  3-(boolean) Fill Missing Frames
'''

import bpy, os, sys
import logging

''' Setup the logger. '''
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

try:
    sys.path.append('../../Modules/')
    import sequenceTools
except:
    logger.error('Unable to import sequenceTools')
    sys.exit(7)


def main():
    logger.info("Blender Loaded, Processing...")

    ''' Get the arguments after the '--' separator. '''
    args = sys.argv[(sys.argv.index('--')+1):]
    logger.debug("Arguments: \n\t" + '\n\t'.join(args))

    try:
        sequence = str(args[0])
        sceneFile = str(args[1])
        fillMissingFrames = bool(args[2])
    except:
        logger.error('Invalid Input Parameters.')

    if sequence:
        ''' Load the Image Sequence files from the folder into a dictionary. '''
        logger.info("Loading sequence...")
        mySequence = sequenceTools.Sequence(sequence)

        '''
        Create an array containing dictionaries for each frame.
        {'name':frameFileName}
        '''
        myFiles = []
        for pathToFrame in mySequence.getFrames(fillMissing=fillMissingFrames):
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
                        channel = 2, \
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

                # Save the scene for rendering the segments
                bpy.ops.wm.save_mainfile(filepath=sceneFile,compress=True)
                logger.info('Blender Scene Saved to ' + sceneFile)
    
                logger.info('Blender Scene Complete!')

if __name__ == '__main__':
    main()