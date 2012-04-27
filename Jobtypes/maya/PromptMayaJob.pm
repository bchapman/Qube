##############################################################################
#
#      Copyright: PipeLinefx @ 2006
#
##############################################################################
#
# PromptMayaJob.pm -- maya job class for handling prompt mode maya jobs.
#
#  This is an abstract base class, derived from maya::MayaJob , and
#  represents a prompt-mode maya job.  It provides common facilities
#  to aid in the implementation of a concrete maya job subclass, based
#  on maya prompt-mode.
#
##############################################################################
local $| = 1;

package maya::PromptMayaJob;

use File::Path;
use File::Spec;
use maya::MayaJob;
use maya::MelProcessor;

# use Symbol;

# use lib qq($ENV{QBDIR}/types);
# use lib qq($ENV{QBDIR}/api/perl);

# use IPC::Run qw( start pump finish timeout );
use File::Temp;

use qb::Job;

@ISA = qw(maya::MayaJob);

# various timeouts, in seconds
# $MayaJob::MAYA_LAUNCH_TIMEOUT = 2 * 60;
# $MayaJob::MAYA_LOAD_TIMEOUT = 60 * 60;
# $MayaJob::MAYA_COMMAND_TIMEOUT = 60;
# $MayaJob::MAYA_RENDER_TIMEOUT = 125;
# $MayaJob::MAYA_QUIT_TIMEOUT = 20;

# $MayaJob::MAXBYTES = 1024;

# $MayaJob::ERRMISSINGFILE = 128;
# $MayaJob::ERRMAYAPROBLEM = 64;

###########################################################################
# Constructors and Object-Initialization Methods
###########################################################################

#
# We'll just inherit the constructor, the new() method, from our base class.
#


###########################################################################
# Public Accessor Methods
###########################################################################

#
# melprocessor()
#
#  Stores the MelProcessor object.
#
sub melprocessor
{
	my $self = shift;
	$self->{"melprocessor"} = shift if @_;
	return $self->{"melprocessor"};
}


#############################################################################
# Maya Command Control Routines
#############################################################################

#
# initialize()
#
#  Sets up the mel command processor (which starts maya in prompt
#  mode), and also sets up the workspace.
#
#  This method should be called from a derived class' initialize()
#  routine, as in: $self->SUPER::initialize();
#
sub initialize
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	$self->{"outdirs"} = [];

	# initialize the mel processor (which will start "maya -prompt")
	$self->melprocessor(maya::MelProcessor->new());
	$self->melprocessor()->mayaExecutable($self->mayaExecutable());
	$self->melprocessor()->echo(1);

	# setup maya's workspace
	$self->mayaSetupWorkspace();

	# make sure that the output directories are all writable
	warn "INFO: testing output directory permissions\n";
	$self->melexec("workspace -q -rootDirectory");
	my $projdir = $self->melresult();
# 	$self->melexec("workspace -q -renderType");
# 	my %renderDirs = split / /, $self->melresult();
	my %renderDirs = $self->renderDirs();
	for (sort keys %renderDirs) {
		warn "INFO: testing output directory for [$_]\n";
		my $dir = "";
		if (not File::Spec->file_name_is_absolute($renderDirs{$_})) {
			$dir = "$projdir/$renderDirs{$_}";
		} else {
			$dir = $renderDirs{$_};
		}
		push @{$self->{outdirs}}, $dir;
		if (! -d $dir) {
			warn "WARN: output directory [$dir] does not exist... ".
				"attempting to create it...\n";
			eval { mkpath($dir) };
			if($@) {
				warn "ERROR: cannot create output dir [$dir]\n";
				return 0;
			} else {
				warn "INFO: successfully created output dir [$dir]\n";
			}
		}
		my $tmpfile = "$dir/qubetmpfile-$ENV{QBJOBID}-$ENV{QBSUBID}.$$";
		if (not open(FH, ">$tmpfile")) {
			warn "ERROR: outdir [$dir] exists, but is not writable\n";
			warn "	make sure the execution user [" . getlogin() . "] " .
				"has write-permission to this directory\n";
			return 0;
		} else {
			close FH;
			unlink $tmpfile or
				warn "WARNING: cannot unlink tmpfile [$tmpfile]: $!\n";
			warn "INFO: outdir [$dir] exists and is writable\n";
		}
	}

	# workaround for issues with Paint FX
	$self->melexec('if("Unknown" != `whatIs "getStrokes"`) { source "getStrokes"; }');

	return 1;
}

#
# return a hash of render output directories.
#  The hash keys are the "render types" such as "images", "depth", etc.,
#  and the values are the paths
#
sub renderDirs
{
	my $self = shift;
	my %dirs = ();

	# we first get a list of fileRules from the "workspace -q -fileRule"
	# command, then iterate over them to get their values. It has to be done
	# this way, as the names and values are returned as mel arrays, and may
	# contain space characters in them, which melexec() and melresult() aren't
	# capable of returning.
	#

	# option name prefix to the "workspace" command changed in maya 8, from
	# "-renderTypeList" to "-fileRuleList", and "-renderTypeEntry" to
	# "-fileRuleEntry", so we accomodate that here.
	#
	my $frl_optname = ($self->getMayaVersion() >= 8) ? "fileRule" : "renderType";
	my $mel = 'string $frl[] = `workspace -q -' . $frl_optname .'List`; stringArrayToString($frl,",");';
	$self->melexec($mel);
	my @fileRuleList = split /,/, $self->melresult();

	for(@fileRuleList) {
		$self->melexec("workspace -q -${frl_optname}Entry \"$_\"");
		$dirs{$_} = $self->melresult();
	}

	return %dirs;
}

#
# mayaSetupWorkspace()
#
sub mayaSetupWorkspace
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	# set up workspace
	if($self->package->project()) {
		$self->melexec("workspace -o \"".$self->package->project()."\";");
	}

	if (length $self->package->renderDirectory()) {
		$self->melexec("workspace -rt \"images\" \"" .
					   $self->package->renderDirectory()."\"");
	}

	if (length $self->package->iprFile()) {
		$self->melexec("workspace -rt \"iprImages\" \"" .
					   $self->package->iprDirectory()."\"");
	}

	# TODO: return some useful $status?
	# return $status
}

#
# mayaLoadScenefile()
#
sub mayaLoadScenefile
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;
	my $status;

	# load scenefile
	return $self->melexec("file -f -o \"".$self->package->scenefile()."\";",
						  "" # ignore errors
						 );
}

#
# melexec()
#
sub melexec
{
	my $self = shift;
	return $self->melprocessor()->exec(@_);
}

#
# melresult()
#
sub melresult
{
	my $self = shift;
	return $self->melprocessor()->result(@_);
}

#
# finalize()
#
sub finalize
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;
	$self->cleanupTmpfiles();
	$self->melprocessor()->finish(); # quit maya
}

#
#
#
sub cleanupTmpfiles
{
	my $self = shift;
	my @outdirs = @{$self->{outdirs}};
	my @tmpfiles = ();

	for(@outdirs) {
		push @tmpfiles, glob("'$_/qubetmpfile*'" );
	}

	for(@tmpfiles) {
		print "INFO: cleaning up tmpfile [$_]\n";
		unlink or warn "cannot unlink tmpfile [$_]: $!\n";
	}
	return 1;
}

###########################################################################
#
###########################################################################

sub createTempDir
{
	my $self = shift;
	if (not -d $self->tempdir()) {
		my $template = sprintf("%s-tmp.XXXX", $self->prototype());
		my $dir = File::Temp::tempdir( $template, CLEANUP => 1, TMPDIR => 1);
		$self->tempdir($dir);
	}
	return $self->tempdir();
}

sub tempdir
{
	my ($self, $dir) = @_;
	$self->{tempdir} = $dir if @_ > 1;
	return $self->{tempdir};
}

sub cleanupTempDir
{
	my $self = shift;
	return if ((not $self->tempdir()) or (not -e $self->tempdir()));

	File::Path::rmtree($self->tempdir());
}

sub mayaGetCameras
{
	my $self = shift;

	$self->melexec("ls -cameras");
	my $result = $self->melresult();

	my @cameras = split(/\s+/, $result);

	return @cameras;
}

sub mayaIsRenderableCamera
{
	my ($self, $cam) = @_;

	my $command = "getAttr \"$cam.renderable\"";
	$self->melexec($command);

	return $self->melresult();
}

#############################################################################
#   Maya Command Control Routines
#############################################################################

sub quitMaya
{
	my $self = shift;

	# skip this step for now, we're running in batch mode
	return if ($self->package->batchmode());

	my $input = $self->reader();

	${$input} = 'quit -f;';
	$self->harness->finish();

	if ($self->pid() > 0) {
		sleep $MayaJob::MAYA_QUIT_TIMEOUT;
		print STDERR "destroying maya instance\n";
		kill TERM => $self->pid();
	}

	return undef;
}

sub mayaGetCurrentRenderer
{
	my $self = shift;

	my $result = "";
	if($self->getMayaVersion() <= 4.5) {
		$result = "mayaSoftware";
	} else {
		$self->melexec("currentRenderer()");
		$result = $self->melresult();
	}
	return $result;
}

sub getMayaVersion
{
	my $self = shift;
	my $command = "getApplicationVersionAsFloat;";

	$self->melexec($command);

	return $self->melresult();
}

sub cleanupWorkerJob
{
	my $job = shift;

	printf STDERR "\n%s CLEANUP BEGIN %s\n", "=" x 20, "=" x 20;

# 	$job->quitMaya();

	printf STDERR "\n%s CLEANUP END %s\n", "=" x 20, "=" x 20;
}


1;
