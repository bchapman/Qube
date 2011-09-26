'''
After Effects renderTalk Scripts
Library of scripts that renderTalk uses
'''

def getOpenProjectScript(projectFile):
    script = '''app.openFast(File("%s"));"Project Loaded"''' % str(projectFile)
    return prepScript(script)

def getRenderAllScript():
    script = '''app.project.renderQueue.render();"Project Rendered"'''
    return prepScript(script)

def getSetupSegmentScript(startFrame, endFrame, rqIndex):
    script = '''\
// Setup the render queue
var startFrame = %s;
var endFrame = %s;
var rqIndex = %s;

// Turn off all other rq items
for (var r=1; r<=app.project.renderQueue.numItems; r++) {
    try {
        app.project.renderQueue.item(r).render = false;
    } catch (error) {
        continue;
    }
}

rqItem = app.project.renderQueue.item(rqIndex);
// If the rq index has already been rendered once, create a duplicate to render from.
if (rqItem.status == RQItemStatus.USER_STOPPED || rqItem.status == RQItemStatus.ERR_STOPPED || rqItem.status == RQItemStatus.DONE) {
    var origRQItem = rqItem;
    rqItem = origRQItem.duplicate();
    
    // Make sure the output files are still the same
    for (var o=1; o<=origRQItem.outputModules.length; o++) {
        rqItem.outputModule(o).file = origRQItem.outputModule(o).file;
    }
}
rqItem.render = true;
rqItem.logType = LogType.ERRORS_AND_PER_FRAME_INFO;

// Set up the start and end frames
var start_time = rqItem.timeSpanStart;
var end_time   = rqItem.timeSpanStart + rqItem.timeSpanDuration;
if (startFrame) {
    start_time = -rqItem.comp.displayStartTime + ((parseInt(startFrame,10) - app.project.displayStartFrame) * rqItem.comp.frameDuration);
};
if (endFrame) {
    var end_frame_plus_one = parseInt(endFrame,10) + 1.0 - app.project.displayStartFrame;
    end_time = -rqItem.comp.displayStartTime + (end_frame_plus_one * rqItem.comp.frameDuration);
}; 
rqItem.timeSpanStart = start_time;
rqItem.timeSpanDuration = end_time - start_time;
outputs = [];
for (var o=1; o<=rqItem.outputModules.length; o++) {
    outputs.push(rqItem.outputModule(o).file.fsName);
};
outputs.toString();
''' % (startFrame, endFrame, rqIndex)

    return prepScript(script)

def prepScript(script):
    result = []
    lines = script.split("\n")
    for line in lines:
        if not line.strip().startswith("//"):
            result.append(line)
    
    result = "".join(result)
    return result