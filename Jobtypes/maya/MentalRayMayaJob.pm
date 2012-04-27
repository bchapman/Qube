###########################################################################
#
#      Copyright: Pipelinefx @ 2002-2006
#
###########################################################################
#
# MentalRayMayaJob.pm
#
###########################################################################

local $| = 1;

package maya::MentalRayMayaJob;

use File::Path;
use maya::MayaJob;
use maya::PromptMayaJob;

# use lib qq($ENV{QBDIR}/types);
# use lib qq($ENV{QBDIR}/api/perl);

use File::Temp;

use qb::Job;
use maya::Utils qw(removeCameraNodeNameFromFilename);

@ISA = qw(maya::PromptMayaJob);

# $MayaJob::MAYA_LAUNCH_TIMEOUT = 2 * 60;
# $MayaJob::MAYA_LOAD_TIMEOUT = 60 * 60;
# $MayaJob::MAYA_COMMAND_TIMEOUT = 60;
# $MayaJob::MAYA_RENDER_TIMEOUT = 125;
# $MayaJob::MAYA_QUIT_TIMEOUT = 20;
# $MayaJob::MAXBYTES = 1024;

# $MayaJob::ERRMISSINGFILE = 128;
# $MayaJob::ERRMAYAPROBLEM = 64;

$maya::MentalRayMayaJob::VERBOSELEVEL = 5;

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
		# setup some render globals
		$self->setupRenderGlobals();
	}
	return $retval;
}

#
# processWork($work)
#
#  Process the $work given.  The $work is usually a frame of render.
#  Return 1 if successful, 0 otherwise.
#
sub processWork
{
	print STDERR (caller 0)[3] . "\n";
	my $self = shift;
	my $work = shift;

	my $minFileSize = $self->{package}->{minFileSize} || 1024;
	my $frame = $work->name();

	$self->melexec("currentTime -e $frame");
	$self->melexec("setAttr defaultRenderGlobals.startFrame $frame");
	$self->melexec("setAttr defaultRenderGlobals.endFrame $frame");
	$self->melexec("setAttr defaultRenderGlobals.byFrameStep 1");
    $self->melexec("setAttr mentalrayGlobals.startFrame $frame");
    $self->melexec("setAttr mentalrayGlobals.endFrame $frame");

    my $cameraArray = [];

	my @sceneCameras = $self->mayaGetCameras();
	if (defined($self->package->cameraOverride())) {
		$cameraArray = ref($self->package->cameraOverride())
			? $self->package->cameraOverride() 
				: [$self->package->cameraOverride()];
	} elsif (length($work->package->cameraOverride()) > 0) {
		$cameraArray = ref($work->package->cameraOverride())
			? $work->package->cameraOverride()
				: [$work->package->cameraOverride()];
	} else {
		# use all renderable cameras in the scene
		foreach my $camera (@sceneCameras) {
			push (@{$cameraArray}, $camera)
				if ($self->mayaIsRenderableCamera($camera));
		}
	}

	my $retval = 1;

	#
	# Mayatomr will render every renderable camera, so we'll turn on
	# only the ones that we want.  This differs from the SW renderer,
	# the "render" mel command.
	#

    # turn off all the cameras
    foreach my $camera (@sceneCameras) {
        $self->melexec("setAttr $camera.renderable 0");
    }

    # turn on all the specified cameras
    foreach my $camera (@$cameraArray) {
        $self->melexec("setAttr $camera.renderable 1");
    }

#     $self->_mayaCurrentTime($frame);
#     $self->_mayaStartFrame($frame);
#     $self->_mayaEndFrame($frame);

    #
    #  Marking the renderGlobals as dirty so that mental ray doesn't
    #  try to do all of the frames.
	#
    $self->melexec("checkDefaultRenderGlobals -changed true;");
    $self->melexec("setAttr mentalrayGlobals.animationFromMaya 1;");

	my $cmd;
    if($self->getMayaVersion() >= 6.5) {
         $cmd = sprintf("Mayatomr -lic ns -render -v %d;",
						$maya::MentalRayMayaJob::VERBOSELEVEL);
    } else {
         $cmd = sprintf("Mayatomr -render -v %d;",
						$maya::MentalRayMayaJob::VERBOSELEVEL);
    }

	$retval = $self->melexec($cmd, undef,
							 'writing image file (.*) \(frame \d+\)');

	# $result should contain the full-path to the rendered image file.
	my $result = $self->melresult();

	# save the result into the resultpackage variable "outputPaths" in
	# the $work, in order to report back to the supe
	$work->resultpackage({"outputPaths" => $result});

	my $framePath;
	if ( defined $self->package()->imageTemplate() ) {
		$framePath = $self->getFramePath($frame);
	} else {
		warn("WARNING: \'imageTemplate\' not defined at front-end, assuming \n\n\t$result\n\n");
		$framePath = $result;
	}

	if ($retval) {
		# check existence of file
		if ($framePath and (not $self->isFrameExists($framePath))) {
			warn("ERROR: file doesn't exist [$framePath]");
			$retval = 0;
		}

		# check the filesize for at least "badFrameSize" bytes
		if ($framePath and
			(not $self->isFrameBigEnough($framePath, $minFileSize))) {
			warn("ERROR: filesize too small [$framePath ($size bytes)]");
			$retval = 0;
		}
	#### <LEGACY parsing code>
#     my $renderOutput = $self->melexec($command, 
# 									  $MayaJob::MAYA_COMMAND_TIMEOUT, 
# 									  join("[mel:]*", split(//, "(: rendering finished|mel:)")),
# 									  join("[mel:]*", split(//, "(Finished Rendering|writing image file)")),
# 									  2		
#     );

#     $renderOutput =~ s/\s+\([^\)]*\)[mel:]*$//g;
#     $renderOutput = $self->_fixFrameName($renderOutput);
	#### </LEGACY parsing code>

# 	my $fixed = $result;
# 	$fixed =~ s/\s+\([^\)]*\)[mel:]*$//g;
# 	$fixed = $self->_fixFrameName($fixed);

# 	print STDERR ">>>> result=$result\n";
# 	print STDERR ">>>>  fixed=$fixed\n";

# 	if($retval) {
		# We skip all the following tests, as mentalray garbles or
		# delays its output to stdout and stderr, and we cannot
		# reliably get the resulting image files name in $result.

# 		if($^O ne "MSWin32") {
# 			# get rid of camera node name from the image file name
# 			if (scalar(@$cameraArray) == 1) {
# 				my $camera = $cameraArray->[0];
# 				my $newname = removeCameraNodeNameFromFilename($result, $camera);
# 				if ($result ne $newname) {
# 					print STDERR "Renamed to: $newname\n";
# 					$result = $newname;
# 				}
# 			}

# 			#     return $self->validateFrame($renderOutput);

# 			# check existence of file
# 			if (!-e $result) {
# 				warn("ERROR: file doesn't exist [$result]");
# 				$retval = 0;
# 			}

# 		# check the filesize for at least "badFrameSize" bytes
# 			if ($self->package->badFrameSize() and
# 				(-s $result <= $self->package->badFrameSize())) {
# 				warn("ERROR: filesize too small [$result ($size bytes)]");
# 				$retval = 0;
# 			}
# 		}

	} else {
		warn("There was an error processing this frame: [". $framePath ."]");
	}

	return $retval;
}

sub getFramePath
{
    my ($self, $frame) = @_;

    $imageTemplate = $self->package()->imageTemplate();
    return undef if (not $imageTemplate);

    my $padString;
    if ($imageTemplate =~ /(\#+)/)
    {
    $padString = $1;
    } else {
    return undef;
    }

    my $padLength = length($padString);
    my $paddedFrame = sprintf("%0${padLength}d", $frame);

    my $framePath;
    ($framePath = $imageTemplate) =~ s/\#+/$paddedFrame/;

    return $framePath;
}    

sub isFrameExists
{
    my ($self, $framePath) = @_;
    return (-e $framePath);
}

sub isFrameBigEnough
{
    my ($self, $framePath, $size) = @_;
    my $imageSize = (-s $framePath);
    return($imageSize >= $size);
}    

#
# set up render globals
#
sub setupRenderGlobals
{
    my $self = shift;

	# load mental ray plugin if necessary
	$self->loadMayatomrPlugin();
	$self->melexec("miCreateDefaultNodes()");

    # naming
    $self->mrPutFrameBeforeExtension();
    $self->mrExtensionPadding();

    # output
    $self->mrImageFormat();
    $self->mrImageFilePrefix();
    $self->mrRenderDirectory();

    # image geometry
    $self->mrXResolution();
    $self->mrYResolution();
    $self->mrBottomRegion();
    $self->mrLeftRegion();
    $self->mrRightRegion();
    $self->mrTopRegion();

    # camera
    $self->mrImageChannel();
    $self->mrMaskChannel();
    $self->mrDepthChannel();

    # motion blur
    $self->mrShutterAngle();

    # MEL
    $self->mrPreRenderMel();
    $self->mrPostRenderMel();

    $self->melexec("checkDefaultRenderGlobals -changed true;");

    return 0;
}

sub loadMayatomrPlugin
{
	my $self = shift;
	my $cmd = 'if ( ! `pluginInfo -q -l "Mayatomr"` ) ' .
		'{ loadPlugin "Mayatomr"; }';
	$self->melexec($cmd);
}

sub mrByExtension
{
    my ($self, $by) = @_;
    $by = $self->package->byExtension() if @_ < 2;
    return if not defined $by;
    my $command = sprintf('setAttr mentalrayGlobals.modifyExtension 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.byExtension %s;',
                        $by);
    $self->melexec($command);
    return;
}
sub mrAnimationMode
{
    my ($self, $animation) = @_;
    $animation = $self->package->animation() if @_ < 2;
    return if not defined $animation;
    my $command = sprintf('setAttr mentalrayGlobals.animation %s;',
                          $animation);
    $self->melexec($command);
    return;
}
sub mrOutFormatExtension
{
    my ($self, $ext) = @_;
    $ext = $self->package->outFormatExt() if @_ < 2;
    return if not defined $ext;
    my $command = sprintf('setAttr mentalrayGlobals.outFormatExt -type "string" "%s";',
                          $ext);
    $self->melexec($command);
    return;
}
sub mrPutFrameBeforeExtension
{
    my ($self, $put) = @_;
    $put = $self->package->putFrameBeforeExt() if @_ < 2;
    return if not defined $put;
    my $command = sprintf('setAttr mentalrayGlobals.putFrameBeforeExt %s;',
                          $put);
    $self->melexec($command);
    return;
}    
sub mrExtensionPadding
{
    my ($self, $pad) = @_;
    $pad = $self->package->extensionPadding() if @_ < 2;
    return if not defined $pad;
    my $command = sprintf('setAttr mentalrayGlobals.extensionPadding %s;',
                          $pad);
    $self->melexec($command);
    return;
}    
sub mrImageFilePrefix
{
    my ($self, $name) = @_;
    $name = $self->package->image() if @_ < 2;
    return if not defined $name;
    my $command = sprintf('setAttr mentalrayGlobals.imageFilePrefix -type "string" "%s";', 
                          $name);
    $self->melexec($command);
    return;
}
sub mrImageFormat
{
    my ($self, $format) = @_;
    $format = $self->package->outputFormat() if @_ < 2;
    return if not defined $format;
    my %formatTable = (
                       gif    => 0,
                       soft   => 1,  softimage => 1,
                       rla    => 2,  wave      => 2,  wavefront => 2,
                       tif    => 3,  tiff      => 3,
                       tif16  => 4,  tiff16    => 4,
                       sgi    => 5,  rgb       => 5,
                       alias  => 6,  als       => 6,  pix       => 6,
                       iff    => 7,  tdi       => 7,  explore   => 7, maya => 7,
                       jpg    => 8,  jpeg      => 8,
                       eps    => 9,
                       maya16 => 10, iff16     => 10, 
                       cineon => 11, cin       => 11, fido      => 11,
                       qtl    => 12, quantel   => 12, yuv       => 12,
                       sgi16  => 13, rgb16     => 13,
                       tga    => 19, targa     => 19,
                       bmp    => 20,
                       sgimv  => 21, mv        => 21, 
                       qt     => 22, Quicktime => 22, QuickTime => 22,
                       AVI    => 23, avi       => 23
                       );
    my $formatNum = $formatTable{$format};
    my $command = sprintf('setAttr mentalrayGlobals.imageFormat %s;', 
                          $formatNum);
    $self->melexec($command);
    return;
}
sub mrRenderDirectory
{
    my ($self, $directory) = @_;
    $directory = $self->package->renderDirectory() if @_ < 2;
    return if not defined $directory;
    my $command = sprintf('workspace -rt "%s" "%s";', "images", $directory);
    $command .=
	'{string $imgDir = `workspace -q -rte "images"`;'.
	' string $imgDirFullPath = `workspace -expandName $imgDir`;'.
	' setAttr mentalrayGlobals.outputPath -type "string" $imgDirFullPath;}';
    $self->melexec($command);
    return;
}
sub mrIPRDirectory
{
    my ($self, $directory) = @_;
    $directory = $self->package->iprDirectory() if @_ < 2;
    return if not defined $directory;
    my $command = sprintf('workspace -rt "%s" "%s";', "iprImages",
                          $directory);
    $self->melexec($command);
    return;
}
#
# CAMERA
#
sub mrShutterAngle
{
    my ($self, $angle) = @_;
    $angle = $self->package->shutterAngle() if @_ < 2;
    return if not defined $angle;
    my $command = sprintf('camera -edit -shutterAngle %s "%s";',
                          $angle, $self->package->cameraOverride());
    $self->melexec($command);
    return;
}
sub mrImageChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->imageChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.image %s;',
                          $self->package->cameraOverride(), $channel);
    $self->melexec($command);
    return;
}
sub mrMaskChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->maskChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.mask %s;',
                          $self->package->cameraOverride(), $channel);
    $self->melexec($command);
    return;
}
sub mrDepthChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->depthChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.depth %s;',
                          $self->package->cameraOverride(), $channel);
    $self->melexec($command);
    return;
}

#
# MEL
#
sub mrPreRenderMel
{
    my ($self, $mel) = @_;
    $mel = $self->package->preRenderMel() if @_ < 2;
    return if not defined $mel;
    my $command = sprintf('setAttr mentalrayGlobals.preRenderMel -type "string" "%s";',
                          $mel);
    $self->melexec($command);
    return;
}
sub mrPostRenderMel
{
    my ($self, $mel) = @_;
    $mel = $self->package->postRenderMel() if @_ < 2;
    return if not defined $mel;
    my $command = sprintf('setAttr mentalrayGlobals.postRenderMel -type "string" "%s";',
                          $mel);
    $self->melexec($command);
    return;
}
sub mrStartExtension
{
    my ($self, $start) = @_;
    $start = $self->package->startExtension() if @_ < 2;
    return if not defined $start;
    my $command = sprintf('setAttr mentalrayGlobals.modifyExtension 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.startExtension %s;',
                        $start);
    $self->melexec($command);
    return;
}
#
# RENDER REGIONS
#
sub mrBottomRegion
{
    my ($self, $yl) = @_;
    $yl = $self->package->yLow() if @_ < 2;
    return if not defined $yl;
    my $command = sprintf('setAttr mentalrayGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.bottomRegion %s;',
                        $yl);
    $self->melexec($command);
    return;
}
sub mrLeftRegion
{
    my ($self, $xl) = @_;
    $xl = $self->package->xLeft() if @_ < 2;
    return if not defined $xl;
    my $command = sprintf('setAttr mentalrayGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.leftRegion %s;',
                        $xl);
    $self->melexec($command);
    return;
}
sub mrRightRegion
{
    my ($self, $xr) = @_;
    $xr = $self->package->xRight() if @_ < 2;
    return if not defined $xr;
    my $command = sprintf('setAttr mentalrayGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.rightRegion %s;',
                        $xr);
    $self->melexec($command);
    return;
}
sub mrTopRegion
{
    my ($self, $yh) = @_;
    $yh = $self->package->yHigh() if @_ < 2;
    return if not defined $yh;
    my $command = sprintf('setAttr mentalrayGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr mentalrayGlobals.topRegion %s;',
                        $yh);
    $self->melexec($command);
    return;
}
sub mrUseFrameExtension
{
    my ($self, $use) = @_;
    $use = $self->package->useFrameExtension() if @_ < 2;
    return if not defined $use;
    my $command = sprintf('setAttr mentalrayGlobals.useFrameExt %s;',
                          $use);
    $self->melexec($command);
    return;
}
sub mrUseMayaFileName
{
    my ($self, $use) = @_;
    $use = $self->package->mayaExtension() if @_ < 2;
    return if not defined $use;
    my $command = sprintf('setAttr mentalrayGlobals.useMayaFileName %s;',
                          $use);
    $self->melexec($command);
    return;
}    
#
# RESOLUTION
#
sub mrXResolution
{
    my ($self, $x) = @_;
    $x = $self->package->xResolution() if @_ < 2;
    return if not defined $x;
    my $command = sprintf('setAttr defaultResolution.width %s;',
                          $x);
    $self->melexec($command);
    return;
}
sub mrYResolution
{
    my ($self, $y) = @_;
    $y = $self->package->yResolution() if @_ < 2;
    return if not defined $y;
    my $command = sprintf('setAttr defaultResolution.height %s;',
                          $y);
    $self->melexec($command);
    return;
}


#
# ANTIALIASING
#
sub _mayaCurrentTime
{
    my ($self, $time) = @_;
    my $command = sprintf('currentTime -e %s;', $time);
    $self->melexec($command);
    return;
}

sub _mayaStartFrame
{
    my ($self, $frame) = @_;

    my $command = sprintf('setAttr mentalrayGlobals.startFrame %s;',
                          $frame);
    $self->melexec($command);
    my $command = sprintf('setAttr defaultRenderGlobals.startFrame %s;',
                          $frame);
    $self->melexec($command);
    return;
}
sub _mayaEndFrame
{
    my ($self, $frame) = @_;

    my $command = sprintf('setAttr mentalrayGlobals.endFrame %s;',
                          $frame);
    $self->melexec($command);
    my $command = sprintf('setAttr defaultRenderGlobals.endFrame %s;',
                          $frame);
    $self->melexec($command);
    return;
}    


sub _filterOutput
{
	my ($self, $prompt, $response, $text) = @_;
	my $result;

	$text =~ s/$prompt\s*//g if ($prompt !~ /render/);
	if ($response =~ /\(/) {
		($text =~ /$response\s*(.*)/) and do { $result = $2; };
	} else {
		($text =~ /$response\s*(.*)/) and do { $result = $1; };
	}

	$result =~ s/\([^\)]+\s*\n//g;
	$result =~ s/\s+$//g;
	$result =~ s/^\s+//g;
	return $result;
}


sub _countChar
{
	my $string = shift;
	my $char = shift;
	return split($char, $string) - 1;
}

sub _removeChar
{
	my $string = shift;
	my $char = shift;
	my $instance = shift;
	
	my @segments = split($char, $string);
	my $count = 1;
	my $result = shift @segments;
	for (@segments) {
		$result .= $char if ($count != $instance);
		$result .= $_;
		$count++;
	}

	return $result;
}

sub _permuteChar
{
	my $string = shift;
	my $pattern = shift;
	my $pos = shift || 0;
	my $result = shift || {};
	return $result if ($pos >= length($pattern));

	my @pat = split(//, $pattern);
	my $limit = _countChar($string, $pat[$pos]);
	for (0 .. $limit) {
		my $data = _removeChar($string, $pat[$pos], $_);
		$result->{$data} = 1;

		_permuteChar($data, $pattern, $pos + 1, $result);
	}

	return $result;
}

sub _permutations
{
	my $data = _permuteChar(@_);
	my $result = [];
	@{$result} = keys %{$data};
	return $result;
}


sub _fixFrameName
{
	my ($self, $file) = @_;

	return $file if (-e $file);

	my $files = _permutations($file, "mel: ");
	for (@{$files}) {
		return $_ if (-e $_);
	}

	return $file;
}


1;
