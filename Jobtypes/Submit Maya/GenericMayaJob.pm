############################################################################
#
#      Copyright: Pipelinefx @ 2006
#
############################################################################
#
# GenericMayaJob.pm
#
############################################################################

local $| = 1;

package maya::GenericMayaJob;

use maya::MayaJob;
use maya::PromptMayaJob;

use qb::Job;

@ISA = qw(maya::PromptMayaJob);


###########################################################################
# Constructors and Object-Initialization Methods
###########################################################################

#
# We'll just inherit the constructor, the new() method, from our base class.
#

#############################################################################
#   Maya Command Control Routines
#############################################################################


#
# initialize()
#
sub initialize
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	$self->SUPER::initialize();

	# load scenefile
	my $retval = $self->mayaLoadScenefile();

	if(not $retval) {
		# Error in loading scenefile
		warn("ERROR: couldn't load scenefile");
# 		qb::reportjob("failed");

	} else {

		# determine which renderer to use
		my $renderer = $self->mayaGetCurrentRenderer();
		warn("INFO: Job submission didn't explicitly specify a renderer.\n");
		warn("INFO: Using the currentRenderer [$renderer] specified in " .
			 "the scene file.\n");
		if ($renderer eq "mayaSoftware" or $renderer eq "sw") {
			bless $self, "maya::SoftwareMayaJob";
# 		} elsif ($renderer eq "mayaHardware" or $renderer eq "hw") {
# 			bless $self, "maya::HardwareMayaJob";
		} elsif ($renderer eq "mayaVector" or $renderer eq "vr") {
			bless $self, "maya::VectorMayaJob";
		} elsif ($renderer eq "mentalRay" or $renderer eq "mr") {
			bless $self, "maya::MentalRayMayaJob";
		} elsif ($renderer eq "turtle") {
			bless $self, "maya::TurtleMayaJob";
		} else {
			warn("ERROR: unsupported renderer [$renderer]");
			$retval = 0;
		}

		if($retval) {
			# setup some render globals
			$self->setupRenderGlobals();
		}
	}

	return $retval;
}


1;

__END__

#
# Legacy code (DELETE ME)
#

sub initializeRenderer
{
	my $self = shift;

	return 0;
}


sub renderMayaFrame
{
	my ($self, $work) = @_;

	my $frame = $work->name();
	my $start = $frame;
	my $end = $frame;


	my $renderCommand = $self->mayaGetRenderCommand();

	$self->_mayaCurrentTime($start);
	$self->_mayaStartFrame($start);
	$self->_mayaEndFrame($end);
	$self->_mayaFrameStep($step);

	$command = sprintf("$renderCommand;");
	my $renderOutput = $self->_mayaCommand($command);

	return $failed;
}

sub mayaGetCameras
{
	my $self = shift;

	my $command = "ls -cameras;";
	my $result = $self->_mayaCommand($command);
	my @cameras = split(/\s+/, $result);

	return @cameras;
}

sub mayaIsRenderableCamera
{
	my ($self, $cam) = @_;

	my $command = "getAttr \"$cam.renderable\";";
	my $result = $self->_mayaCommand($command);

	return $result;
}

sub mayaGetRenderCommand
{
	my ($self, $cam) = @_;
	my $version = $self->getMayaVersion();

	my $cmd;
	if ($version >= 6.0) {
		$cmd = "renderer -query -commandRenderProcedure (currentRenderer());";
	} elsif ($version >= 5.0) {
		$cmd = "renderer -query -renderProcedure (currentRenderer());";
	} else {
		return;
	}

	my $result = $self->_mayaCommand($cmd);

	return $result;
}

sub _mayaCurrentTime
{
    my ($self, $time) = @_;
    my $command = sprintf('currentTime -e %s;', $time);
    $self->_mayaCommand($command);
    return;
}

sub _mayaStartFrame
{
    my ($self, $frame) = @_;

    my $command = sprintf('setAttr defaultRenderGlobals.startFrame %s;',
                          $frame);
    $self->_mayaCommand($command);
    return;
}
sub _mayaEndFrame
{
    my ($self, $frame) = @_;

    my $command = sprintf('setAttr defaultRenderGlobals.endFrame %s;',
                          $frame);
    $self->_mayaCommand($command);
    return;
}    
sub _mayaFrameStep
{
    my ($self, $step) = @_;

    my $command = sprintf('setAttr defaultRenderGlobals.byFrameStep %s;',
                          $step);
    $self->_mayaCommand($command);
    return;
}

1;
