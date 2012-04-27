###########################################################################
#
#      Copyright: Pipelinefx @ 2002-2006
#
###########################################################################
#
# MayaJob.pm -- Job.pm subclass for handling Maya job types
#
#  This is the base class for all other maya jobtype *MayaJob classes.
#  It's an abstract base class, meant to be subclassed.
#
###########################################################################

package maya::MayaJob;

use Data::Dumper;
use qb::Job;
use maya::Package;
use maya::Utils qw(sceneMayaVersion findMayaExecutable);

use vars qw(@ISA);
@ISA = qw(qb::Job);

# $MayaJob::MAYA_LAUNCH_TIMEOUT = 2 * 60;
# $MayaJob::MAYA_LOAD_TIMEOUT = 60 * 60;
# $MayaJob::MAYA_COMMAND_TIMEOUT = 60;
# $MayaJob::MAYA_RENDER_TIMEOUT = 125;
# $MayaJob::MAYA_QUIT_TIMEOUT = 20;
# $MayaJob::MAXBYTES = 1024;

# $MayaJob::ERRMISSINGFILE = 128;
# $MayaJob::ERRMAYAPROBLEM = 64;

$WAITINGTIMEOUT = 30;

#
# handleFrameTimeout()
#
#  handles frame timeout, which is presently implemented using the
#  ALRM signal.  It is very lacking in features, and bluntly reports
#  to the supe that the entire job has "failed", and dies.
#
#### UNUSED-- probably should be removed
sub handleFrameTimeout
{
	print STDERR "ERROR: frame has timed out...reporting failure\n";
	qb::reportjob("failed");
	die("ERROR: frame has timed out... reported failure and aborting\n");
}

###########################################################################
# Constructors and Object-Initialization Methods
###########################################################################

#
# We'll just inherit the constructor, the new() method, from our base
# class, qb::Job .
#

#
# _instantiate()
#
#  This method is automatically called when
#  qb::jobobj("maya::MayaJob") is called.
#
sub _instantiate
{
	my $self = shift;
	$self->blessPackage("maya::Package");
	$self->blessCallbacks("Callbacks");
}

###########################################################################
# Public Accessor Methods
###########################################################################

#
# mayaExecutable()
#
#  Stores location of the maya executable file.
#
sub mayaExecutable
{
	my $self = shift;
	$self->{"mayaExecutable"} = shift if @_;
	return $self->{"mayaExecutable"};
}

###########################################################################
# Job control methods
###########################################################################

###########################################################################
#
# Concrete subclasses of maya::MayaJob must/can implement the methods
# described below.  These methods will be called by this class'
# (maya::MayaJob) run() method.
#
#==========================================================================
#  sub initialize($self) [OPTIONAL]
#
#   An optional routine that initializes the job.  For example, it
#   should launch Maya, setup renderGlobals, etc.  It must return true
#   to indicate success, false otherwise.
#
#==========================================================================
#  sub processWork($self, $work) [REQUIRED]
#
#   A routine that processes a single work (usually a frame) given.
#   It should return 1 if successful, 0 otherwise.
#
#==========================================================================
#  sub finalize($self) [OPTIONAL]
#
#   An optional routine that does finalization or cleanup of the job,
#   such as quitting Maya gracefully, and/or removing temporary
#   files. It must return true to indicate success, false otherwise.
#
###########################################################################

#
# initialize()
#
sub initialize
{
	return 1;				   # need to return 1 to indicate success
}

#
# finalize()
#
sub finalize
{
	return 1;				   # need to return 1 to indicate success
}

#
# isReadable($file)
#
# This routine was implemented since the code "! -r $scenefile" doesn't
# necessarily return an expected value in Windows.
#
sub isReadable
{
	my $filename = shift;
	my $ret = open FILE, "<$filename";
	if($ret) {
		close FILE;
	}
	return $ret;
}

#
# run()
#
#  Run the job, and return the status, such as "complete", "failed",
#  "pending" (for preempted jobs), etc.
#
sub run
{
	my $self = shift;

	# print some job info
	$self->printJobInfo();

	# make sure scenefile is readable
	my $scenefile = $self->package->scenefile() || "";
	if($scenefile) {
		if(! -e $scenefile) {
			warn("ERROR: scenefile [$scenefile] does not exist on the " .
				 "execution machine [" . hostname() . "]");
			return "failed";
		} elsif( ! isReadable($scenefile)) {
			warn "ERROR: scenefile [$scenefile] exists, but cannot be read\n";
			warn "  make sure that the execution user [" . getlogin() . "] ".
				"has read-permission to the scenefile on the execution ".
					"machine [" . hostname() . "]";
			return "failed";
		} else {
			warn "INFO: scenefile [$scenefile] exists and is readable\n";
		}
	}

	# figure out the version number of Maya we'll be using
	my $ver = "";
	if ($self->package->mayaVersion()) {
		$ver = $self->package->mayaVersion();
	} elsif ($self->package->scenefile()) {
		$ver = sceneMayaVersion($self->package->scenefile());
		print STDERR "Scene File Maya Version: $ver\n";
	}

	# find the appropriate maya executable and store its path
	if($self->package->{mayaExecutable}) {
		$self->mayaExecutable($self->package->{mayaExecutable});
		print STDERR "INFO: Using maya executable specified in submission\n";
		print STDERR "  [" . $self->mayaExecutable() . "]\n";
	} else {
		print STDERR "INFO: Searching for suitable maya executable...\n";
		$self->mayaExecutable(findMayaExecutable($ver));
	}
	print STDERR "Maya Binary: " . $self->mayaExecutable() . "\n";

	# initialize the job
	if(!$self->initialize()) { #### this must be implemented in subclass
		warn("ERROR: in initializing job");
		return "failed";
	}

	# process the worklist
	my ($status, $successcount, $failcount) = $self->processWorklist();
	if($successcount) {
		warn("INFO: [$successcount] agenda items succeeded\n");
	}
	if($failcount) {
		warn("WARN: [$failcount] agenda items failed\n");
	}

	# finalize the job
	if(!$self->finalize()) { #### this must be implemented in subclass
		warn("ERROR: in finalizing job");
		return "failed";
	}

	return $status;
}

#
# printJobInfo()
#
sub printJobInfo
{
	my $self = shift;
	printf STDERR "\n%s INIT BEGIN %s\n", "=" x 20, "=" x 20;

	print STDERR "HOME: ".($ENV{HOME} || "")."\n";
	print STDERR "QBDIR: ".($ENV{QBDIR} || "")."\n";
	print STDERR "MAYA_LOCATION: ".($ENV{MAYA_LOCATION} || "")."\n";
	print STDERR "MAYA_PLUG_IN_PATH: ".($ENV{MAYA_PLUG_IN_PATH} || "")."\n";
	print STDERR "MAYA_SCRIPT_PATH: ".($ENV{MAYA_SCRIPT_PATH} || "")."\n";

	print STDERR "\n";

	# print globals (stored in "package" variable)

	if ($self->package->project()) {
		printf STDERR "Project Directory: %s\n", $self->package->project();
	}
	if ($self->package->renderDirectory()) {
		printf STDERR "Render Directory:  %s\n",
			$self->package->renderDirectory();
	}
	if ($self->package->scenefile()) {
		printf STDERR "Scene File:        %s\n", $self->package->scenefile();
	}
	if ($self->package->image()) {
		printf STDERR "Image Name:        %s.%s.%s\n", $self->package->image(),
			"#" x ($self->package->extensionPadding()),
				$self->package->outputFormat();
	}
	if ($self->package->xResolution() and $self->package->yResolution()) {
		printf STDERR "Resolution:        %sx%s\n",
			$self->package->xResolution(),
				$self->package->yResolution();
	}
	if (defined $self->package->cameraOverride()) {
		printf STDERR "Cameras:            %s\n",
			ref($self->package->cameraOverride()) ?
				join(" ", @{$self->package->cameraOverride()})
					: $self->package()->cameraOverride();
	}

	local $Data::Dumper::Indent = 1;
	print STDERR "\n" . Dumper($self->package) . "\n";
}

#
# processWorklist()
#
#  Loop through the worklist, and process each of the items.  Return
#  the overall subjob status (such as "complete", "failed",
#  "pending"), the number of successfully processed work items, and
#  the number of failed items, as an list.
#
sub processWorklist
{
	my $self = shift;
	my $successCount = 0;
	my $failCount = 0;
	my $subjobstatus = "complete";

	printf STDERR "\n%s WORK START %s\n", "=" x 20, "=" x 20;

	while (1) {
		my $gotfatal = 0;
		# request for next available work from supe
		my $work = qb::requestwork();
		bless($work->package(), "maya::Package") if $work->package();

		# for some reason, I cannot modify $work (I get an error message like:
		# "Modification of non-creatable hash value attempted, subscript
		# "package" at C:\Program Files\pfx\jobtypes/maya/MayaJob.pm line 279.")
		# so I duplicate the $work to $newwork, and use that to pass onto
		# processWork();

		my $newwork = qb::Work->new();
		$newwork->name($work->name());
		$newwork->subid($work->subid());
		$newwork->pid($work->pid());
		$newwork->host($work->host());
		$newwork->status($work->status());
		$newwork->package($work->package());
		bless($newwork->package(), "maya::Package");

		# handle the status from the supervisor
		local $_ = $work->status();
		if(/^complete|pending|blocked$/) {
			$subjobstatus = $_;
			last;
		} elsif(/^waiting$/) {
			sleep $WAITINGTIMEOUT;
			next;
		};

		# otherwise, ($status is "running")-- we process it!

		printf STDERR "\n%s START FRAME #%04d %s\n", "=" x 20,
			$work->name(), "=" x 20;

 		my $frameTimeout = $self->package->frameTimeout() || 0;

		# do a maximum of "maxPasses" tries
		my $maxPasses = $self->package->maxPasses() || 1;
		my $pass;
		my $retval = 0;
		my $retryFrame = 0;
		for ($pass = 0; $pass < $maxPasses; $pass++) {
			if ($pass > 0) {
				printf STDERR "\n%s RETRY(" . $pass + 1 .
					") FRAME #%04d %s\n", "=" x 20,	$work->name(), "=" x 20;
			}
			if($frameTimeout) {
				$SIG{ALRM} = \&handleAlarm;
				alarm($self->package->frameTimeout());
			}

			# fatal errors can raise exceptions, so we "eval()" here.
			eval {
				# processWork() must be implemented in concrete subclasses
				$retval = $self->processWork($newwork);
			};
			if($@) {
				my $x = $@;	# save $@ in case another exception occurs
				warn("ERROR: Exception caught!-- $x\n" .
					 "Reporting failure of subjob to supe");

				$retval = 0;
				$retryFrame = 1;
				$gotfatal = 1;
				last;
			}

			if($frameTimeout) {
				$SIG{ALRM} = "IGNORE";
				alarm(0);
			}

			# break out of loop if the work processed successfully
			last if $retval;
		}

		if ($pass >= $maxPasses) {
			use Sys::Hostname;
			$retval = 0;
			warn("WARNING: maximum tries of $maxPasses exhausted...");
			warn("WARNING: ...subjob bailing...\n");
			$gotfatal = 1;
		}

		if ($retval==1) {
			printf STDERR "\n%s DONE FRAME #%04d %s\n", "=" x 20,
				$work->name(), "=" x 20;
			$newwork->status("complete");
			$successCount++;
# 		} elsif ( ($retval==0) and ($retryFrame==1) ) {
# 			printf STDERR "\n%s RETRYING FRAME #%04d %s\n", "=" x 20,
# 				$work->name(), "=" x 20;
# 			$newwork->status("pending");
		} else {
			printf STDERR "\n%s FAIL FRAME #%04d %s\n", "=" x 20,
				$work->name(), "=" x 20;
			$newwork->status("failed");
			$failCount++;
		}

		warn "Reporting frame status to supe:\n";
		local $Data::Dumper::Indent = 1;
		print STDERR "\n" . Dumper($newwork) . "\n";

		qb::reportwork($newwork);

		# we hit a fatal error, so bail immediately
		if($gotfatal) {
			$subjobstatus = "failed";
			last;
		}
	}

	printf STDERR "\n%s WORK END %s\n", "=" x 20, "=" x 20;

	# we mark the subjob "failed", if any of the frames failed
	if($failCount) {
		$subjobstatus = "failed";
	}
	return ($subjobstatus, $successCount, $failCount);
}


#
# handleAlarm()
#### TODO: frame timeout is tricky...
#
sub handleAlarm
{
	print STDERR "frame has timed out... exiting and reporting a failure\n";
	qb::reportjob("failed");

	#### TODO: we should ideally do a reportwork() here.

	exit(1);
}

1;

