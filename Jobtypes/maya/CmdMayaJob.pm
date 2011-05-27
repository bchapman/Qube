###########################################################################
#
#      Copyright: PipeLine FX @ 2006
#
###########################################################################
#
# CmdMayaJob.pm
#
#  Maya jobtype backend for handling command-line batch renders--
#  i.e. "maya -render [options] <scenefile>".
#
###########################################################################

package maya::CmdMayaJob;

use qb::Job;
use maya::MayaJob;
use maya::Utils qw(isAbsolutePath);

@ISA = qw(maya::MayaJob);

#
# processWork($work)
#
#  Process the $work given.  The $work is usually a frame of render.
#  Return 1 if successful, 0 otherwise.
#
sub processWork
{
	my ($self, $work) = @_;

	my $frame = $work->name();
	my $start = $frame;
	my $end = $frame;

# 	my @cmd = ($self->mayaExecutable(), "-render", "-s", $start, "-e", $end,
# 			   $self->_assembleRenderArgList(), $self->package->scenefile());

	# substitute the "maya(Batch.exe)" command with "Render(.exe)"
	my $renderExecutable = $self->mayaExecutable();
	$renderExecutable =~ s/maya(Batch)?(\.exe)?$/Render$2/;

	my @cmd = ($renderExecutable);

	if($self->package->currentRenderer()) {
		my $renderer = $self->package->currentRenderer();
		my @opts = ();
		if($renderer eq "mayaSoftware") {
			$renderer = "sw";
		} elsif($renderer eq  "mentalRay") {
			$renderer = "mr";
			@opts = ("-lic", "ns");
		} elsif($renderer eq "mayaHardware") {
			$renderer = "hw";
		} elsif($renderer eq "mayaVector") {
			$renderer = "vr";
		}
		print "INFO: using renderer [$renderer]\n";
		push @cmd, "-r", $renderer;
		if(@opts) {
			push @cmd, @opts;
		}
	} else {
		print "INFO: renderer not specified... using default\n";
	}

	push @cmd, "-s", $start, "-e", $end, $self->_assembleRenderArgList(),
		$self->package->scenefile();

	# run the command!
	print STDERR "COMMAND: @cmd\n";
	my $ret = system(@cmd);

	if($ret != 0) {
		warn("ERROR: with renderer command: '@cmd'");
		if ($? == -1) {
			warn("ERROR: failed to execute: $!\n");
		} elsif ($? & 127) {
			warn(sprintf("ERROR: child died with signal %d, %s coredump\n",
						 ($? & 127),  ($? & 128) ? 'with' : 'without'));
		} else {
			warn(sprintf("ERROR: child exited with value %d\n", $? >> 8));
		}
	}

	return !$ret;
}

#
# _assembleRenderArgList()
#
#  Assemble the command-line options and arguments to the render
#  command from the package data, and return it as a list.
#
sub _assembleRenderArgList
{
	my $self = shift;
	my $pkg = $self->package();

	my @list;
	push (@list, "-se ", $pkg->startExtension()) 
		if $pkg->startExtension();
	push (@list, "-be", $pkg->byExtension())
		if $pkg->byExtension();
	push (@list, "-pad", $pkg->extensionPadding())
		if $pkg->extensionPadding();
	push (@list, "-proj", $pkg->project())
		if $pkg->project();
	if (length $pkg->renderDirectory()) {
		my $renderDir = $pkg->renderDirectory();
		if (length($pkg->project()) and !isAbsolutePath($renderDir)) {
			$renderDir = $pkg->project()."/".$renderDir;
		}
		push (@list, "-rd", $renderDir);
	}

	push (@list, "-im", $pkg->image())
		if $pkg->image();
	push (@list, "-me", $pkg->mayaExtension())
		if $pkg->mayaExtension();
	push (@list, "-mf", $pkg->mayaFormat())
		if $pkg->mayaFormat();
	push (@list, "-cam", $pkg->cameraOverride())
		if $pkg->cameraOverride();
	push (@list, "-g", $pkg->gamma())
		if $pkg->gamma();
	push (@list, "-ifg", $pkg->ignoreFilmGate())
		if $pkg->ignoreFilmGate();
	push (@list, "-ih", $pkg->imageHeight())
		if $pkg->imageHeight();
	push (@list, "-iw", $pkg->imageWidth())
		if $pkg->imageWidth();
	push (@list, "-ard", $pkg->deviceAspectRatio())
		if $pkg->deviceAspectRatio();
	#	push (@list, "-ar", $pkg->aspectRatio())
	#		if  $pkg->aspectRatio();
	push (@list, "-mm", $pkg->maximumMemory())
		if $pkg->maximumMemory();
	push (@list, "-mb", $pkg->motionBlur())
		if $pkg->motionBlur();
	push (@list, "-mbf", $pkg->motionBlurByFrame())
		if $pkg->motionBlurByFrame();
    push (@list, "-sa", $pkg->shutterAngle())
        if $pkg->shutterAngle();
    push (@list, "-mb2d", $pkg->motionBlur2D())
        if $pkg->motionBlur2D();
    push (@list, "-bll", $pkg->blurLength())
        if $pkg->blurLength();
    push (@list, "-bls", $pkg->blurSharpness())
        if $pkg->blurSharpness();
    push (@list, "-smv", $pkg->smoothValue())
        if $pkg->smoothValue();
    push (@list, "-smc=s", $pkg->smoothColor())
        if $pkg->smoothColor();
    push (@list, "-kmv", $pkg->keepMotionVector())
        if $pkg->keepMotionVector();
    push (@list, "-uf", $pkg->useFileCache())
        if $pkg->useFileCache();
    push (@list, "-oi", $pkg->optimizeInstances())
        if $pkg->optimizeInstances();
    push (@list, "-rut", $pkg->reuseTessellations())
        if $pkg->reuseTessellations();
    push (@list, "-udb", $pkg->useDisplacementBbox())
        if $pkg->useDisplacementBbox();
    push (@list, "-edm", $pkg->enableDepthMaps())
        if $pkg->enableDepthMaps();
    push (@list, "-ert", $pkg->enableRayTrace())
        if $pkg->enableRayTrace();
    push (@list, "-rfl", $pkg->reflections())
        if $pkg->reflections();
    push (@list, "-rfr", $pkg->refractions())
        if $pkg->refractions();
    push (@list, "-rl", $pkg->renderLayers())
        if $pkg->renderLayers();
    push (@list, "-rp", $pkg->renderPasses())
        if $pkg->renderPasses();
    push (@list, "-rs", $pkg->renderSubdirs())
        if $pkg->renderSubdirs();
    push (@list, "-sl", $pkg->shadowLevel())
        if $pkg->shadowLevel();
	#    push (@list, "-eaa", $pkg->edgeAntiAliasing())
	#        if $pkg->edgeAntiAliasing();
    push (@list, "-ufil", $pkg->useFilter())
        if $pkg->useFilter();
    push (@list, "-pft", $pkg->pixelFilterType())
        if $pkg->pixelFilterType();
    push (@list, "-ss", $pkg->shadingSamples())
        if $pkg->shadingSamples();
    push (@list, "-mss", $pkg->maxShadingSamples())
        if $pkg->maxShadingSamples();
    push (@list, "-mvs", $pkg->visibilitySamples())
        if $pkg->visibilitySamples();
    push (@list, "-mvm", $pkg->maxVisibilitySamples())
        if $pkg->maxVisibilitySamples();
    push (@list, "-vs", $pkg->volumeSamples())
        if $pkg->volumeSamples();
    push (@list, "-pss", $pkg->particleSamples())
        if $pkg->particleSamples();
    push (@list, "-rct", $pkg->redThreshold())
        if $pkg->redThreshold();
    push (@list, "-gct", $pkg->greenThreshold())
        if $pkg->greenThreshold();
    push (@list, "-bct", $pkg->blueThreshold())
        if $pkg->blueThreshold();
    push (@list, "-cct", $pkg->coverageThreshold())
        if $pkg->coverageThreshold();
    push (@list, "-of", $pkg->outputFormat())
        if $pkg->outputFormat();
    push (@list, "-sp", $pkg->shadowPass())
        if $pkg->shadowPass();
    push (@list, "-amt") if $pkg->abortOnMissingTexture();
    push (@list, "-rep") if $pkg->dontReplaceRendering();
    push (@list, "-verbose", $pkg->verbose())
        if $pkg->verbose();
    push (@list, "-ipr") if $pkg->iprFile();
    push (@list, "-x", $pkg->xResolution())
        if $pkg->xResolution();
    push (@list, "-y", $pkg->yResolution())
        if $pkg->yResolution();
    push (@list, "-xl", $pkg->xLeft())
        if $pkg->xLeft();
    push (@list, "-xr", $pkg->xRight())
        if $pkg->xRight();
    push (@list, "-yl", $pkg->yLow())
        if $pkg->yLow();
    push (@list, "-yh", $pkg->yHigh())
        if $pkg->yHigh();
    push (@list, "-l", $pkg->displayLayer())
        if $pkg->displayLayer();
    push (@list, "-n", $pkg->numberOfProcessors())
        if $pkg->numberOfProcessors();
	#    push (@list, "-tw", $pkg->tileWidth())
	#        if $pkg->tileWidth();
	#    push (@list, "-th", $pkg->tileHeight())
	#        if $pkg->tileHeight();
    push (@list, "-cont") if $pkg->continue();
    push (@list, "-keepPreImage") if $pkg->keepPreImage();

    return @list;
}


1;
