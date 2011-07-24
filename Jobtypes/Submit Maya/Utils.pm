###########################################################################
#
#      Copyright: Pipelinefx @ 2006
#
###########################################################################
#
# Utils.pm
#
###########################################################################

package maya::Utils;

use Exporter;
use vars qw(@ISA @EXPORT_OK);
use File::Basename;
use qb;

@ISA = qw(Exporter);
@EXPORT_OK = qw(sceneMayaVersion findMayaExecutable isAbsolutePath
				removeCameraNodeNameFromFilename);

#
# sceneMayaVersion($scenefile)
#
#  Parse the $scenefile for the associated maya version, and return the
#  version number as a string.  Return the null string if not found.
#
sub sceneMayaVersion
{
	my $scenefile = shift;
	my $ver = "";

	my $ret = open FILE, "<$scenefile";
	if(! $ret) {
		warn("WARNING: cannot open scenefile [$scenefile] for reading");
	} else {
		my $buffer;
		while (<FILE>) {
			$buffer .= $_;
			if ($buffer =~ /version.[\" ]*((\d+\.\d+)|(\d+))/) {
				$ver = $1;
				last;
			} elsif (length($buffer) > 1024) {
				# terminate at 1K
				last;
			}
		}
		close FILE;
	}

	return $ver;
}

#
# findMayaExecutable($ver)
#
#  Traverse thru each directory in the execution environment's PATH,
#  and find the maya executable file of version $ver.  $ver should be
#  given as a string.  If $ver is not given, or is the empty string,
#  find the first one in PATH.
#
#  Return the full path to the executable found.
#
#  If no suitable executable can be found, return the bare word "maya"
#  (Unix) or "mayabatch.exe" (Windows).
sub findMayaExecutable
{
	my $ver = shift;

	my $command = "maya";
	my $pathdelim = ":";
	if($^O eq "MSWin32") {
		$command = "mayaBatch.exe";
		$pathdelim = ";";
	}

	my $saveMayaLocationEnv = $ENV{"MAYA_LOCATION"} || "";

	# search thru the PATH set in the execution environment first
	my @paths = split(/$pathdelim/, $ENV{"PATH"});

	# add paths defined explicitly in job.conf
	my $jobconfPaths = qb::jobconfig("maya", "maya_paths", 0);
	if($jobconfPaths) {
		push @paths, split(/,/, $jobconfPaths);
	}

	# add maya paths found in the windows registry (windows only)
	if($^O eq "MSWin32") {
		eval 'use Win32::TieRegistry (Delimiter => "/");';
		my @regpaths = split /,/,
			qb::jobconfig("maya", "installdir_windows_registry_paths", 0);
		for (@regpaths) {
			my $maya_location = $Registry->{$_};
			if ($maya_location) {
				push @paths, $maya_location . "bin";
			}
		}
	}


	# add standard "default" paths-- sort them in reverse order, in hopes
	#  that the newer versions come first in the list...
	push @paths, sort {$b cmp $a}
		glob(join ' ',
			 "/usr/autodesk/maya*/bin",
			 "/usr/aw/maya*/bin",
			 "/Applications/Autodesk/maya*/bin",
			 "/Applications/Alias/maya*/Maya.app/Contents/bin",
			 "/Applications/AliasWavefront/maya*/bin",
			 'C:/Program\ Files/Autodesk/Maya*/bin',
			 'C:/Program\ Files/Alias/Maya*/bin',
			 'C:/Program\ Files (x86)/Alias/Maya*/bin',
			 'C:/Program\ Files/AliasWavefront/Maya*/bin',
			);


	# now search for the executable!
	my $exefile = "";
	my $firstexe = "";
	my %pathChecked = ();
	for(@paths) {
		$_ =~ s/\"//g;
		$_ =~ s/\\$//g;
		$_ =~ s!\\!/!g;		# translate backslashes to forward slashes

		# shortcut to avoid checking same path more than once
		$pathChecked{$_} ? next : ($pathChecked{$_} = 1);

		my $file = "$_/$command";
		if(-x $file and not -d $file) {

			warn("INFO: checking maya executable [$file]\n");

			# save the path to the first found executable
			if(not $firstexe) {
				$firstexe = $file;
			}

			# return the first executable found, if $ver is undefined
			#  or empty.
			if(not defined $ver or $ver eq "") {
				$exefile = $file;
				last;
			}

			# test the executable $file if it's version matches ours

			# make sure we have MAYA_LOCATION set properly
			if ($file !~ m[/usr/(local/)?s?bin/maya]) {
				$ENV{"MAYA_LOCATION"} = dirname(dirname($file));
				warn("INFO: MAYA_LOCATION=" . $ENV{MAYA_LOCATION} . "\n");
			}
			my $tag = `"$file" -batch -v`;
			if($? != 0) {
				my $exitval = $? >> 8;
				my $signum = $? & 127;
				my $coredump = $? & 128;
				warn("ERROR: cannot run '$file -batch -v' to find executable\n".
					 "  exitval=$exitval, signal=$signum, coredump=$coredump");
			}
			chomp $tag;
			$tag =~ s/^.*Maya ((\d+\.\d+)|(\d+)).*,.*/$1/;
			warn("INFO: ver=$tag\n");
			if($tag eq $ver) {
				$exefile = $file;
				last;
			}
		}
	}

	if($exefile eq "") {
		warn("WARNING: Cannot find a maya executable '$command' " .
			 "matching exactly the version [$ver] in your PATH or ".
			 "in any of the system's default locations");
		if($firstexe) {
			warn("INFO: Using first found executable: $firstexe");
			$exefile = $firstexe;
		} else {
			warn("WARNING: In fact, no executable file was found anywhere");
			$exefile = $command;
		}
	}

	# restore MAYA_LOCATION
	$ENV{MAYA_LOCATION} = $saveMayaLocationEnv if $saveMayaLocationEnv;

	return $exefile;
}

#
# isAbsolutePath($dir)
#  Return 1 if $dir is an absolute path starting from "/" (Unix)
#  or from "\\" or "<DriveLetter>:" (such as "C:") (Windows).
#
#  NOTE: Treats "/" and "\" equally on MSWin32 platform.
#
sub isAbsolutePath
{
	my $path = shift;

 	if($^O eq "MSWin32") {
		$path =~ s/\\/\//g;		# convert back-slashes to forward-slashes
		if($path =~ /^[A-Za-z]\:\// or
		   $path =~ /^\/\//) {
			return 1;
		}
	} elsif($path =~ /^\//) {
		return 1;
	}
	return 0;
}

1;


#
# removeCameraNodeNameFromFilename($filename, $camera)
#
#  If the $filename contains the node name of the $camera,
#  such as _${camera}Shape, remove that from the filename.
#
#  Actually renames the file on the filesystem, and returns the new
#  filename.
#
sub removeCameraNodeNameFromFilename
{
	my ($filename, $camera) = @_;

	my $oldfile = $filename;
	return $oldfile if $filename !~ s/_$camera(Shape)*//g;

	rename $oldfile, $filename
		or warn("cannot rename [$oldfile] to [$filename]");
	return $filename;
}

1;

