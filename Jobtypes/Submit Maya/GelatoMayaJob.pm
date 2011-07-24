###########################################################################
#
#      Copyright: Pipelinefx @ 2002-2006
#
###########################################################################
#
# GelatoMayaJob.pm
#
##############################################################################

local $| = 1;

package maya::GelatoMayaJob;

use IPC::Open3;
use File::Path;
use maya::MayaJob;
use maya::PromptMayaJob;

use Symbol;

# use lib qq($ENV{QBDIR}/types);
# use lib qq($ENV{QBDIR}/api/perl);

use IPC::Run qw( start pump finish timeout );
use File::Temp;

use qb::Job;

use maya::Utils qw(removeCameraNodeNameFromFilename);


@ISA = qw(maya::PromptMayaJob);

$MayaJob::MAYA_LAUNCH_TIMEOUT = 2 * 60;
$MayaJob::MAYA_LOAD_TIMEOUT = 60 * 60;
$MayaJob::MAYA_COMMAND_TIMEOUT = 60;
$MayaJob::MAYA_RENDER_TIMEOUT = 125;
$MayaJob::MAYA_QUIT_TIMEOUT = 20;
$MayaJob::MAXBYTES = 1024;

$MayaJob::ERRMISSINGFILE = 128;
$MayaJob::ERRMAYAPROBLEM = 64;

BEGIN {
	if (not defined $ENV{GELATOHOME}) {
		$ENV{GELATOHOME} = $^O eq "MSWin32" ? 'C:\Gelato' : "/opt/nvidia/gelato";
	}
}


sub new 
{
    my ($class, @args) = @_;
    my $self = {};
    bless $self, $class;
    $self->_init(@args);
    return $self;
}

#############################################################################
#   Maya Command Control Routines
#############################################################################


sub initializeRenderer
{
    my $self = shift;

    my $ext = $^O eq "MSWin32" ? ".mll" : ".so";
    $self->_mayaCommand("loadPlugin -qt (getenv(\"GELATOHOME\") + \"/mango/maya5.0/plug-ins/Mango$ext\");");
    $self->_mayaCommand("addGelatoRenderGlobals();");

   # naming
    $self->mrPutFrameBeforeExtension();
    $self->mrExtensionPadding();

    # output
    $self->mrImageFormat();

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

    return 0;
}


sub renderMayaFrame
{
    my ($self, $work) = @_;

    my $frame = $work->name();
    my $start = $frame;
    my $end = $frame;

    $self->_mayaCurrentTime($start);
    $self->_mayaEndFrame($end);
    $self->_mayaStartFrame($start);

    my $renderOutput;

    my $cameraArray = [];

    if (defined($self->package->cameraOverride())) {
        $cameraArray = ref($self->package->cameraOverride()) 
            ? $self->package->cameraOverride() 
            : [$self->package->cameraOverride()];
    } elsif($work->package()) {
        $cameraArray = ref($work->package->cameraOverride()) 
            ? $work->package->cameraOverride() 
            : [$work->package->cameraOverride()];
    } else {
        my @sceneCameras = $self->mayaGetCameras();
        foreach my $camera (@sceneCameras) {
            push (@{$cameraArray}, $camera) 
                if ($self->mayaIsRenderableCamera($camera));
        }
    }

    my $failed = 0;

    # turn off all the cameras
    foreach my $camera (@sceneCameras) {
        $command = sprintf('setAttr %s.renderable 0;', $camera);
        my $result = $self->_mayaCommand($command);
    }

    # turn on all the specified cameras
    foreach my $camera (@$cameraArray) {
        $command = sprintf('setAttr %s.renderable 1;', $camera);
    }

    # setup gelato renderglobals
    $command = " addGelatoRenderGlobals();";
    $self->_mayaCommand($command);

    my $TEMP = $^O eq "MSWin32" ? $ENV{TMP} || $ENV{TEMP} : "/tmp";
    $TEMP =~ s/\\/\//g;

    my $jobid = $ENV{QBJOBID}."_".$ENV{QBSUBID};

    $command = "file -exportAll -force -type \"GelatoExport\" -options (\"startFrame=$frame;endFrame=$frame;animation=1;format=tif\") \"$TEMP/".$jobid."qube.pyg\";";
    $self->_mayaCommand($command);
                                   #        $MayaJob::MAYA_COMMAND_TIMEOUT, 
                                   #        "rendering finished",
                                   #        "(Finished Rendering|Result:|writing image file\s*)");


    my $pygfiles;
    my $filename = "$TEMP/".$jobid."qube.".$frame."Cmds.pyg";
    if (! -e $filename) { 
        $filename = "$TEMP/".$jobid."qube.".sprintf("%.4d", $frame)."Cmds.pyg";
    }

    if (! -e $filename) {
        $filename = "$TEMP/".$jobid."qubeCmds.pyg";
    }

    if (! -e $filename) {
	print "ERROR: unable to find pygfile - $filename\n";
    }


    open FILE, "<$filename";
    while (<FILE>) {
        if ($_ =~ /\.pyg/ and $_ =~ /gelato/) {
		if ($_ =~ /gelato[\s\"]+([^\']+)/) {
			$pygfiles = $1;
		}
	}
    }
    close FILE;

    my $renderOutput = ""; 
    for (split(/ /, $pygfiles)) {
	print "Searching for Output in file: $_\n";
        open FILE, "<$_";
        while (<FILE>) {
            if ($_ =~ /^Output\s*\(\s*((\"[^\"]+)|(\S+))/) {
		$renderOutput = $1;
		$renderOutput =~ s/\"//g;
            }
        }
        close FILE;
    }

    my $imageDir = $self->_mayaCommand("workspace -q -rte \"images\"");
    my $workspace = $self->_mayaCommand("workspace -q -dir");
    if ($^O eq "MSWin32") {
         if ($renderOutput !~ /^[A-Z]\:\//) {
		my $outdir = "";
		if ($imageDir =~ /^[A-Z]\:\//) {
			$outdir = $imageDir;
		} else {
			$outdir = $workspace."/".$imageDir;	
		}
		$outdir =~ s/[\n\r]//g;
		$outdir =~ s/\/+/\//g;
		$outdir =~ s/\/+$//g;
		if (! -e $outdir) {
			mkdir $outdir;
		}
		chdir $outdir;

		print "Output Directory: $outdir\n";
         }
    } else {
         if ($renderOutput !~ /^\//) {
		my $outdir = "";
		if ($imageDir =~ /^\//) {
			$outdir = $imageDir;
		} else {
			$outdir = $workspace."/".$imageDir;
		}
		$outdir =~ s/[\n\r]//g;
		$outdir =~ s/\/+/\//g;
		$outdir =~ s/\/+$//g;
		if (! -e $outdir) {
			mkdir $outdir;
		}
		chdir $outdir;

		print "Output Directory: $outdir\n";
         }
    }
    
    print($ENV{GELATOHOME}."/bin/gelato -statistics -verbosity 4 $pygfiles\n");
    my $results = `$ENV{GELATOHOME}/bin/gelato -statistics -verbosity 4 $pygfiles`;
    print $results;

    if (scalar(@$cameraArray) == 1) {
	$camera = $cameraArray->[0];
	$output = removeCameraNodeNameFromFilename($renderOutput, $camera);
        print "Rename: $output\n";
        $renderOutput = $output;
    }

    return $self->validateFrame($renderOutput);
}

sub mrByExtension
{
    my ($self, $by) = @_;
    $by = $self->package->byExtension() if @_ < 2;
    return if not defined $by;
    my $command = sprintf('setAttr defaultRenderGlobals.modifyExtension 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.byExtension %s;',
                        $by);
    $self->_mayaCommand($command);
    return;
}
sub mrAnimationMode
{
    my ($self, $animation) = @_;
    $animation = $self->package->animation() if @_ < 2;
    return if not defined $animation;
    my $command = sprintf('setAttr defaultRenderGlobals.animation %s;',
                          $animation);
    $self->_mayaCommand($command);
    return;
}
sub mrOutFormatExtension
{
    my ($self, $ext) = @_;
    $ext = $self->package->outFormatExt() if @_ < 2;
    return if not defined $ext;
    my $command = sprintf('setAttr defaultRenderGlobals.outFormatExt -type "string" "%s";',
                          $ext);
    $self->_mayaCommand($command);
    return;
}
sub mrPutFrameBeforeExtension
{
    my ($self, $put) = @_;
    $put = $self->package->putFrameBeforeExt() if @_ < 2;
    return if not defined $put;
    my $command = sprintf('setAttr defaultRenderGlobals.putFrameBeforeExt %s;',
                          $put);
    $self->_mayaCommand($command);
    return;
}    
sub mrExtensionPadding
{
    my ($self, $pad) = @_;
    $pad = $self->package->extensionPadding() if @_ < 2;
    return if not defined $pad;
    my $command = sprintf('setAttr defaultRenderGlobals.extensionPadding %s;',
                          $pad);
    $self->_mayaCommand($command);
    return;
}    
sub mrImageFilePrefix
{
    my ($self, $name) = @_;
    $name = $self->package->image() if @_ < 2;
    return if not defined $name;
    my $command = sprintf('setAttr defaultRenderGlobals.imageFilePrefix -type "string" "%s";', 
                          $name);
    $self->_mayaCommand($command);
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
    my $command = sprintf('setAttr defaultRenderGlobals.imageFormat %s;', 
                          $formatNum);
    $self->_mayaCommand($command);
    return;
}
sub mrRenderDirectory
{
    my ($self, $directory) = @_;
    $directory = $self->package->renderDirectory() if @_ < 2;
    return if not defined $directory;
    my $command = sprintf('workspace -rt "%s" "%s";', "images",
                          $directory);
    $self->_mayaCommand($command);
    return;
}
sub mrIPRDirectory
{
    my ($self, $directory) = @_;
    $directory = $self->package->iprDirectory() if @_ < 2;
    return if not defined $directory;
    my $command = sprintf('workspace -rt "%s" "%s";', "iprImages",
                          $directory);
    $self->_mayaCommand($command);
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
    $self->_mayaCommand($command);
    return;
}
sub mrImageChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->imageChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.image %s;',
                          $self->package->cameraOverride(), $channel);
    $self->_mayaCommand($command);
    return;
}
sub mrMaskChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->maskChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.mask %s;',
                          $self->package->cameraOverride(), $channel);
    $self->_mayaCommand($command);
    return;
}
sub mrDepthChannel
{
    my ($self, $channel) = @_;
    $channel = $self->package->depthChannel() if @_ < 2;
    return if not defined $channel;
    my $command = sprintf('setAttr %s.depth %s;',
                          $self->package->cameraOverride(), $channel);
    $self->_mayaCommand($command);
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
    my $command = sprintf('setAttr defaultRenderGlobals.preRenderMel -type "string" "%s";',
                          $mel);
    $self->_mayaCommand($command);
    return;
}
sub mrPostRenderMel
{
    my ($self, $mel) = @_;
    $mel = $self->package->postRenderMel() if @_ < 2;
    return if not defined $mel;
    my $command = sprintf('setAttr defaultRenderGlobals.postRenderMel -type "string" "%s";',
                          $mel);
    $self->_mayaCommand($command);
    return;
}
sub mrStartExtension
{
    my ($self, $start) = @_;
    $start = $self->package->startExtension() if @_ < 2;
    return if not defined $start;
    my $command = sprintf('setAttr defaultRenderGlobals.modifyExtension 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.startExtension %s;',
                        $start);
    $self->_mayaCommand($command);
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
    my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.bottomRegion %s;',
                        $yl);
    $self->_mayaCommand($command);
    return;
}
sub mrLeftRegion
{
    my ($self, $xl) = @_;
    $xl = $self->package->xLeft() if @_ < 2;
    return if not defined $xl;
    my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.leftRegion %s;',
                        $xl);
    $self->_mayaCommand($command);
    return;
}
sub mrRightRegion
{
    my ($self, $xr) = @_;
    $xr = $self->package->xRight() if @_ < 2;
    return if not defined $xr;
    my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.rightRegion %s;',
                        $xr);
    $self->_mayaCommand($command);
    return;
}
sub mrTopRegion
{
    my ($self, $yh) = @_;
    $yh = $self->package->yHigh() if @_ < 2;
    return if not defined $yh;
    my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1;\n');
    $command .= sprintf('setAttr defaultRenderGlobals.topRegion %s;',
                        $yh);
    $self->_mayaCommand($command);
    return;
}
sub mrUseFrameExtension
{
    my ($self, $use) = @_;
    $use = $self->package->useFrameExtension() if @_ < 2;
    return if not defined $use;
    my $command = sprintf('setAttr defaultRenderGlobals.useFrameExt %s;',
                          $use);
    $self->_mayaCommand($command);
    return;
}
sub mrUseMayaFileName
{
    my ($self, $use) = @_;
    $use = $self->package->mayaExtension() if @_ < 2;
    return if not defined $use;
    my $command = sprintf('setAttr defaultRenderGlobals.useMayaFileName %s;',
                          $use);
    $self->_mayaCommand($command);
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
    $self->_mayaCommand($command);
    return;
}
sub mrYResolution
{
    my ($self, $y) = @_;
    $y = $self->package->yResolution() if @_ < 2;
    return if not defined $y;
    my $command = sprintf('setAttr defaultResolution.height %s;',
                          $y);
    $self->_mayaCommand($command);
    return;
}


#
# ANTIALIASING
#
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

    my $command = sprintf('playbackOptions -min %s;',
                          $frame);
    $self->_mayaCommand($command);
    return;
}
sub _mayaEndFrame
{
    my ($self, $frame) = @_;

    my $command = sprintf('playbackOptions -max %s;',
                          $frame);
    $self->_mayaCommand($command);
    return;
}    
sub _mayaFrameStep
{
    my ($self, $step) = @_;

    my $command = sprintf('playbackOptions -by %s;',
                          $frame);
    $self->_mayaCommand($command);
    return;
}

1;
