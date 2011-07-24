# Convert a string containing a the name of a single image
# in an image sequence to a template string.

import re

def getSequenceTemplate(fileName):
    pattern = re.compile('(.+?)(\d\d+?)(\.\w+)')
    matches = pattern.finditer(fileName)

    name = number = extension = ''
    for match in matches:
        name, number, extension  = match.groups()

    if (name):
        # Convert the digits to # signs
        templateNumbers = ''
        for d in range(0, len(number)):
            templateNumbers += '#'

        # print "Name: " + name
        # print "Number: " + number
        # print "Template: " + templateNumbers
        # print "Extension: " + extension

        return name + templateNumbers + extension
    else:
        return "ERROR: Invalid Sequence"
            
print getSequenceTemplate("/testing/testing.01.png")