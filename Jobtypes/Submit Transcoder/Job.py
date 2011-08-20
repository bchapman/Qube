'''
Transcoder Job Class (Model)

Author: Brennan Chapman
Date: 7/12/2011
Version: 1.0

Job model class to store all related information.
'''


class Job:

    def __init__(self):
        ''' Input Settings '''
        self.sequence = ''
        self.audioFile = ''
        self.frameRange = []

        ''' Output Settings '''
        self.outputFile = ''
        self.preset = ''
        self.transcoderFolder = ''

        self.selfContained = True
        self.smartUpdate = True
        self.fillMissingFrames = False

        ''' Other Settings '''
        self.qubejob = {}

    def __str__(self):
        result = 'Job Details:\n'
        for key, value in vars(self).items():
            result += '\t' + str(key) + ': ' + str(value) + '\n'
        return result

    def __repr__(self):
        return self.__str__()
