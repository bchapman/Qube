###########################################################################
#
#      Copyright: Pipelinefx @ 2006
#
###########################################################################
#
# Package.pm -- job packaging module
#
###########################################################################

package maya::Package;

use strict;

sub new
{
	my ($class, %args) = @_;
	my $self = {};
	bless ($self, $class);
	$self->_init(%args);
	return $self;
}

sub _init
{
	my ($self, %args) = @_;
	$self->{$_} = $args{$_} for (keys %args);
	return $self;
}

###########################################################################
#
# accessor methods
#
###########################################################################

sub mayaVersion
{
	my ($self, $ver) = @_;
	$self->{mayaVersion} = $ver if @_ > 1;
	return $self->{mayaVersion};
}

sub startFrame
{
	my ($self, $frame) = @_;
	$self->{startFrame} = $frame if @_ > 1;
	return $self->{startFrame};
}

sub endFrame
{
	my ($self, $frame) = @_;
	$self->{endFrame} = $frame if @_ > 1;
	return $self->{endFrame};
}

sub byFrame
{
	my ($self, $by) = @_;
	$self->{byFrame} = $by if @_ > 1;
	return $self->{byFrame};
}

sub startExtension
{
	my ($self, $extension) = @_;
	$self->{startExtension} = $extension if @_ > 1;
	return $self->{startExtension};
}

sub byExtension
{
	my ($self, $extension) = @_;
	$self->{byExtension} = $extension if @_ > 1;
	return $self->{byExtension};
}

sub extensionPadding
{
	my ($self, $padding) = @_;
	$self->{extensionPadding} = $padding if @_ > 1;
	return $self->{extensionPadding};
}

sub animation
{
	my ($self, $animation) = @_;
	$self->{animation} = $animation if @_ > 1;
	return $self->{animation};
}

sub outFormatControl
{
	my ($self, $control) = @_;
	$self->{outFormatControl} = $control if @_ > 1;
	return $self->{outFormatControl};
}

sub outFormatExt
{
	my ($self, $ext) = @_;
	$self->{outFormatExt} = $ext if @_ > 1;
	return $self->{outFormatExt};
}

sub periodInExt
{
	my ($self, $period) = @_;
	$self->{periodInExt} = $period if @_ > 1;
	return $self->{periodInExt};
}

sub putFrameBeforeExt
{
	my ($self, $put) = @_;
	$self->{putFrameBeforeExt} = $put if @_ > 1;
	return $self->{putFrameBeforeExt};
}

sub project
{
	my ($self, $project) = @_;
	$self->{project} = $project if @_ > 1;
	return $self->_convertToMayaNative($self->{project});
}

sub renderDirectory
{
	my ($self, $directory) = @_;
	$self->{renderDirectory} = $directory if @_ > 1;
	return $self->_convertToMayaNative($self->{renderDirectory});
}

sub iprDirectory
{
	my ($self, $directory) = @_;
	$self->{iprDirectory} = $directory if @_ > 1;
	return $self->_convertToMayaNative($self->{iprDirectory});
}

sub image
{
	my ($self, $image) = @_;
	$self->{image} = $image if @_ > 1;
	return $self->{image};
}

sub imageTemplate
{
	my ($self, $imageTemplate) = @_;
	$self->{imageTemplate} = $imageTemplate if @_ > 1;
	return $self->{imageTemplate};
}

sub mayaExtension
{
	my ($self, $extension) = @_;
	$self->{mayaExtension} = $extension if @_ > 1;
	return $self->{mayaExtension};
}

sub mayaFormat
{
	my ($self, $format) = @_;
	$self->{mayaFormat} = $format if @_ > 1;
	return $self->{mayaFormat};
}

sub cameraOverride
{
	my ($self, $cameraArrayRef) = @_;
	$self->{cameraOverride} = $cameraArrayRef if @_ > 1;
	return $self->{cameraOverride};
}

sub imageChannel
{
	my ($self, $channel) = @_;
	$self->{imageChannel} = $channel if @_ > 1;
	return $self->{imageChannel};
}

sub maskChannel
{
	my ($self, $channel) = @_;
	$self->{maskChannel} = $channel if @_ > 1;
	return $self->{maskChannel};
}

sub depthChannel
{
	my ($self, $channel) = @_;
	$self->{depthChannel} = $channel if @_ > 1;
	return $self->{depthChannel};
}

sub preRenderMel
{
	my ($self, $mel) = @_;
	$self->{preRenderMel} = $mel if @_ > 1;
	return $self->{preRenderMel};
}

sub postRenderMel
{
	my ($self, $mel) = @_;
	$self->{postRenderMel} = $mel if @_ > 1;
	return $self->{postRenderMel};
}

sub gamma
{
	my ($self, $gamma) = @_;
	$self->{gamma} = $gamma if @_ > 1;
	return $self->{gamma};
}

sub composite
{
	my ($self, $composite) = @_;
	$self->{composite} = $composite if @_ > 1;
	return $self->{composite};
}

sub compositeThreshold
{
	my ($self, $compositeThreshold) = @_;
	$self->{compositeThreshold} = $compositeThreshold if @_ > 1;
	return $self->{compositeThreshold};
}

sub ignoreFilmGate
{
	my ($self, $ignore) = @_;
	$self->{ignoreFilmGate} = $ignore if @_ > 1;
	return $self->{ignoreFilmGate};
}

sub imageHeight
{
	my ($self, $height) = @_;
	$self->{imageHeight} = $height if @_ > 1;
	return $self->{imageHeight};
}

sub imageWidth
{
	my ($self, $width) = @_;
	$self->{imageWidth} = $width if @_ > 1;
	return $self->{imageWidth};
}

sub deviceAspectRatio
{
	my ($self, $aspect) = @_;
	$self->{deviceAspectRatio} = $aspect if @_ > 1;
	return $self->{deviceAspectRatio};
}

sub aspectRatio
{
	my ($self, $aspect) = @_;
	$self->{aspectRatio} = $aspect if @_ > 1;
	return $self->{aspectRatio};
}

sub maximumMemory
{
	my ($self, $memory) = @_;
	$self->{maximumMemory} = $memory if @_ > 1;
	return $self->{maximumMemory};
}

sub motionBlur
{
	my ($self, $blur) = @_;
	$self->{motionBlur} = $blur if @_ > 1;
	return $self->{motionBlur};
}

sub motionBlurByFrame
{
	my ($self, $blur) = @_;
	$self->{motionBlurByFrame} = $blur if @_ > 1;
	return $self->{motionBlurByFrame};
}

sub shutterAngle
{
	my ($self, $angle) = @_;
	$self->{shutterAngle} = $angle if @_ > 1;
	return $self->{shutterAngle};
}

sub motionBlurType
{
	my ($self, $type) = @_;
	$self->{motionBlurType} = $self->{motionBlur3D}
		if (not defined $self->{motionBlurType}) and 
			defined $self->{motionBlur3D};
	$self->{motionBlurType} = $type if @_ > 1;
	return $self->{motionBlurType};
}

sub motionBlur3D
{
	my ($self, $blur) = @_;
	$self->{motionBlur3D} = $blur if @_ > 1;
	return $self->{motionBlur3D};
}

sub motionBlur2D
{
	my ($self, $blur) = @_;
	$self->motionBlur3D(!$blur) if @_ > 1;
	return undef if (not defined $self->motionBlur3D);
	return $self->motionBlur3D() ? 0 : 1;
}

sub blurLength
{
	my ($self, $length) = @_;
	$self->{blurLength} = $length if @_ > 1;
	return $self->{blurLength};
}

sub blurSharpness
{
	my ($self, $sharp) = @_;
	$self->{blurSharpness} = $sharp if @_ > 1;
	return $self->{blurSharpness};
}

sub smoothValue
{
	my ($self, $value) = @_;
	$self->{smoothValue} = $value if @_ > 1;
	return $self->{smoothValue};
}

sub smoothColor
{
	my ($self, $color) = @_;
	$self->{smoothColor} = $color if @_ > 1;
	return $self->{smoothColor};
}

sub keepMotionVector
{
	my ($self, $keep) = @_;
	$self->{keepMotionVector} = $keep if @_ > 1;
	return $self->{keepMotionVector};
}

sub blur2DMemoryCap
{
	my ($self, $cap) = @_;
	$self->{blur2DMemoryCap} = $cap if @_ > 1;
	return $self->{blur2DMemoryCap};
}

sub useFileCache
{
	my ($self, $use) = @_;
	$self->{useFileCache} = $use if @_ > 1;
	return $self->{useFileCache};
}

sub optimizeInstances
{
	my ($self, $optimize) = @_;
	$self->{optimizeInstances} = $optimize if @_ > 1;
	return $self->{optimizeInstances};
}

sub reuseTessellations
{
	my ($self, $reuse) = @_;
	$self->{reuseTessellations} = $reuse if @_ > 1;
	return $self->{reuseTessellations};
}

sub useDisplacementBbox
{
	my ($self, $use) = @_;
	$self->{useDisplacementBbox} = $use if @_ > 1;
	return $self->{useDisplacementBbox};
}

sub enableDepthMaps
{
	my ($self, $enable) = @_;
	$self->{enableDepthMaps} = $enable if @_ > 1;
	return $self->{enableDepthMaps};
}

sub enableRayTrace
{
	my ($self, $enable) = @_;
	$self->{enableRayTrace} = $enable if @_ > 1;
	return $self->{enableRayTrace};
}

sub reflections
{
	my ($self, $reflections) = @_;
	$self->{reflections} = $reflections if @_ > 1;
	return $self->{reflections};
}

sub refractions
{
	my ($self, $refractions) = @_;
	$self->{refractions} = $refractions if @_ > 1;
	return $self->{refractions};
}

sub renderLayers
{
	my ($self, $layers) = @_;
	$self->{renderLayers} = $layers if @_ > 1;
	return $self->{renderLayers};
}

sub renderPasses
{
	my ($self, $render) = @_;
	$self->{renderPasses} = $render if @_ > 1;
	return $self->{renderPasses};
}

sub renderSubdirs
{
	my ($self, $render) = @_;
	$self->{renderSubdirs} = $render if @_ > 1;
	return $self->{renderSubdirs};
}

sub shadowLevel
{
	my ($self, $level) = @_;
	$self->{shadowLevel} = $level if @_ > 1;
	return $self->{shadowLevel};
}

sub edgeAntiAliasing
{
	my ($self, $aa) = @_;
	$self->{edgeAntiAliasing} = $aa if @_ > 1;
	return $self->{edgeAntiAliasing};
}

sub useFilter
{
	my ($self, $use) = @_;
	$self->{useFilter} = $use if @_ > 1;
	return $self->{useFilter};
}

sub pixelFilterType
{
	my ($self, $type) = @_;
	$self->{pixelFilterType} = $type if @_ > 1;
	return $self->{pixelFilterType};
}

sub shadingSamples
{
	my ($self, $samples) = @_;
	$self->{shadingSamples} = $samples if @_ > 1;
	return $self->{shadingSamples};
}

sub maxShadingSamples
{
	my ($self, $samples) = @_;
	$self->{maxShadingSamples} = $samples if @_ > 1;
	return $self->{maxShadingSamples};
}

sub visibilitySamples
{
	my ($self, $samples) = @_;
	$self->{visibilitySamples} = $samples if @_ > 1;
	return $self->{visibilitySamples};
}

sub maxVisibilitySamples
{
	my ($self, $samples) = @_;
	$self->{maxVisibilitySamples} = $samples if @_ > 1;
	return $self->{maxVisibilitySamples};
}

sub volumeSamples
{
	my ($self, $samples) = @_;
	$self->{volumeSamples} = $samples if @_ > 1;
	return $self->{volumeSamples};
}

sub particleSamples
{
	my ($self, $samples) = @_;
	$self->{particleSamples} = $samples if @_ > 1;
	return $self->{particleSamples};
}

sub redThreshold
{
	my ($self, $threshold) = @_;
	$self->{redThreshold} = $threshold if @_ > 1;
	return $self->{redThreshold};
}

sub greenThreshold
{
	my ($self, $threshold) = @_;
	$self->{greenThreshold} = $threshold if @_ > 1;
	return $self->{greenThreshold};
}

sub blueThreshold
{
	my ($self, $threshold) = @_;
	$self->{blueThreshold} = $threshold if @_ > 1;
	return $self->{blueThreshold};
}

sub coverageThreshold
{
	my ($self, $threshold) = @_;
	$self->{coverageThreshold} = $threshold if @_ > 1;
	return $self->{coverageThreshold};
}

sub outputFormat
{
	my ($self, $format) = @_;
	$self->{outputFormat} = $format if @_ > 1;
	return $self->{outputFormat};
}

sub shadowPass
{
	my ($self, $pass) = @_;
	$self->{shadowPass} = $pass if @_ > 1;
	return $self->{shadowPass};
}

sub abortOnMissingTexture
{
	my ($self, $abort) = @_;
	$self->{abortOnMissingTexture} = $abort if @_ > 1;
	return $self->{abortOnMissingTexture};
}

sub dontReplaceRendering
{
	my ($self, $dont) = @_;
	$self->{dontReplaceRendering} = $dont if @_ > 1;
	return $self->{dontReplaceRendering};
}

sub verbose
{
	my ($self, $verbose) = @_;
	$self->{verbose} = $verbose if @_ > 1;
	return $self->{verbose};
}

sub iprFile
{
	my ($self, $ipr) = @_;
	$self->{iprFile} = $ipr if @_ > 1;
	return $self->{iprFile};
}

sub xResolution
{
	my ($self, $resolution) = @_;
	$self->{xResolution} = $resolution if @_ > 1;
	return $self->{xResolution};
}

sub yResolution
{
	my ($self, $resolution) = @_;
	$self->{yResolution} = $resolution if @_ > 1;
	return $self->{yResolution};
}

sub xLeft
{
	my ($self, $xl) = @_;
	$self->{xLeft} = $xl if @_ > 1;
	return $self->{xLeft};
}

sub xRight
{
	my ($self, $xr) = @_;
	$self->{xRight} = $xr if @_ > 1;
	return $self->{xRight};
}

sub yLow
{
	my ($self, $yl) = @_;
	$self->{yLow} = $yl if @_ > 1;
	return $self->{yLow};
}

sub yHigh
{
	my ($self, $yh) = @_;
	$self->{yHigh} = $yh if @_ > 1;
	return $self->{yHigh};
}

sub displayLayer
{
	my ($self, $display) = @_;
	$self->{displayLayer} = $display if @_ > 1;
	return $self->{displayLayer};
}

sub numberOfProcessors
{
	my ($self, $procs) = @_;
	$self->{numberOfProcessors} = $procs if @_ > 1;
	return $self->{numberOfProcessors};
}

sub tileWidth
{
	my ($self, $width) = @_;
	$self->{tileWidth} = $width if @_ > 1;
	return $self->{tileWidth};
}

sub tileHeight
{
	my ($self, $height) = @_;
	$self->{tileHeight} = $height if @_ > 1;
	return $self->{tileHeight};
}

sub continue
{
	my ($self, $continue) = @_;
	$self->{continue} = $continue if @_ > 1;
	return $self->{continue};
}

sub keepPreImage
{
	my ($self, $keep) = @_;
	$self->{keepPreImage} = $keep if @_ > 1;
	return $self->{keepPreImage};
}

sub localdm
{
	my ($self, $ldm) = @_;
	$self->{localdm} = $ldm if @_ > 1;
	return $self->{localdm};
}

sub maxPasses
{
	my ($self, $passes) = @_;
	$self->{maxPasses} = $passes if @_ > 1;
	return $self->{maxPasses};
}

sub badFrameSize
{
	my ($self, $size) = @_;
	$self->{badFrameSize} = $size if @_ > 1;
	return $self->{badFrameSize};
}

sub scenefile
{
	my ($self, $scene) = @_;
	$self->{scenefile} = $scene if @_ > 1;
	return $self->_convertToMayaNative($self->{scenefile});
}

sub renderLayerSubdirs
{
	my ($self, $subdirs) = @_;
	$self->{renderLayerSubdirs} = $subdirs if @_ > 1;
	return $self->{renderLayerSubdirs};
}

sub renderAllLayers
{
	my ($self, $all) = @_;
	$self->{renderAllLayers} = $all if @_ > 1;
	return $self->{renderAllLayers};
}

sub renderRenderableLayers
{
	my ($self, $renderable) = @_;
	$self->{renderRenderableLayers} = $renderable if @_ > 1;
	return $self->{renderRenderableLayers};
}

sub renderLayer
{
	my ($self, $layer) = @_;
	$self->{renderLayer} = $layer if @_ > 1;
	return $self->{renderLayer};
}

sub batchmode
{
	my ($self, $mode) = @_;
	$self->{batchmode} = $mode if @_ > 1;
	return $self->{batchmode};
}

sub currentRenderer
{
	my ($self, $mode) = @_;
	$self->{currentRenderer} = $mode if @_ > 1;
	return $self->{currentRenderer};
}

sub frameTimeout
{
	my ($self, $timeout) = @_;
	$self->{frameTimeout} = $timeout if @_ > 1;
	return $self->{frameTimeout};
}

sub outputPaths
{
	my $self = shift;
	$self->{outputPaths} = shift if @_;
	return $self->{outputPaths};
}

###########################################################################
#   Private Routines
###########################################################################

sub _convertToMayaNative
{
	my ($self, $path) = @_;
	$path =~ s/\\/\//g;
#  	$path =~ s|/+$||g if(length($path) > 1);
	return $path;
}

1;
