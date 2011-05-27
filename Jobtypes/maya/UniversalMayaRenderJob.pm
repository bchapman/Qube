###########################################################################
#
#	   Copyright: Pipelinefx @ 2002-2006
#
###########################################################################
#
# SoftwareMayaJob.pm
#
###########################################################################

local $| = 1;

package maya::UniversalMayaRenderJob;

use Data::Dumper;
use File::Path;
use maya::MayaJob;
use maya::PromptMayaJob;

use File::Copy;
use File::Basename;
use File::Temp;
use Config;

use qb::Job;
use maya::Utils qw(removeCameraNodeNameFromFilename);

@ISA = qw(maya::PromptMayaJob);

###########################################################################
# Constructors and Object-Initialization Methods
###########################################################################

#
# We'll just inherit the constructor, the new() method, from our base class.
#

#############################################################################
#	Maya Command Control Routines
#############################################################################

#
# setThreads()
#
#  set the number of threads to use for this subjob, based on the
#  package variable, "renderThreads".  If it's "-1", sync with
#  host.processors for the job.  If it's "0", then use the default
#  value for the renderer (usually as many threads as there are
#  cores).  Otherwise, if renderThreads > 0, use the specified number
#  of threads.
#
sub setThreads
{
	my $self = shift;
	my $threads = -1;
	if(defined $self->package->{renderThreads}) {
		$threads = $self->package->{renderThreads};
	}

	warn "INFO: setting up thread control...\n";
	if($threads == -1) {
		warn "INFO: syncing thread count to 'host.processors'\n";
		# "renderThreads" of -1 means we should sync the number of
		# threads to "host.processors"

		# get the host.processors value into $threads
		my $reserv = $self->reservations();
		$reserv =~ s/\s*//g;	# remove all whitespace
		my %reserv = map {split(/=/, $_)} (split/,/, $reserv);
		$threads = $reserv{"host.processors"};

		# now $threads can be one of the following formats (N, M-N, N+)
		if($threads =~ /^\d+\+$/) {
			$threads = 0;		# REVIST: for now, we just set to ALL cores
		} elsif($threads =~ /^\d+-(\d+)$/) {
			$threads = $1;
		}
	}
	# POST-CONDITION; $threads is >= 0

	warn "INFO: threads=$threads\n";
	my $cmd = "setAttr defaultRenderGlobals.numCpusToUse $threads";
	$self->melexec($cmd);
	$cmd = "if(!`about -mac`) { threadCount -n $threads; }";
	$self->melexec($cmd);
	$cmd = "global int \$gNumProcessorsForBatchRender = $threads";
	$self->melexec($cmd);

	# for mental ray
	if($threads == 0) {
		$cmd = 'global int $g_mrBatchRenderCmdOption_NumThreadAutoOn = true;';
		$self->melexec($cmd);
	} else {
		$cmd = 'global int $g_mrBatchRenderCmdOption_NumThreadAutoOn = false;';
		$self->melexec($cmd);
		$cmd = 'global int $g_mrBatchRenderCmdOption_NumThreadOn = true;';
		$self->melexec($cmd);
		$cmd = "global int \$g_mrBatchRenderCmdOption_NumThread = $threads";
		$self->melexec($cmd);
	}
}

#
# initialize()
#
sub initialize
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	if(not $self->SUPER::initialize()) {
		warn "ERROR: SUPER::initialize()";
		return 0;
	}

	# load scenefile
	my $retval = $self->mayaLoadScenefile();

	if(not $retval) {
		# Error in loading scenefile
		warn("ERROR: couldn't load scenefile");
# 		qb::reportjob("failed");
		return $retval;
	}

	# call render globals setup routine for legacy parameter names
	$self->setupRenderGlobals();

	# set up render globals, resolution, renderDirectory, and camera
	#  from the package data.
	for (sort keys %{$self->package()}) {
		my $key = $_;
		my $val = $self->package->{$key};

		# translate legacy parameter names
		if($key eq "image" and $val ne "") {
			$key = "defaultRenderGlobals.imageFilePrefix";
		} elsif($key eq "currentRenderer" and $val) {
			$key = "defaultRenderGlobals.currentRenderer";
		} elsif($key eq "project" and $val ne "") {
			# this is taken care of in PromptMayaJob::mayaSetupWorkspace(),
			#  called from initialize()
		} elsif($key eq "extensionPadding" and $val ne "") {
			$key = "defaultRenderGlobals.extensionPadding";
		} elsif($key eq "mayaExtension" and $val ne "") {
			$key = "defaultRenderGlobals.outFormatExt";
			# NOTE: we also set "outFormatControl" behind the scene
			$self->melexec("setAttr defaultRenderGlobals.outFormatControl 2");
		} elsif($key eq "outputFormat" and $val ne "") {
			# ignored
			warn "INFO: package parameter '$key' is deprecated... ignored\n";
		} elsif($key eq "cameraOverride" and $val ne "") {
			# NOTE: overwrite the "cameras" package data
			$self->package->{cameras} = $self->package->{$key};
		} elsif($key eq "maxPasses" and $val ne "") {
			# ignored
			warn "INFO: package parameter '$key' is deprecated... ignored\n";
		} elsif($key eq "badFrameSize" and $val ne "") {
			# ignored
			warn "INFO: package parameter '$key' is deprecated... ignored\n";
		}

		if ($key eq "cameras") {
			# we'll handle cameras later
		} elsif($key eq "layers") {
			# we'll handle layers later
		} elsif ($key eq "renderDirectory" and $val) {
			$val =~ s!\\!/!g;
			$self->melexec("workspace -rt \"images\" \"$val\"");
		} elsif ($key eq "scenefile") {
			# no need to take action...
		} elsif ($key =~ /^(defaultRenderGlobals|defaultResolution)\./) {
			my $cmd;
			if ($val and
				$key eq "defaultRenderGlobals.currentRenderer" ||
				$key eq "defaultRenderGlobals.imageFilePrefix" ||
				$key eq "defaultRenderGlobals.outFormatExt" ||
				$key eq "defaultRenderGlobals.postMel" ||
				$key eq "defaultRenderGlobals.preMel" ||
				$key eq "defaultRenderGlobals.postRenderLayerMel" ||
				$key eq "defaultRenderGlobals.preRenderLayerMel" ||
				$key eq "defaultRenderGlobals.postRenderMel" ||
				$key eq "defaultRenderGlobals.preRenderMel"
			   ) {
				$cmd = "setAttr $key -type \"string\" \"$val\"";
			} else {
				$cmd = "setAttr $key $val";
			}
			$self->melexec($cmd);
		}
	}


	# set up cameras
	my $cameras = $self->package->{cameras} || "All Renderable";
	my @allCameras = $self->mayaGetCameras();
	if($cameras eq "All Renderable") {
		foreach my $cam (@allCameras) {
			$self->melexec("getAttr $cam.renderable");
			if ($self->melresult()) {
				push @{$self->{cameras}}, $cam;
			}
		}
		if(@{$self->{cameras}} == 0) {
			warn("ERROR: 'All Renderable' cameras selected, " .
				 "but none of the cameras are renderable\n");
		}
	} elsif ($cameras eq "All") {
		@{$self->{cameras}} = @allCameras;
	} else {
		# job explicitly specifies which cameras to render
		@{$self->{cameras}} = split / /, $cameras;
	}

	# set all cameras non-renderable for now...
	for (@allCameras) {
		$self->melexec("setAttr $_.renderable 0");
	}

	if(@{$self->{cameras}} == 0) {
		warn("ERROR: no cameras to render... aborting job\n");
		return 0;
	}
	warn("INFO: rendering camera(s): $cameras (@{$self->{cameras}})\n");

	# set up layers
	my $layers = $self->package->{layers} ||
		$self->package->{renderLayers} || "All Renderable";
	$self->melexec("listConnections renderLayerManager");
	my @allLayers = split / /, $self->melresult();
	if($layers eq "All Renderable") {
		foreach my $layer (@allLayers) {
			$self->melexec("getAttr $layer.renderable");
			if ($self->melresult()) {
				push @{$self->{layers}}, $layer;
			}
		}
		if(@{$self->{layers}} == 0) {
			warn("ERROR: 'All Renderable' layers selected, " .
				 "but none of the layers are renderable\n");
		}
	} elsif ($layers eq "All") {
		@{$self->{layers}} = @allLayers;
	} else {
		# job explicitly specifies which layers to render
		@{$self->{layers}} = split / /, $layers;
	}

	# set all layers non-renderable for now...
	for (@allLayers) {
		$self->melexec("setAttr $_.renderable 0");
	}

	if(@{$self->{layers}} == 0) {
		warn("ERROR: no layers to render... aborting job\n");
		return 0;
	}
	warn("INFO: rendering layer(s): $layers (@{$self->{layers}})\n");

	# create appropriate sub directories for layer and camera images
	my %renderDirs = $self->renderDirs();
	my $imgdir = $renderDirs{"images"};

	if (length($imgdir) == 0) {
		warn("WARNING: directory for fileRule 'images' not defined, defaulting to 'images'\n");
		$imgdir = "images";
		$self->melexec("workspace -renderType \"images\" $imgdir");
	}

	if (not File::Spec->file_name_is_absolute($imgdir)) {
		$self->melexec("workspace -q -rootDirectory");
		my $projdir = $self->melresult();
		$imgdir = "$projdir/$imgdir";
		mkdir("$imgdir");
	}

	# load default plugin renderer if needed
	$self->melexec("getAttr defaultRenderGlobals.currentRenderer");
	my $currentRenderer = $self->melresult();
	$self->loadPluginRenderer($currentRenderer);

	if (@allLayers == 1) {
		# NO layers in the scene (i.e., "defaultRenderLayer" only)

		# load plugin renderer if needed
		$self->melexec("getAttr defaultRenderGlobals.currentRenderer");
		my $currentRenderer = $self->melresult();
		$self->loadPluginRenderer($currentRenderer);

		if(@{$self->{cameras}} > 1) {
			# more than one cameras to render

			# create directory for each camera
			for (@{$self->{cameras}}) {
				(my $cam = $_) =~ s/:/_/g; # replace all ":" with "_"
				my $dir = "$imgdir/$cam";
				warn("INFO: creating image directory for camera [$dir]\n");
				mkdir("$dir");
			}
		}

	} else {
		# some layers defined in the scene (but not necessarily renderable)

		for my $layer (@{$self->{layers}}) {

			# load plugin renderer if needed
			$self->melexec("editRenderLayerGlobals -crl $layer");
			$self->melexec("currentRenderer()");
			my $currentRenderer = $self->melresult();
			$self->loadPluginRenderer($currentRenderer);

			# create dir for each layer to be rendered
			(my $layername = $layer) =~ s/:/_/g; # replace all ":" with "_"
			my $dir = "$imgdir/$layername";
			warn("INFO: creating image directory for layer [$dir]\n");
			mkdir("$dir");

			if(@{$self->{cameras}} > 1) {
				# create a subdir for the camera in the layer's subdir
				for (@{$self->{cameras}}) {
					(my $camname = $_) =~ s/:/_/g; # replace all ":" with "_"
					$dir = "$imgdir/$layername/$camname";
					warn("INFO: creating image directory for layer/camera ".
						 "[$dir]\n");
					mkdir("$dir");
				}
			}
		}
	}

	# Set threads control. This needs to be called after loading
	# plugins above.
	$self->setThreads();

	return $retval;
}

#
# loadPluginRenderer($renderer)
#
sub loadPluginRenderer
{
	my $self = shift;
	my $renderer = shift;
	my $pluginName = "";
	if($renderer eq "mentalRay") {
		$pluginName = "Mayatomr";
	} elsif($renderer eq "mayaVector") {
		$pluginName = "VectorRender";
	} elsif($renderer eq "turtle") {
		$pluginName = "TurtleForMaya";
		my $mayaver = $self->getMayaVersion();
		if ($mayaver < 6.5) {
			die("ERROR: Turtle does not support maya version $mayaver");
		}
		$mayaver *= 10;
		$pluginName .= $mayaver;
	} elsif($renderer eq "_3delight") {
		$pluginName = "3delight_for_maya";
		my $mayaver = $self->getMayaVersion();
		$pluginName .= $mayaver;
	}
	if($pluginName) {
		warn "INFO: loading plugin [$pluginName] for the plugin-renderer " .
			"[$renderer]\n";
		my $cmd = 'if ( ! `pluginInfo -q -l "' . $pluginName . '"` ) ' .
			'{ loadPlugin "' . $pluginName. '"; }';
		$self->melexec($cmd);
	}
	if($renderer eq "turtle") {
		$self->melexec("ilrDefaultNodes(1)");
	}
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

	my $frame = $work->name();

	local $Data::Dumper::Indent = 1;
	print STDERR "\n" . Dumper($work) . "\n";

	# make sure the following attrs are unlocked
	$self->melexec("setAttr -l false defaultRenderGlobals.startFrame");
	$self->melexec("setAttr -l false defaultRenderGlobals.endFrame");
	$self->melexec("setAttr -l false defaultRenderGlobals.byFrameStep");

	$self->melexec("currentTime -e $frame");
	$self->melexec("setAttr defaultRenderGlobals.startFrame $frame");
	$self->melexec("setAttr defaultRenderGlobals.endFrame $frame");
	$self->melexec("setAttr defaultRenderGlobals.byFrameStep 1");

	$self->melexec("getAttr defaultRenderGlobals.modifyExtension");
	my $modifyExt = $self->melresult();
	my $origStartExt;
	if($modifyExt) {
		$self->melexec("getAttr defaultRenderGlobals.startExtension");
		$origStartExt = $self->melresult();
		my $startext = $origStartExt;
		$self->melexec("getAttr defaultRenderGlobals.byExtension");
		my $byext = $self->melresult();
		my $newext = $startext +
			($frame - $self->package->{startFrame}) * $byext;
		$self->melexec("setAttr defaultRenderGlobals.startExtension $newext");

		warn "startext=$startext\n";
		warn "byext=$byext\n";
		warn "newext=$newext\n";
		warn "INFO: adjusting startExtension to $newext\n";
	}


	my $errorCount = 0;
	my @results = ();
	# loop over all cameras
	for my $cam (@{$self->{cameras}}) {
		warn "\n\nINFO: rendering camera [$cam]\n";

		# make the camera renderable
		$self->melexec("setAttr $cam.renderable 1");

		# Now render each layer!
		for my $layer (@{$self->{layers}}) {
			# make the layer renderable
			$self->melexec("setAttr " . $layer .".renderable 1");

			# select the layer
			$self->melexec("editRenderLayerGlobals -crl $layer");

			# get the renderer name for this layer
			$self->melexec("currentRenderer()");
			my $renderer = $self->melresult();

			if(!$renderer) {
				warn "INFO: No layer-specific renderer for layer [$layer]... ".
					"Using defaultRenderGlobals.currentRenderer\n";

				$self->melexec("getAttr defaultRenderGlobals.currentRenderer");
				$renderer = $self->melresult();
			}

			warn "\nINFO: rendering layer [$layer] using renderer " .
				"[$renderer]\n";

			my $successRegex = 'Finished Rendering (.*)\.';
			my $errorRegex = undef;
			my $postFrameCheck = 0;
			my $opts = "";
			#
			# setup renderer-specific options
			#

			if($renderer eq "mayaSoftware") {
				$postFrameCheck = 1;
			} elsif ($renderer eq "mayaHardware") {
				$postFrameCheck = 1;
				$successRegex = 'Rendering frame .* : (.*)';
			} elsif ($renderer eq "mentalRay") {
				$postFrameCheck = 1;

				# verbose log
				$opts = "-v 5 ";
				$self->melexec("if(size(`ls mentalrayGlobals`)) { setAttr mentalrayGlobals.renderVerbosity 5; }");

				# maya2008 and above require the following globals to be set
				#  for verbose output by mental ray
				$self->melexec('global int $g_mrBatchRenderCmdOption_VerbosityOn = true');
				$self->melexec('global int $g_mrBatchRenderCmdOption_Verbosity = 5;');

				if($self->package->{mentalray_satellite} eq
						"Unlimited (8 CPUs)") {
					$opts .= "-lic mu";
				} elsif($self->package->{mentalray_satellite} eq
						"Complete (2 CPUs)") {
					$opts .= "-lic mc";
				} else {
					# use no satelite license by default
					$opts .= "-lic ns";
				}

				$successRegex = 'writing image file (.*) \(frame \d+\)';
			} elsif ($renderer eq "mayaVector") {
				$postFrameCheck = 1;
# 				$successRegex = 'Finished Rendering (.*)';
				$successRegex = 'Output to File:\[(.*)\]';
			} elsif ($renderer eq "gelato") {
				$opts = "-verbosity 2";
# 				$successRegex = 'Wrote \'(.)\'\.';
# 				$errorRegex = "";
			} elsif ($renderer eq "turtle") {
# 				$opts = "-verbosity 2";
				$postFrameCheck = 1;
				# find out the turtle version
				$pluginName = "TurtleForMaya";
				my $mayaver = $self->getMayaVersion();
				if ($mayaver < 6.5) {
					die("ERROR: Turtle does not support maya version $mayaver");
				}
				$mayaver *= 10;
				$pluginName .= $mayaver;
				my $cmd = 'pluginInfo -q -version "' . $pluginName . '"';
				$self->melexec($cmd);
				my $turtle_ver = $self->melresult();

				if($turtle_ver < 3.1) {
					$successRegex = '\[PROGRESS\] Rendering Frame : 100.00 \((.*)\)';
				} else {
					# for turtle 3.1+, we need to enable the "Debug" output verbosity
					$self->melexec('setAttr "TurtleRenderGlobals.debugPrint" 1');
					$successRegex = '\[DEBUG\]\s+Validated the filename (.*)';
				}

			} elsif ($renderer eq "_3delight") {
				$postFrameCheck = 1;
				$successRegex = 'Frame \d+: rendering displays: (.*)';
			}

			#
			# construct mel command for rendering, and run it!
			#

			# parameters are interactive, scenename, layername,
			#  renderer, opts
			my $melcmd = 'mayaBatchRenderProcedure(0, "", "' .
				$layer .'", "'. $renderer . '", "' . $opts . '")';

			# Note: we run a "sleep" to wait for the output
# 			my $perlpath = $Config{'perlpath'};
# 			$melcmd .= "; system (\"$perlpath -e \\\"sleep 1\\\"\");";
			$melcmd .= "; pause -sec 2;";

			if($self->package->{ignoreRenderTimeErrors}) {
				$errorRegex = "";
				$postFrameCheck = 0;
			}

			if ($self->melexec($melcmd, $errorRegex, $successRegex)) {
				# $result should contain the fullpath to the
				# imagefile-- it could be a comma-separated list of
				# files too
				my $result = $self->melresult();
				warn ">>>> result=$result\n";
				my @imagepaths = split /,/, $result;
				my $ipath = $result; # set $ipath to $result here,
                                     # just in case we're skipping the
                                     # postFrameCheck
				if($postFrameCheck) {
					if (not $result) {
						warn "WARNING: melexec() returned success, but ".
							"'result' is empty\n";
# 						$errorCount++;
					} else {
						my $minsize =
							qb::jobconfig("maya", "min_imgsize", 0) || 0;
						for $ipath (@imagepaths) {
							if (not -e $ipath) {
								# check that output file exists
								warn "ERROR: melexec() returned success, but ".
									"the resulting output file [$ipath] does ".
										"not exist\n";
								$errorCount++;
								next;
							}
							# test the output file size
							my $size = -s $ipath;
							if ($size < $minsize) {
								warn "ERROR: the output file size [$size]".
									" is too small (< $minsize bytes) for ".
										"file[$ipath]\n";
								$errorCount++;
								next;
							}
							# at this point, this file pointed to by
							# $ipath exists and is of reasonable
							# size. So, if we're doing multiple
							# cameras, we need to move the image file
							# to the appropriate camera subdir
							if (@{$self->{cameras}} > 1) {
								my ($basename, $path) = fileparse($ipath);
								(my $camname = $cam) =~ s/:/_/g;
								my $newname = "$path/$camname/$basename";
								warn "INFO: moving [$ipath] to [$newname]\n";
								move $ipath, $newname;
								$ipath = $newname;
							}
						} # for(@imagepaths)
					}
				}
				push @results, $ipath;
			} else {
				warn "ERROR: mel command [$melcmd] failed\n";
				warn($self->melresult() . "\n");
				$errorCount++;
			}

			# make the layer non-renderable
			$self->melexec("setAttr " . $layer .".renderable 0");

		}
		# make the camera non-renderable
		$self->melexec("setAttr $cam.renderable 0");
	}
	$work->resultpackage({"outputPaths" => join(',', @results) } );

	if($modifyExt) {
		# restore scene's original startExtension
		$self->melexec("setAttr defaultRenderGlobals.startExtension " .
					   $origStartExt);
	}

	if($errorCount) {
		warn "ERROR: there were at least [$errorCount] errors in processing ".
			"this frame\n";
		return 0;
	}
	return 1;
}


#
# set up render globals
#
sub setupRenderGlobals
{
	my $self = shift;

	# naming
	$self->mayaImageFilePrefix();
	$self->mayaUseMayaFileName();
	$self->mayaStartExtension();
	$self->mayaByExtension();
	$self->mayaAnimationMode();
	$self->mayaOutFormatControl();
	$self->mayaOutFormatExtension();
	$self->mayaPeriodInExtension();
	$self->mayaPutFrameBeforeExtension();
	$self->mayaExtensionPadding();
	$self->mayaMayaFormat();	# corresponds to the "-mf" option

	# output
	$self->mayaImageFormat();
	$self->mayaCreateIprFile();
	$self->mayaEnableDepthMaps();
	$self->mayaLocalDepthMaps();
	$self->mayaGammaCorrection();

	# image geometry
	$self->mayaXResolution();
	$self->mayaYResolution();
	$self->mayaDeviceAspectRatio();
#	 $self->mayaPixelAspect();
	$self->mayaBottomRegion();
	$self->mayaLeftRegion();
	$self->mayaRightRegion();
	$self->mayaTopRegion();

	# camera
#	 $self->mayaAspectRatio();
	$self->mayaImageChannel();
	$self->mayaMaskChannel();
	$self->mayaDepthChannel();
	$self->mayaIgnoreFilmGate();

	# motion blur
	$self->mayaShutterAngle();
	$self->mayaMotionBlur();
	$self->mayaMotionBlurType();
	$self->mayaMotionBlurByFrame();
	$self->mayaMotionBlur3D();
	$self->mayaBlurLength();
	$self->mayaBlurSharpness();
	$self->mayaSmoothValue();
	$self->mayaSmoothColor();
	$self->mayaKeepMotionVector();
	$self->mayaBlur2DMemoryCap();

	# MEL
	$self->mayaPreRenderMel();
	$self->mayaPostRenderMel();

	# contrast thresholds
	$self->mayaRedThreshold();
	$self->mayaBlueThreshold();
	$self->mayaGreenThreshold();
	$self->mayaCoverageThreshold();

	# compositing
	$self->mayaComposite();
	$self->mayaCompositeThreshold();

	# optimization and resources
	$self->mayaShadowPass();
	$self->mayaUseFileCache();
	$self->mayaOptimizeInstances();
	$self->mayaReuseTessellations();
	$self->mayaUseDisplacementBoundingBox();
	$self->mayaTileWidth();
	$self->mayaTileHeight();
	$self->mayaMaximumMemory();
	$self->mayaNumCpusToUse();

	# ray tracing
	$self->mayaEnableRaytracing();
	$self->mayaRTRefractions();
	$self->mayaRTReflections();
	$self->mayaRTShadows();

	# anti-aliasing
	$self->mayaEdgeAntiAliasing();
	$self->mayaUseMultiPixelFilter();
	$self->mayaPixelFilterType();
	$self->mayaShadingSamples();
	$self->mayaMaxShadingSamples();
	$self->mayaVisibilitySamples();
	$self->mayaMaxVisibilitySamples();
	$self->mayaVolumeSamples();
	$self->mayaParticleSamples();

	# render layers
	$self->mayaRenderLayerSubdirs();
	$self->mayaRenderAllLayers();
	$self->mayaRenderRenderableLayers();
	$self->mayaRenderLayer();

	return 0;
}


sub mayaByExtension
{
	my ($self, $by) = @_;
	$by = $self->package->byExtension() if @_ < 2;
	return if not defined $by;
	my $command = sprintf('setAttr defaultRenderGlobals.modifyExtension 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.byExtension %s;',
						$by);
	$self->melexec($command);
	return;
}
sub mayaAnimationMode
{
	my ($self, $animation) = @_;
	$animation = $self->package->animation() if @_ < 2;
	return if not defined $animation;
	my $command = sprintf('setAttr defaultRenderGlobals.animation %s;',
						  $animation);
	$self->melexec($command);
	return;
}
sub mayaOutFormatControl
{
	my ($self, $control) = @_;
	$control = $self->package->outFormatControl() if @_ < 2;
	return if not defined $control;
	my $command = sprintf('setAttr defaultRenderGlobals.outFormatControl %s;',
						  $control);
	$self->melexec($command);
	return;
}
sub mayaOutFormatExtension
{
	my ($self, $ext) = @_;
	$ext = $self->package->outFormatExt() if @_ < 2;
	return if not defined $ext;
	my $command = sprintf('setAttr defaultRenderGlobals.outFormatExt -type "string" "%s";',
						  $ext);
	$self->melexec($command);
	return;
}
sub mayaPeriodInExtension
{
	my ($self, $period) = @_;
	$period = $self->package->periodInExt() if @_ < 2;
	return if not defined $period;
	my $command = sprintf('setAttr defaultRenderGlobals.periodInExt %s;',
						  $period);
	$self->melexec($command);
	return;
}	 
sub mayaPutFrameBeforeExtension
{
	my ($self, $put) = @_;
	$put = $self->package->putFrameBeforeExt() if @_ < 2;
	return if not defined $put;
	my $command = sprintf('setAttr defaultRenderGlobals.putFrameBeforeExt %s;',
						  $put);
	$self->melexec($command);
	return;
}	 
sub mayaExtensionPadding
{
	my ($self, $pad) = @_;
	$pad = $self->package->extensionPadding() if @_ < 2;
	return if not defined $pad;
	my $command = sprintf('setAttr defaultRenderGlobals.extensionPadding %s;',
						  $pad);
	$self->melexec($command);
	return;
}	 

sub mayaMayaFormat
{
	my ($self, $use) = @_;
	$use = $self->package->mayaFormat() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderGlobals.outFormatControl %d;',
						  $use ? 0 : 1);
	$self->melexec($command);
	return;
}

sub mayaCreateIprFile()
{
	my ($self, $create) = @_;
	$create = $self->package->iprFile() if @_ < 2;
	return if not defined $create;
	my $command = sprintf('setAttr defaultRenderGlobals.iprFile %s;',
						  $create);
	$self->melexec($command);
	return;
}	 
sub mayaEnableDepthMaps
{
	my ($self, $enable) = @_;
	$enable = $self->package->enableDepthMaps() if @_ < 2;
	return if not defined $enable;
	my $command = sprintf('setAttr defaultRenderGlobals.enableDepthMaps %s;',
						  $enable);
	$self->melexec($command);
	return;
}	 
sub mayaLocalDepthMaps
{
	my ($self, $localDM) = @_;
	$localDM = $self->package->localdm() if @_ < 2;
	return if not defined $localDM;
	my $command = sprintf('workspace -rt "%s" "%s";', 
						  "depth", $self->createTempDir());
	$self->melexec($command);
	return;
}
sub mayaGammaCorrection
{
	my ($self, $gamma) = @_;
	$gamma = $self->package->gamma() if @_ < 2;
	return if not defined $gamma;
	my $command = sprintf('setAttr defaultRenderGlobals.gammaCorrection %s;',
						  $gamma);
	$self->melexec($command);
	return;
}
sub mayaImageFilePrefix
{
	my ($self, $name) = @_;
	$name = $self->package->image() if @_ < 2;
	return if not defined $name;
	my $command = sprintf('setAttr defaultRenderGlobals.imageFilePrefix -type "string" "%s";', 
						  $name);
	$self->melexec($command);
	return;
}
sub mayaImageFormat
{
	my ($self, $format) = @_;
	$format = $self->package->outputFormat() if @_ < 2;
	return if not defined $format;
	my %formatTable = (
					   gif	  => 0,
					   soft	  => 1,	 softimage => 1,
					   rla	  => 2,	 wave	   => 2,  wavefront => 2,
					   tif	  => 3,	 tiff	   => 3,
					   tif16  => 4,	 tiff16	   => 4,
					   sgi	  => 5,	 rgb	   => 5,
					   alias  => 6,	 als	   => 6,  pix		=> 6,
					   iff	  => 7,	 tdi	   => 7,  explore	=> 7, maya => 7,
					   jpg	  => 8,	 jpeg	   => 8,
					   eps	  => 9,
					   maya16 => 10, iff16	   => 10, 
					   cineon => 11, cin	   => 11, fido		=> 11,
					   qtl	  => 12, quantel   => 12, yuv		=> 12,
					   sgi16  => 13, rgb16	   => 13,
					   tga	  => 19, targa	   => 19,
					   bmp	  => 20,
					   sgimv  => 21, mv		   => 21, 
					   qt	  => 22, Quicktime => 22, QuickTime => 22,
					   AVI	  => 23, avi	   => 23
					   );
	my $formatNum = $formatTable{$format};
	my $command = sprintf('setAttr defaultRenderGlobals.imageFormat %s;', 
						  $formatNum);
	$self->melexec($command);
	return;
}
sub mayaMaximumMemory
{
	my ($self, $mem) = @_;
	$mem = $self->package->maximumMemory() if @_ < 2;
	return if not defined $mem;
	my $command = sprintf('setAttr defaultRenderGlobals.maximumMemory %s;', 
						  $mem);
	$self->melexec($command);
	return;
}
sub mayaNumCpusToUse
{
	my ($self, $cpus) = @_;
	$cpus = $self->package->numberOfProcessors() if @_ < 2;
	return if not defined $cpus;
	my $command = sprintf('setAttr defaultRenderGlobals.numCpusToUse %s;', 
						  $cpus);
	$self->melexec($command);
	return;
}
sub mayaRenderDirectory
{
	my ($self, $directory) = @_;
	$directory = $self->package->renderDirectory() if @_ < 2;
	return if not defined $directory;
	my $command = sprintf('workspace -rt "%s" "%s";', "images",
						  $directory);
	$self->melexec($command);
	return;
}
sub mayaIPRDirectory
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
sub mayaShutterAngle
{
	my ($self, $angle) = @_;
	$angle = $self->package->shutterAngle() if @_ < 2;
	return if not defined $angle;
	my $command = sprintf('camera -edit -shutterAngle %s "%s";',
						  $angle, $self->package->cameraOverride());
	$self->melexec($command);
	return;
}
sub mayaImageChannel
{
	my ($self, $channel) = @_;
	$channel = $self->package->imageChannel() if @_ < 2;
	return if not defined $channel;
	my $command = sprintf('setAttr %s.image %s;',
						  $self->package->cameraOverride(), $channel);
	$self->melexec($command);
	return;
}
sub mayaMaskChannel
{
	my ($self, $channel) = @_;
	$channel = $self->package->maskChannel() if @_ < 2;
	return if not defined $channel;
	my $command = sprintf('setAttr %s.mask %s;',
						  $self->package->cameraOverride(), $channel);
	$self->melexec($command);
	return;
}
sub mayaDepthChannel
{
	my ($self, $channel) = @_;
	$channel = $self->package->depthChannel() if @_ < 2;
	return if not defined $channel;
	my $command = sprintf('setAttr %s.depth %s;',
						  $self->package->cameraOverride(), $channel);
	$self->melexec($command);
	return;
}
sub mayaIgnoreFilmGate
{
	my ($self, $ignore) = @_;
	$ignore = $self->package->ignoreFilmGate() if @_ < 2;
	return if not defined $ignore;
	my $command = sprintf('setAttr defaultRenderGlobals.ignoreFilmGate %s;',
						  $ignore);
	$self->melexec($command);
	return;
}
sub mayaDeviceAspectRatio
{
	my ($self, $aspect) = @_;
	$aspect = $self->package->deviceAspectRatio() if @_ < 2;
	return if not defined $aspect;
	my $command = sprintf('setAttr defaultResolution.deviceAspectRatio %s;',
						  $aspect);
	$self->melexec($command);
	return;
}
sub mayaPixelAspect
{
	my ($self, $aspect) = @_;
	$aspect = $self->package->aspectRatio() if @_ < 2;
	return if not defined $aspect;
	my $command = sprintf('setAttr defaultResolution.pixelAspect %s;',
						  $aspect);
	$self->melexec($command);
	return;
}

#
# MOTION BLUR
#
sub mayaMotionBlur
{
	my ($self, $blur, $type) = @_;
	$blur = $self->package->motionBlur() if @_ < 2;
	$type = $self->package->motionBlurType() if @_ < 3;
	return if not defined $blur;
	$self->package->motionBlurType(1) if not defined $type;
	my $command = sprintf('setAttr defaultRenderGlobals.motionBlur %s;',
						  $blur);
	$self->melexec($command);

	$self->mayaMotionBlurType($type) if (@_ == 3);
	return;
}
sub mayaMotionBlurType
{
	my ($self, $type) = @_;
	$type = $self->package->motionBlurType() if @_ < 2;
	return if not defined $type;
	my $command = sprintf('setAttr defaultRenderGlobals.motionBlurType %s;',
						  $type);
	$self->melexec($command);
	return;
}
sub mayaMotionBlurByFrame
{
	my ($self, $blur) = @_;
	$blur = $self->package->motionBlurByFrame() if @_ < 2;
	return if not defined $blur;
	my $command = sprintf('setAttr defaultRenderGlobals.motionBlurByFrame %s;',
						  $blur);
	$self->melexec($command);
	return;
}
sub mayaMotionBlur3D
{
	my ($self, $blur) = @_;
	$blur = $self->package->motionBlur3D() if @_ < 2;
	return if not defined $blur;
	$self->mayaMotionBlurType(1);
	return;
}
sub mayaBlurLength
{
	my ($self, $length) = @_;
	$length = $self->package->blurLength() if @_ < 2;
	return if not defined $length;
	my $command = sprintf('setAttr defaultRenderGlobals.blurLength %s;',
						  $length);
	$self->melexec($command);
	return;
}
sub mayaBlurSharpness
{
	my ($self, $sharp) = @_;
	$sharp = $self->package->blurSharpness() if @_ < 2;
	return if not defined $sharp;
	my $command = sprintf('setAttr defaultRenderGlobals.blurSharpness %s;',
						  $sharp);
	$self->melexec($command);
	return;
}
sub mayaSmoothValue
{
	my ($self, $value) = @_;
	$value = $self->package->smoothValue() if @_ < 2;
	return if not defined $value;
	my $command = sprintf('setAttr defaultRenderGlobals.smoothValue %s;',
						  $value);
	$self->melexec($command);
	return;
}
sub mayaSmoothColor
{
	my ($self, $color) = @_;
	$color = $self->package->smoothColor() if @_ < 2;
	return if not defined $color; 
	my $command = sprintf('setAttr defaultRenderGlobals.smoothColor %s;',
						  $color);
	$self->melexec($command);
	return;
}
sub mayaKeepMotionVector
{
	my ($self, $keep) = @_;
	$keep = $self->package->keepMotionVector() if @_ < 2;
	return if not defined $keep;
	my $command = sprintf('setAttr defaultRenderGlobals.keepMotionVector %s;',
						  $keep);
	$self->melexec($command);
	return;
}
sub mayaBlur2DMemoryCap
{
	my ($self, $cap) = @_;
	$cap = $self->package->blur2DMemoryCap() if @_ < 2;
	return if not defined $cap;
	my $command = sprintf('setAttr defaultRenderGlobals.blur2DMemoryCap %s;',
						  $cap);
	$self->melexec($command);
	return;
}
#
# MEL
#
sub mayaPreRenderMel
{
	my ($self, $mel) = @_;
	$mel = $self->package->preRenderMel() if @_ < 2;
	return if not defined $mel;
	my $command = sprintf('setAttr defaultRenderGlobals.preRenderMel -type "string" "%s";',
						  $mel);
	$self->melexec($command);
	return;
}
sub mayaPostRenderMel
{
	my ($self, $mel) = @_;
	$mel = $self->package->postRenderMel() if @_ < 2;
	return if not defined $mel;
	my $command = sprintf('setAttr defaultRenderGlobals.postRenderMel -type "string" "%s";',
						  $mel);
	$self->melexec($command);
	return;
}
#
# CONTRAST THRESHOLDS
#
sub mayaRedThreshold
{
	my ($self, $threshold) = @_;
	$threshold = $self->package->redThreshold() if @_ < 2;
	return if not defined $threshold;
	my $command = sprintf('setAttr defaultRenderQuality.redThreshold %s;',
						  $threshold);
	$self->melexec($command);
	return;
}
sub mayaBlueThreshold
{
	my ($self, $threshold) = @_;
	$threshold = $self->package->blueThreshold() if @_ < 2;
	return if not defined $threshold;
	my $command = sprintf('setAttr defaultRenderQuality.blueThreshold %s;',
						  $threshold);
	$self->melexec($command);
	return;
}
sub mayaGreenThreshold
{
	my ($self, $threshold) = @_;
	$threshold = $self->package->greenThreshold() if @_ < 2;
	return if not defined $threshold;
	my $command = sprintf('setAttr defaultRenderQuality.greenThreshold %s;',
						  $threshold);
	$self->melexec($command);
	return;
}
sub mayaCoverageThreshold
{
	my ($self, $threshold) = @_;
	$threshold = $self->package->coverageThreshold() if @_ < 2;
	return if not defined $threshold;
	my $command = sprintf('setAttr defaultRenderQuality.coverageThreshold %s;',
						  $threshold);
	$self->melexec($command);
	return;
}
#
# COMPOSITING
#
sub mayaComposite
{
	my ($self, $composite) = @_;
	$composite = $self->package->composite() if @_ < 2;
	return if not defined $composite;
	my $command = sprintf('setAttr defaultRenderGlobals.composite %s;',
						  $composite);
	$self->melexec($command);
	return;
}
sub mayaCompositeThreshold
{
	my ($self, $threshold) = @_;
	$threshold = $self->package->compositeThreshold() if @_ < 2;
	return if not defined $threshold;
	my $command = sprintf('setAttr defaultRenderGlobals.compositeThreshold %s;',
						  $threshold);
	$self->melexec($command);
	return;
}

sub mayaShadowPass
{
	my ($self, $pass) = @_;
	$pass = $self->package->shadowPass() if @_ < 2;
	return if not defined $pass;
	my $command = sprintf('setAttr defaultRenderGlobals.shadowPass %s;',
						  $pass);
	$self->melexec($command);
	return;
}
sub mayaStartExtension
{
	my ($self, $start) = @_;
	$start = $self->package->startExtension() if @_ < 2;
	return if not defined $start;
	my $command = sprintf('setAttr defaultRenderGlobals.modifyExtension 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.startExtension %s;',
						$start);
	$self->melexec($command);
	return;
}
#
# RENDER REGIONS
#
sub mayaBottomRegion
{
	my ($self, $yl) = @_;
	$yl = $self->package->yLow() if @_ < 2;
	return if not defined $yl;
	my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.bottomRegion %s;',
						$yl);
	$self->melexec($command);
	return;
}
sub mayaLeftRegion
{
	my ($self, $xl) = @_;
	$xl = $self->package->xLeft() if @_ < 2;
	return if not defined $xl;
	my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.leftRegion %s;',
						$xl);
	$self->melexec($command);
	return;
}
sub mayaRightRegion
{
	my ($self, $xr) = @_;
	$xr = $self->package->xRight() if @_ < 2;
	return if not defined $xr;
	my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.rightRegion %s;',
						$xr);
	$self->melexec($command);
	return;
}
sub mayaTopRegion
{
	my ($self, $yh) = @_;
	$yh = $self->package->yHigh() if @_ < 2;
	return if not defined $yh;
	my $command = sprintf('setAttr defaultRenderGlobals.useRenderRegion 1; ');
	$command .= sprintf('setAttr defaultRenderGlobals.topRegion %s;',
						$yh);
	$self->melexec($command);
	return;
}
sub mayaUseFrameExtension
{
	my ($self, $use) = @_;
	$use = $self->package->useFrameExtension() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderGlobals.useFrameExt %s;',
						  $use);
	$self->melexec($command);
	return;
}
sub mayaUseMayaFileName
{
	my ($self, $use) = @_;
	$use = $self->package->mayaExtension() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderGlobals.useMayaFileName %s;',
						  $use);
	$self->melexec($command);
	return;
}	 
#
# RESOLUTION
#
sub mayaXResolution
{
	my ($self, $x) = @_;
	$x = $self->package->xResolution() if @_ < 2;
	return if not defined $x;
	my $command = sprintf('setAttr defaultResolution.width %s;',
						  $x);
	$self->melexec($command);
	return;
}
sub mayaYResolution
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
# TILING
#
sub mayaTileWidth
{
	my ($self, $width) = @_;
	$width = $self->package->tileWidth() if @_ < 2;
	return if not defined $width;
	my $command = sprintf('setAttr defaultRenderGlobals.tileWidth %s;',
						  $width);
	$self->melexec($command);
	return;
}
sub mayaTileHeight
{
	my ($self, $height) = @_;
	$height = $self->package->tileHeight() if @_ < 2;
	return if not defined $height;
	my $command = sprintf('setAttr defaultRenderGlobals.tileHeight %s;',
						  $height);
	$self->melexec($command);
	return;
}
#
# TESSELLATION
#
sub mayaUseFileCache
{
	my ($self, $use) = @_;
	$use = $self->package->useFileCache() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderGlobals.useFileCache %s;',
						  $use);
	$self->melexec($command);
	return;
}
sub mayaOptimizeInstances
{
	my ($self, $optimize) = @_;
	$optimize = $self->package->optimizeInstances() if @_ < 2;
	return if not defined $optimize;
	my $command = sprintf('setAttr defaultRenderGlobals.optimizeInstances %s;',
						  $optimize);
	$self->melexec($command);
	return;
}
sub mayaReuseTessellations
{
	my ($self, $reuse) = @_;
	$reuse = $self->package->reuseTessellations() if @_ < 2;
	return if not defined $reuse;
	my $command = sprintf('setAttr defaultRenderGlobals.reuseTessellations %s;',
						  $reuse);
	$self->melexec($command);
	return;
}
sub mayaUseDisplacementBoundingBox
{
	my ($self, $use) = @_;
	$use = $self->package->useDisplacementBbox() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderGlobals.useDisplacementBoundingBox %s;',
						  $use);
	$self->melexec($command);
	return;
}

#
# RAY-TRACING
#
sub mayaEnableRaytracing
{
	my ($self, $enable) = @_;
	$enable = $self->package->enableRayTrace() if @_ < 2;
	return if not defined $enable;
	my $command = sprintf('setAttr defaultRenderQuality.enableRaytracing %s;',
						  $enable);
	$self->melexec($command);
	return;
}
sub mayaRTRefractions
{
	my ($self, $refractions) = @_;
	$refractions = $self->package->refractions() if @_ < 2;
	return if not defined $refractions;
	my $command = sprintf('setAttr defaultRenderQuality.refractions %s;',
						  $refractions);
	$self->melexec($command);
	return;
}
sub mayaRTReflections
{
	my ($self, $reflections) = @_;
	$reflections = $self->package->reflections() if @_ < 2;
	return if not defined $reflections;
	my $command = sprintf('setAttr defaultRenderQuality.reflections %s;',
						  $reflections);
	$self->melexec($command);
	return;
}
sub mayaRTShadows
{
	my ($self, $shadows) = @_;
	$shadows = $self->package->shadowLevel() if not @_ < 2;
	return if not defined $shadows;
	my $command = sprintf('setAttr defaultRenderQuality.shadows %s;',
						  $shadows);
	$self->melexec($command);
	return;
}

#
# ANTIALIASING
#
sub mayaEdgeAntiAliasing
{
	my ($self, $quality) = @_;
	$quality = $self->package->edgeAntiAliasing() if @_ < 2;
	return if not defined $quality;
	my %antiAliasingQualityTable = (
									highest => 0,
									high	=> 1,
									medium	=> 2,
									low		=> 3
									);
	my $qualityNum = $antiAliasingQualityTable{$quality};
	my $command = sprintf('setAttr defaultRenderQuality.edgeAntiAliasing %s;',
						  $qualityNum);
	$self->melexec($command);
	return;
}
sub mayaUseMultiPixelFilter
{
	my ($self, $use) = @_;
	$use = $self->package->useFilter() if @_ < 2;
	return if not defined $use;
	my $command = sprintf('setAttr defaultRenderQuality.useMultiPixelFilter %s;',
						  $use);
	$self->melexec($command);
	return;
}
sub mayaPixelFilterType
{
	my ($self, $filter) = @_;
	$filter = $self->package->pixelFilterType() if @_ < 2;
	return if not defined $filter;
	my %filterTable = (
					   box				  => 0, 
					   triangle			  => 2, 
					   gaussian			  => 4,
					   quadraticbspline	  => 5, 
					   plugin			  => 1000
					   );
	my $typeNum = $filterTable{$filter};
	my $command = sprintf('setAttr defaultRenderQuality.pixelFilterType %s;',
						  $typeNum);
	$self->melexec($command);
	return;
}
sub mayaShadingSamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->shadingSamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.shadingSamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}
sub mayaMaxShadingSamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->maxShadingSamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.maxShadingSamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}
sub mayaVisibilitySamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->visibilitySamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.visibilitySamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}
sub mayaMaxVisibilitySamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->maxVisibilitySamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.maxVisibilitySamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}
sub mayaVolumeSamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->volumeSamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.volumeSamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}
sub mayaParticleSamples
{
	my ($self, $samples) = @_;
	$samples = $self->package->particleSamples() if @_ < 2;
	return if not defined $samples;
	my $command = sprintf('setAttr defaultRenderQuality.particleSamples %s;',
						  $samples);
	$self->melexec($command);
	return;
}

sub mayaRenderLayerSubdirs
{
	my ($self, $subdirs) = @_;
	$subdirs = $self->package->renderLayerSubdirs() if @_ < 2;
	return if not defined $subdirs;
	my $command = sprintf('setAttr defaultRenderGlobals.renderLayerSubdirs %s;',
						  $subdirs);
	$self->melexec($command);
	return;
}

sub mayaRenderAllLayers
{
	my ($self, $all) = @_;
	$all = $self->package->renderAllLayers() if @_ < 2;
	return if not $all;
	my $command = sprintf('setAttr defaultRenderGlobals.renderAll 1;');
	$self->melexec($command);
	return;
}

sub mayaRenderRenderableLayers
{
	my ($self, $renderable) = @_;
	$renderable = $self->package->renderRenderableLayers() if @_ < 2;
	return if not $renderable;
	my $command = sprintf('setAttr defaultRenderGlobals.renderLayerEnable 1;');
	$self->melexec($command);
	return;
}

sub mayaRenderLayer
{
	my ($self, $rLayer) = @_;
	$rLayer = $self->package->renderLayer() if @_ < 2;
	return if not defined $rLayer;
	my $command = sprintf('setAttr defaultRenderGlobals.renderLayerEnable 1; ');
	$command .= sprintf('for ($layer in `listConnections renderLayerManager`) { ');
	$command .= sprintf('if ($layer == "%s") { ', $rLayer);
	$command .= sprintf('setAttr ($layer + ".renderable") 1; } ');
	$command .= sprintf('else { setAttr ($layer + ".renderable") 0; }}');
	$self->melexec($command);
	return;
}

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

	my $command = sprintf('setAttr defaultRenderGlobals.startFrame %s;',
						  $frame);
	$self->melexec($command);
	return;
}
sub _mayaEndFrame
{
	my ($self, $frame) = @_;

	my $command = sprintf('setAttr defaultRenderGlobals.endFrame %s;',
						  $frame);
	$self->melexec($command);
	return;
}	 
sub _mayaFrameStep
{
	my ($self, $step) = @_;

	my $command = sprintf('setAttr defaultRenderGlobals.byFrameStep %s;',
						  $step);
	$self->melexec($command);
	return;
}

1;
