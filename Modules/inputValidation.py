'''
Input Validation Module
Author: Brennan Chapman

Set of tools to check for errors with input values.
'''

import os
import logging

''' Setup the logger. '''
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def validateFile(filepath, required=True, expand=True, checkExist=True):
    '''
    Input is a files path.
    Returns either the original or an expanded path as a string.

    required
        Throws an error if input doesn't have a value.
    expand
        Converts the path to an absolute location.
        Turns path variables into their absolutes.
    checkExist
        Checks if the file exists.
    '''
    
    filepath = str(filepath)
    
    logger.debug("validateFile")
    logger.debug("Input: " + filepath)
    logger.debug("Parameters: " + str(locals().items()))
    
    result = ''
    if required and filepath == '':
        raise ValueError('No file path supplied.')
    
    if expand:
        result = os.path.expandvars(filepath)
        result = os.path.expanduser(result)
        if result != filepath:
            logger.debug("Expanded Path: " + result)
    else:
        result = filepath
    
    if checkExist and not os.path.exists(result):
        raise IOError('Input file path doesn\'t exist. ' + str(result))
    else:
        logger.debug('Input file path exists. ' + str(result))
    
    return result
        

def validateFolder(folderpath, required=True, expand=True, checkExist=True, createDirectories=True):
    '''
    Input is a folder path.
    Returns either the original or an expanded path as a string.
    
    required
        Throws an error if input doesn't have a value.
    checkExist
        Checks if the folder exists
    createDirectories
        If not, creates the the directory and any intermediates.
    expand
        Convers the path to an absolute location.
        Turns path variables into their absolutes.
    '''
    
    folderpath = str(folderpath)
    
    logger.debug("validateFolder")
    logger.debug("Input: " + folderpath)
    logger.debug("Parameters: " + str(locals().items()))
    
    result = ''
    if required and folderpath == '':
        raise ValueError('No folder path supplied.')
        
    if expand:
        result = os.path.expandvars(folderpath)
        result = os.path.expanduser(result)
        if result != folderpath:
            logger.debug("Expanded Path: " + result)
    else:
        result = filepath

    if checkExist and not os.path.exists(result):
        if createDirectories:
            os.makedirs(result)
        else:
            raise IOError('Input folder path doesn\'t exist. ' + str(result))
    else:
        logger.debug('Input folder path exists. ' + str(result))
        
    return result
    
def validateString(inputString, required=True):
    '''
    Input is a string.
    Returns the input cast as a string.
    required
        Throws an error if input doesn't have a value.
    '''
    
    inputString = str(inputString)
    
    logger.debug("validateFolder")
    logger.debug("Input: " + folderpath)
    logger.debug("Parameters: " + str(locals().items()))
    
    if required and inputString == '':
        raise ValueError('No input string supplied.')

    return inputString