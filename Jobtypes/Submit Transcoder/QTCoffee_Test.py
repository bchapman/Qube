'''
Compile all of the segments together into one movie

----------------------------------------
catmovie
----------------------------------------
Usage: catmovie [global options] filename1 [file specific options] [filename2 [file specific options] ... ]
Flags:
    -self-contained
    -no-fast-start    When used in conjunction with -self-contained, does not
        make the movie fast-start (quicker, and takes less disk space).
    -no-compressed-header When used in conjuction with -self-contained, does not
        compress the movie header.
    -names-from-stdin File names will be read from standard input instead of 
        the command line, one file per line.
    -o filename       Output to the specified file (defaults to 
        ~/Desktop/out.mov or ~/Desktop/out.mp4).
    -                 Terminate option processing (including file specific 
        options). All other arguments are filenames.
Global or file specific options:
These options are global if they appear before any filenames and local if they
appear after a filename.
    -noresolve        Don't try to look for data in external files; helpful 
        when trying to use reference movies some of whose original files have 
        disappeared.
    -list             List the names of the tracks in the movie.
    -chaplist         List the names of the chapters in the movie.

Time Trials:
52sec 1GB with -self-contained
52sec 1GB with -self-contained -no-fast-start
50sec 1GB with -self-contained -no-fast-start -no-compressed-headers
52sec 1GB with -self-contained -no-compressed-headers
= no difference = just used -self-contained
'''
catmovie -self-contained audioFile -track "Sound Track" -o outputFile -names-from-stdin