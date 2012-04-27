#!/usr/bin/perl
#
#       $RCSfile: qbMayaRender.pl,v $
#       $Header: /home/cvs/cvsroot/jobtype/maya/qbMayaRender.pl,v 1.2 2005/05/11 01:46:57 shinya Exp $
#       Copyright: PipeLine FX @ 2002
#
###############################################################################
#
#       Command-line Maya jobtype front-end
#
###############################################################################
#
#       $Log: qbMayaRender.pl,v $
#       Revision 1.2  2005/05/11 01:46:57  shinya
#       Removed the "Memory" option (--qbmemory), as it's been long
#       obsoleted and had no effect whatsoever on the submitted job.
#       See case 1592.
#
#       Revision 1.1.1.1  2005/02/11 20:36:49  cvs
#       fractioning off job type libraries
#
#       Revision 1.5.2.2  2004/12/14 02:59:07  cvs
#       added --qbflags
#
#       Revision 1.5.2.1  2004/07/29 06:07:15  cvs
#       new maya job type designed to work better with Gelato and Mental Ray
#
#       Revision 1.5  2004/03/26 20:00:32  cvs
#       added CurrentRenderer option
#
#       Revision 1.4  2004/03/05 21:43:31  cvs
#       corrected postrendermel argument
#
#       Revision 1.3  2004/01/23 23:51:57  cvs
#       added preRenderMel/postRenderMel to usage help
#
#       Revision 1.2  2004/01/23 23:43:32  cvs
#        added command option -preRenderMel -postRenderMel
#
#       Revision 1.1  2003/08/12 21:18:43  cvs
#       new
#
#       Revision 1.12  2003/06/17 04:33:12  cvs
#       corrected usage message
#
#       Revision 1.11  2003/05/12 20:44:35  cvs
#       add --localdm option
#
#       Revision 1.10  2003/02/26 21:13:46  cvs
#       fixes to everything
#
#       Revision 1.9  2003/02/26 03:45:55  cvs
#       added -user -groups -hosts
#
#       Revision 1.8  2003/01/15 21:53:12  cvs
#       added --qbreservations --qbresrictions options
#
#       Revision 1.7  2003/01/15 21:40:18  cvs
#       added --batchmode flag
#
#       Revision 1.6  2003/01/14 05:07:52  cvs
#       Use QBDIR env variable for lib path
#
#       Revision 1.3  2002/10/19 02:42:43  cvs
#       fixed "motoin" typo in usage message
#
#       Revision 1.2  2002/10/19 01:01:23  cvs
#       added usage messages
#
#
###############################################################################
use strict;
use Getopt::Long;

use lib qq($ENV{QBDIR}/api/perl);
use lib qq($ENV{QBDIR}/api/perl/qb/blib/lib);
use lib qq($ENV{QBDIR}/api/perl/qb/blib/arch);
use lib "../../api/perl";

use qb;
use qb::Job;

main();

sub main
{
    my $args = parseCommandLine();
    my $agenda = buildAgenda($args);
    my $job = buildJob($args, $agenda);
    submitJob($job);
}


sub parseCommandLine
{
    my $args = {};
    my %argspec = (
		   'h|help',  \&usage,
		   's=f',     \$args->{startFrame},
		   'e=f',     \$args->{endFrame},
		   'b=f',     \$args->{byFrame},
		   'se=i',    \$args->{startExtension},
		   'be=i',    \$args->{byExtension},
		   'pad=i',   \$args->{extensionPadding},
		   'proj=s',  \$args->{project},
		   'export=s',\$args->{export},
		   'rd=s'   , \$args->{renderDirectory},
		   'im|p=s',  \$args->{image},
		   'me=s',    \$args->{mayaExtension},
		   'mf=s',    \$args->{mayaFormat},
		   'cam=s',   \$args->{cameraOverride},
		   'g=f',     \$args->{gamma},
		   'ifg=s',   \$args->{ignoreFilmGate},
		   'ih=i',    \$args->{imageHeight},
		   'iw=i',    \$args->{imageWidth},
		   'ard=f',   \$args->{deviceAspectRatio},
		   'ar=f',    \$args->{aspectRatio},
		   'mm=i',    \$args->{maximumMemory},
		   'mb=s',    \$args->{motionBlur},
		   'mbf=f',   \$args->{motionBlurByFrame},
		   'sa=f',    \$args->{shutterAngle},
		   'mb2d=s',  \$args->{motionBlur2D},
		   'bll=f',   \$args->{blurLength},
		   'bls=f',   \$args->{blurSharpness},
		   'smv=i',   \$args->{smoothValue},
		   'smc=s',   \$args->{smoothColor},
		   'kmv=s',   \$args->{keepMotionVector},
		   'uf=s',    \$args->{useFileCache},
		   'oi=s',    \$args->{optimizeInstances},
		   'rut=s',   \$args->{reuseTessellations},
		   'udb=s',   \$args->{useDisplacementBbox},
		   'edm=s',   \$args->{enableDepthMaps},
		   'ert=s',   \$args->{enableRayTrace},
		   'rfl=i',   \$args->{reflections},
		   'rfr=i',   \$args->{refractions},
		   'rl=s',    \$args->{renderLayers},
		   'rp=s',    \$args->{renderPasses},
		   'rs=s',    \$args->{renderSubdirs},
		   'sl=i',    \$args->{shadowLevel},
		   'eaa=s',   \$args->{edgeAntiAliasing},
		   'ufil=s',  \$args->{useFilter},
		   'pft=s',   \$args->{pixelFilterType},
		   'ss=i',    \$args->{shadingSamples},
		   'mss=i',   \$args->{maxShadingSamples},
		   'mvs=i',   \$args->{visibilitySamples},
		   'mvm=i',   \$args->{maxVisibilitySamples},
		   'vs=i',    \$args->{volumeSamples},
		   'pss=i',   \$args->{particleSamples},
		   'rct=f',   \$args->{redThreshold},
		   'gct=f',   \$args->{greenThreshold},
		   'bct=f',   \$args->{blueThreshold},
		   'cct=f',   \$args->{coverageThreshold},
		   'of=s',    \$args->{outputFormat},
		   'sp=s',    \$args->{shadowPass},
		   'amt',     \$args->{abortOnMissingTexture},
		   'rep',     \$args->{dontReplaceRendering},
		   'verbose=s', \$args->{verbose},
		   'ipr',     \$args->{iprFile},
		   'x=i',     \$args->{xResolution},
		   'y=i',     \$args->{yResolution},
		   'xl=i',    \$args->{xLeft},
		   'xr=i',    \$args->{xRight},
		   'yl=i',    \$args->{yLow},
		   'yh=i',    \$args->{yHigh},
		   'l=s',     \$args->{displayLayer},
		   'n=i',     \$args->{numberOfProcessors},
		   'tw=i',    \$args->{tileWidth},
		   'th=i',    \$args->{tileHeight},
		   'cont',    \$args->{continue},
                   'renderer=s', \$args->{currentRenderer},
                   'preRenderMel=s', \$args->{preRenderMel},
                   'postRenderMel=s', \$args->{postRenderMel},
		   'keepPreImage',   \$args->{keepPreImage},
                   'localdm',        \$args->{localdm},
                   'maxPasses=i',      \$args->{maxPasses},
                   'badFrameSize=i',   \$args->{badFrameSize},
		   'qbname=s',       \$args->{qbname},
                   'qbuser=s',       \$args->{qbuser},
		   'qbpriority=i',   \$args->{qbpriority},
		   'qbhosts=s',   \$args->{qbhosts},
		   'qbgroups=s',   \$args->{qbgroups},
		   'qbflags=s',   \$args->{qbflags},
		   'qbrequirements=s', \$args->{qbrequirements},
		   'qbreservations=s', \$args->{qbreservations},
		   'qbrestrictions=s', \$args->{qbrestrictions},
		   'qbpid=i',        \$args->{qbpid},
		   'qbpgrp=i',       \$args->{qbpgrp},
		   'qbbranch|qbcluster=s',     \$args->{qbcluster},
		   'qbcpus=i',       \$args->{qbcpus},
		   'qbstatus=s',     \$args->{qbstatus},
		   'qbframes=s',     \$args->{qbframes},
		   'qbmail',     \$args->{qbmail},
		   'qbmailaddress=s',     \$args->{qbmailaddress},
		   'batchmode',      \$args->{batchmode},
		   'ignoreRenderTimeErrors',      \$args->{ignoreRenderTimeErrors},
		   'qbtimelimit=i',     \$args->{qbtimelimit},
		   );

    my $result = GetOptions(%argspec);

    # check for unknown options
    usage("",1) if ($result == 0);

    # check for scenefiles in @ARGV
    my @scenefiles = grep '/*\.m[ab]/', @ARGV;
    usage("ERROR: no scenefile specified...\n", 10) 
	if (scalar(@scenefiles) == 0);
    usage("ERROR: multiple scenefiles specified...\n", 11) 
	if (scalar(@scenefiles) > 1);
    $args->{scenefile} = shift @scenefiles;

    return $args;
}


sub buildJob
{
    my ($args, $agenda) = @_;

    my $job = qb::Job->new();
    $job->agenda($agenda);
    $job->prototype("maya");

    my $exportFile = undef;

	my $flags = "";
	# process cmdline args
    while (1)
    {
		my ($key, $value) = each(%$args);
		last if (not $key);
		next if (not defined($value));
		if ($key =~ /^export/) {
			$exportFile = $value;
		} elsif ($key eq "qbflags") {
			$flags = join ",", (split /,/, $flags), $value;
		} elsif ($key eq "qbmail") {
			$flags = join ",", (split /,/, $flags), "mail";
		} elsif ($key eq "qbtimelimit") {
			$job->timeout($value);
			$job->{callbacks} =
				[
				 {
				  "triggers" => "timeout-subjob-self-*",
				  "language" => "qube",
				  "code" => "kill-subjob-self",
				 }
				];
		} elsif ($key =~ /^qb/) { 
			$key =~ s/^qb//; 
			$job->$key($value); 
		} else { 
			$job->package($key,$value); 
		}
    }
	if($flags) {
		$job->flagsstring($flags);
	}

    if (defined $exportFile) {
		qb::_qb_archivejob($exportFile, $job);
		print "exported file: ", $exportFile, "\n";
		exit(0);
    }
    return $job;
}


sub buildAgenda
{
    my $args = shift;
    my $agenda = [];

    # try frame list first
    if (defined ($args->{qbframes})) {
	$agenda = qb::genframes($args->{qbframes});
	$args->{qbframes} = undef;
    } else {

    # try maya -s -e
	$agenda = qb::genframes($args->{startFrame}."-".$args->{endFrame});
	$args->{startFrame} = undef;
	$args->{endFrame} = undef;
    }

    # verify valid agenda list
    die "ERROR: need valid frame range..." if (not $agenda);

    return $agenda;
    
}


sub submitJob
{
    my ($job) = @_;

    my @results;
    my @results = qb::submit($job);
    for my $jobinfo (@results)
    {
	print $jobinfo->{id}, "\n";
    }
    return;
}


sub usage
{
    use File::Basename;
    my ($msg, $status) = @_;

    print "$msg\n" if ($msg !~ "^h");

    print "Usage: ",basename($0)," <maya options> <qube options> <filename>\n";
    print "  where <filename> is a Maya ASCII or a Maya Binary file.\n";
    print "\n<maya options>: \n";
    print "  -s   <float>     starting frame for an animation sequence\n";
    print "  -e   <float>     end frame for an animation sequence\n";
    print "  -b   <float>     by frame (or step)\n";
    print "                   for an animation sequence\n";
    print "  -se  <int>       starting number for the output image\n";
    print "                   frame file name extensions\n";
    print "  -be  <int>       by extension (or step) for the output\n";
    print "                   image frame file name extension\n";
    print "  -pad <int>       number of digits in the output image\n";
    print "                   frame file name extension\n";
    print "  -proj <dir>      project directory to use\n";
    print "  -rd  <path>      directory in which to store image file\n";
    print "  -im  <filename>  image file output name (identical to -p)\n";
    print "  -p   <filename>  image file output name (identical to -im)\n";
    print "  -me  <boolean>   append maya file name to image name\n";
    print "                   if true\n";
    print "  -mf  <boolean>   append image file format to image name\n";
    print "                   if true\n";
    print "  -cam <name>      render using specified camera\n";
    print "                   renders using first renderable cam otherwise\n";
    print "  -g   <float>     gamma value\n";
    print "  -ifg <boolean>   use the film gate for rendering if false\n";
    print "  -ard <float>     device aspect ratio for the rendered image\n";
    print "  -ar  <float>     aspect ratio for the film aperture\n";
    print "  -mm  <int>       renderer maximum memory use (in MB)\n";
    print "  -mb  <boolean>   motion blur on/off\n";
    print "  -mbf <float>     motion blur by frame\n";
    print "  -sa  <float>     shutter angle for motion blur (1-360)\n";
    print "  -mb2d <boolean>  motion blur 2D on/off\n";
    print "  -bll <float>     2D motion blur blur length\n";
    print "  -bls <float>     2D motion blur blur sharpness\n";
    print "  -smv <int>       2D motion blur smooth value\n";
    print "  -smc <boolean>   2D motion blur smooth color on/off\n";
    print "  -kmv <boolean>   keep motion vector for 2D motion blur on/off\n";
    print "  -uf  <boolean>   use the tessellation file cache\n";
    print "  -oi  <boolean>   dynamically detects similarly\n";
    print "                   tessellated surfaces\n";
    print "  -rut <boolean>   reuse render geometry to\n";
    print "                   generate depth maps\n";
    print "  -udb <boolean>   use the displacement bounding box scale to\n";
    print "                   optimize displacement-map performance\n";
    print "  -edm <boolean>   enable depth map usage\n";
    print "  -ert <boolean>   enable ray tracing\n";
    print "  -rfl <int>       maximum ray-tracing reflection level\n";
    print "  -rfr <int>       maximum ray-tracing refraction level\n";
    print "  -rp <boolean|name>  render passes separately\n";
    print "  -rs <boolean>    render layer output placed in subdirectories\n";
    print "  -sl  <int>       maximum ray-tracing shadow ray depth\n";
    print "  -eaa <quality>   The anti-aliasing quality of EAS \n";
    print "                   (Abuffer). One of highest high medium low\n";
    print "  -ufil <boolean>  if true, use the multi-pixel filtering\n";
    print "                   otherwise use single pixel filtering.\n";
    print "  -pft  <filter>   when useFilter is true, identifies one of the\n";
    print "                   following filters: box, triangle\n";
    print "                   gaussian, quadraticbspline, plugin\n";
    print "  -ss  <int>       global number of shading samples\n";
    print "                   per surface in a pixel\n";
    print "  -mss <int>       maximum number of adaptive shading\n";
    print "                   samples per surface in a pixel\n";
    print "  -mvs <int>       number of motion blur visibility samples\n";
    print "  -mvm <int>       maximum number of motion blur\n";
    print "                   visibility samples\n";
    print "  -vs  <int>       global number of volume shading samples\n";
    print "  -pss <int>       number of particle visibility samples\n";
    print "  -rct <float>     red channel contrast threshold\n";
    print "  -gct <float>     green channel contrast threshold\n";
    print "  -bct <float>     blue channel contrast threshold\n";
    print "  -cct <float>     pixel coverage contrast threshold\n";
    print "                   (default is 1.0/8.0)\n";
    print "  -of  <format>    output image file format. One of: si soft                                       softimage, gif, rla wave wavefront, tiff\n";
    print "                   tif, tiff16 tif16, sgi rgb, sgi16 rgb16\n";
    print "                   alias als pix, iff tdi explore maya, jpeg                                       jpg, eps, maya16 iff16, cineon cin fido,\n";
    print "                   qtl quantel, tga targa, bmp\n";
    print "  -sp <boolean>    generate shadow depth maps only\n";
    print "  -ipr             create an IPR file\n";
    print "  -x   <int>       set X resolution of the final image\n";
    print "  -y   <int>       set Y resolution of the final image\n";
    print "  -xl  <int>       set X sub-region left pixel boundary\n";
    print "                   of the final image\n";
    print "  -xr  <int>       set X sub-region right pixel boundary\n";
    print "                   of the final image\n";
    print "  -yl  <int>       set Y sub-region low pixel boundary\n";
    print "                   of the final image\n";
    print "  -yh  <int>       set Y sub-region high pixel boundary\n";
    print "                   of the final image\n";
    print "  -n  <int>        number of processors to use. 0 indicates\n";
    print "                   use all available.\n";
    print "  -tw <int>        force the width of the tiles.  Valid values\n";
    print "                   are between 16 and 256.\n";
    print "  -th <int>        force the height of the tiles.  Valid values\n";
    print "                   are between 16 and 256.\n";
    print "  -renderer        render engine to use\n";
    print "  -keepPreImage    keep the renderings prior to post-process around\n";
    print "  -localdm         depthmaps to local temp directory\n";
    print "  -maxPasses       maximum number of attempts to render frame (default: 1)\n";
    print "  -badFrameSize    size of bad or blank frame (in bytes)\n";
    print "  -preRenderMel    pre-render mel script\n";
    print "  -postRenderMel   post-render mel script\n";
    print " Any boolean flag will take on, yes, true, or 1, as TRUE,\n";
    print " and off, no, false, or 0 as FALSE.\n";
    print "\n<qube options>: \n";
    print "  --qbname <string>            job name\n";
    print "  --qbuser <string>            impersonate user\n";
    print "  --qbpriority <int>           job priority \n";
    print "  --qbhosts <string>           job hosts to run in \n";
    print "  --qbgroups <string>          job hostgroup to run in \n";
    print "  --qbrequirements <string>    job requirements\n";
    print "  --qbrestrictions <string>    job restrictions\n";
    print "  --qbreservations <string>    job reservations\n";
    print "  --qbpid <int>                parent job to submitted job\n";
    print "  --qbpgrp <int>               process group\n";
    print "  --qbcluster <string>         cluster\n";
    print "  --qbcpus <int>               number of cpus to run\n";
    print "  --qbflags <string>           job flags to run in \n";
    print "  --qbstatus <string>          job in \"blocked\" or \"pending\" state\n";
    print "  --qbframes <int|string>      list of frames to render\n";
    print "  --qbmail                     enable email notification\n";
    print "  --qbmailaddress <string>     override default email notification address\n";
    print "  --qbtimelimit <int>          commit hara-kiri after specified seconds\n";
    print "  --batchmode                  force job to use Maya command line render\n";
    print "  --ignoreRenderTimeErrors     ignore render-time errors\n";
    exit $status if ($status != 0);
}
