import sys

print sys.argv
args = sys.argv[(sys.argv.index('--')+1):]
print args