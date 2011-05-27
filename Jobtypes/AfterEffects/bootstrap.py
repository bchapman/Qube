#!/usr/bin/python 
##################################################################
#  The above lines is dependent upon the location of Python.
##################################################################
#
#  Python bootstrap script
#
##################################################################

# load system libs
import sys, os, os.path
import getopt

# load system path
sys.path.append(".");
sys.path.append("..");
sys.path.append('%s/api/python' % os.environ.get('QB_DIR'))
sys.path.append('%s/api/python' % os.environ.get('QBDIR'))

sys.path.append("/Applications/pfx/qube/api/python/")
#load qube libs
import qb

def main():
        options = 'h'
        longOptions = ['archive=',
                       'backend=',
                       'base=',
                       'frontend=',
                       'help',
                       'type=']
        opts, pargs = getopt.getopt(sys.argv[1:], options, longOptions)

        # obtain input job
        archive = "job.qja"
        base = '.'
        frontend = ''
        backend = "execute.py"
        type = ''
        
        for opt in opts:
                if opt[0] == '--archive':
                        archive = opt[1]
                if opt[0] == '--base':
                        base = opt[1]
                elif opt[0] == '--backend':
                        backend = opt[1]
                elif opt[0] == '--frontend':
                        frontend = opt[1]
                elif opt[0] == '--type':
                        type = opt[1]
                elif opt[0] == '--help' or opt[0] == '-h':
                        usage()
                        return
        if type != '':
                archive = os.path.join(base, type, archive)
                backend = os.path.join(base, type, backend)
        else:
                archive = os.path.join(base, archive)
                backend = os.path.join(base, backend)
                
        if not os.path.exists(backend):
                print 'ERROR: backend %s not found' % backend
                sys.exit(1)

        # output the archive
        print 'executing %s...' % frontend
        os.system(frontend)

        if not os.path.exists(archive):
                print 'ERROR: archive %s not found' % archive
                sys.exit(1)
        
        # setup development env
        qb._setjob(archive)

        # launch execution script
        print "INFO: bootstrap script loading execute module\n"
        execfile(backend, globals())

def usage():
        print 'bootstrap.py [options]'
        print 'where [options] are:'
        print '\t--archive <archive>  : path to existing job archive (job.xja)'
        print '\t--backend <backend>  : path to backend (execute.py)'
        print '\t--base <path>        : path to type directory'
        print '\t--frontend <command> : frontend command to create job submission archive  (None)'
        print '\t--type <type>        : type name'
        print '\t-h|--help            : usage message'
        return

if __name__ == '__main__':
        main()


