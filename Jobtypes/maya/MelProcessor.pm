##############################################################################
#
#      Copyright: PipeLinefx @ 2006
#
##############################################################################
#
# MelProcessor.pm -- command processor for mel commands.
#
#  This class implements a Mel "command processor", by launching Maya
#  in the background and feeding it mel commands to execute.
#
##############################################################################
local $| = 1;

package maya::MelProcessor;

use IPC::Run;
use File::Basename;
use maya::Utils qw(findMayaExecutable);

# various timeouts, in seconds.
$maya::MelProcessor::MAYA_LAUNCH_TIMEOUT = 300;
$maya::MelProcessor::MAYA_QUIT_TIMEOUT = 60;
$maya::MelProcessor::MAYA_DEFAULT_CMD_NUDGE_INTERVAL = 600;

#########################################################################
# Constructors, Destructors, and Initialization/Finalization Routines
#########################################################################
#
# new()
#
#  Constructor.
#
sub new
{
	my $class = shift;

	my $self = {};
	bless($self, $class);

	$self->_init(@_);

	return $self;
}

#
# _init()
#
#  Initialize instance.  For internal use only.
#
sub _init
{
	my $self = shift;
	my $executable = shift || "";

	$self->mayaVersion("");
	$self->mayaExecutable("");
	$self->started(0);
	$self->result("");
	$self->stdout("");
	$self->stderr("");
}

#
# DESTROY()
#
#  Destructor.
#
#  Note: At least on the MacOS X platform, it seems that the MayaBatch
#  command remains undead when a MelProcessor object is automatically
#  DESTROYed (i.e., when the object drops out of scope)-- so, the
#  finish() method must be called explicitly by the creator.
#
sub DESTROY
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	# make sure we clean up, including the termination of maya
	$self->finish();
}

#
# finish()
#
#  Properly finishes our maya process, and closes the harness handles.
#  Returns TRUE if all child processes exited successfully, FALSE otherwise.
#
sub finish
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	my $retval = 1;

	if($self->started()) {
		warn "INFO: HARNESS=[" . $self->_mayaharness() . "]\n";
		if($self->_mayaharness()) {
			if($self->_mayaharness->pumpable()) {
				warn "INFO: exiting from maya\n";
				# gracefully exit from maya, but timeout after a while...
				$self->exec('quit -f', undef, undef,
							$maya::MelProcessor::MAYA_QUIT_TIMEOUT, 0);
			} else {
				# not pumpable()? maya must've crashed earlier.
				warn("ERROR: did maya crash earlier?");
			}
			# properly finish the subprocesses and close the pipes
			$retval = $self->_mayaharness->finish();
		} else {
			# started() but no _mayaharness?  Maya must've not started
			# up properly.  We should never really get here, but
			# timing issues can actually leave us here...  it's not a
			# huge problem, so we just fall thru and let go of it...

#  			warn("ERROR: started() but no pipe to maya???");
#  			warn("ERROR: perhaps maya didn't startup properly...");
#  			warn("ERROR: should never get here!!!");
		}
		$self->started(0);
	}
	return $retval;
}

#
# abort()
#
sub abort
{
	print STDERR (caller 0)[3]."\n";
	my $self = shift;

	if($self->_mayaharness()) {
		$self->_mayaharness()->kill_kill();
	}

	die("aborting");
}

###########################################################################
# Public Accessor Methods
###########################################################################

#
# mayaVersion()
#
#  Stores prefered maya version.
#
sub mayaVersion
{
	my $self = shift;
	$self->{"mayaVersion"} = shift if @_;
	return $self->{"mayaVersion"};
}

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

#
# started()
#
#  Indicates whether we've started Maya or not.
#
sub started
{
	my $self = shift;
	$self->{"started"} = shift if @_;
	return $self->{"started"};
}

#
# echo()
#
#  echo == 1 means we should echo the mel commands we're executing to
#  stderr.
#
sub echo
{
	my $self = shift;
	$self->{"echo"} = shift if @_;
	return $self->{"echo"};
}

#
# result()
#
#  Stores the result string from the last mel command run via the
#  exec() method.
#
#  When a mel command is executed, it prints the result (return value)
#  to STDERR, as in "Result: blah blah".  If there was an error,
#  "Error: blah blah" is printed instead.  Finally, if the command was
#  successful but it has no return value, such as when doing a
#  "setAttr", it will not print anything.  This method will return the
#  "blah blah" part (i.e., without the "Result: " or "Error: " part),
#  or the empty string if the previous mel command completed with no
#  output.
#
sub result
{
	my $self = shift;
	$self->{"result"} = shift if @_;
	return $self->{"result"};
}

#
# stdout()
#
#  Stores the stdout output from the last mel command execution via
#  the exec() method.
#
sub stdout
{
	my $self = shift;
	$self->{"stdout"} = shift if @_;
	return $self->{"stdout"};
}

#
# stderr()
#
#  Stores the stderr output from the last mel command execution via
#  the exec() method.
#
sub stderr
{
	my $self = shift;
	$self->{"stderr"} = shift if @_;
	return $self->{"stderr"};
}

###########################################################################
# Private/Internal Accessor Methods
###########################################################################

#
# _mayaharness()
#
#  Stores the IPC::Run::harness object that controls our maya instance.
#
sub _mayaharness
{
	my $self = shift;
	$self->{_mayaharness} = shift if @_;
	return $self->{_mayaharness};
}

#
# _mayastdin()
#
#  Stores the reference to a scalar, which is the stdin handle of our
#  maya instance.  We feed maya with mel commands by appending strings
#  to this handle, as in:
#
#    ${$self->_mayastdin()} .= "ls -cameras";
#
sub _mayastdin
{
	my $self = shift;
	$self->{_mayastdin} = shift if @_;
	return $self->{_mayastdin};
}

#
# _mayastdout()
#
#  Stores the reference to a scalar, which is the stdout handle of our
#  maya instance.  We get stdout output from maya by reading from this
#  handle, as in:
#
#    $outbuf .= ${$self->_mayastdout()};
#
#  Note that this handle should be manually cleared after reading, as
#  in:
#
#    ${$self->_mayastdout()} = "";
#
sub _mayastdout
{
	my $self = shift;
	$self->{_mayastdout} = shift if @_;
	return $self->{_mayastdout};
}

#
# _mayastderr()
#
#  Stores the reference to a scalar, which is the stderr handle of our
#  maya instance.  We get stderr output from maya by reading from this
#  handle, as in:
#
#    $errbuf .= ${$self->_mayastderr()};
#
#  Note that this handle should be manually cleared after reading, as
#  in:
#
#    ${$self->_mayastderr()} = "";
#
sub _mayastderr
{
	my $self = shift;
	$self->{_mayastderr} = shift if @_;
	return $self->{_mayastderr};
}

#
# _mayatimer()
#
#  Stores the timer that times out when the "mel: " prompt doesn't
#  come back for a pre-determined time period.  It is used in the
#  'while($h->pump())' loop in the exec() method.
#
sub _mayatimer
{
	my $self = shift;
	$self->{_mayatimer} = shift if @_;
	return $self->{_mayatimer};
}

###########################################################################
# Public Methods
###########################################################################

#
# start()
#
#  Start up Maya in prompt mode, and open its stdin, stdout, and
#  stderr for pumping input and output.  The user doesn't necessarily
#  have to call this method, as it will be automatically called on the
#  first call to the exec() method.
#
sub start
{
	my $self = shift;

	if($self->started()) {
		warn("WARNING: Maya has already been started");
		return;
	}

	my $in;
	my $out;
	my $err;
	my $h;
	my $exec = $self->mayaExecutable() ||
		findMayaExecutable($self->mayaVersion());

	# make sure we have MAYA_LOCATION set properly
	if($exec =~ m[/usr/(local/)?s?bin/maya]) {
		delete $ENV{"MAYA_LOCATION"};
		warn("INFO: unsetting MAYA_LOCATION\n");
	} else {
		$ENV{"MAYA_LOCATION"} = dirname(dirname($exec));
		warn("INFO: setting MAYA_LOCATION to $ENV{MAYA_LOCATION}\n");
	}

	my @cmd = ($exec, "-batch", "-prompt");
	print STDERR "launching: @cmd\n";

	# "start" the maya program.  We redirect both stdout and stderr to
	# the $writer handle
	#
	# NOTE: "IPC::Run::start" launches the command as a background
	# process, and does NOT return error.  It will, however, raise an
	# exception upon error or when it times out, so we'll need to
	# catch it.

 	my $t = IPC::Run::timer($maya::MelProcessor::MAYA_LAUNCH_TIMEOUT);
	eval {
		$h = IPC::Run::start(\@cmd, \$in, \$out, \$err, $t);
	};
	if($@) {
		warn("exception caught!");
		my $x = $@;			# save $@ in case another exception occurs
		$h->kill_kill if $h;
		die $x;
	}

	$self->started(1);
	$self->_mayaharness($h);
	$self->_mayastdin(\$in);
	$self->_mayastdout(\$out);
	$self->_mayastderr(\$err);

	$self->_mayatimer($t);		# save it for later use

	# wait for the first "mel:" prompt
	$self->exec(undef, undef, undef, $maya::MelProcessor::MAYA_LAUNCH_TIMEOUT, 0);

	# we'll reuse the timer later, so set it up here
# 	$t->reset();
# 	$t->exception(undef);	  # morph it into a "timer", which doesn't
# 							  # throw an exception
# 	$self->_mayatimer($t);		# save it for later use

	return $h;
}

#
# exec($self, $cmd, [$errorRegex], [$successRegex],
#      [$nudgeInterval], [$maxNudges])
#
#  Execute a single line of mel command, $cmd, by feeding it into the
#  STDIN of the maya process, then waiting for the prompt to come
#  back.

#  The input $cmd can have more than one mel command, separated by
#  semi-colons ';', which are processed in order.  If any of the
#  commands fail, the processing stops.  Note, however, that you
#  cannot have multiple lines in the input (i.e., no newline "\n"
#  characters in the input)-- it will be attempted to execute, but the
#  exact behavior is undefined for multiple-line input.
#
#  The status of command execution is returned-- i.e. TRUE if the
#  command succeeded, FALSE if there was an error.  If invoked with
#  multi-command, return TRUE iff all commands ran successfully, FALSE
#  otherwise.
#
#  Use the result() method to access the result from the last mel
#  command execution via exec().  Depending on if the mel command
#  succeeded or not, maya will output, to stderr, either "Result: blah
#  blah" or "Error: blah blah", (usually as the last line of output,
#  but not necessarily).  A call to result() will return the "blah
#  blah", with the "Result: " or "Error: " and the trailing newline
#  stripped off.  For multi-command invocation, the result from the
#  last command is saved in result(), if all commands ran
#  successfully.  If there was an error in running one of the
#  multi-commands, the "Error:" from that command is stored in
#  result().
#
#  Note that the regular expressions that are used to determine the
#  error conditions can be overidden from the default '^Error: (.*)'
#  and '^Result: (.*)' if the caller provides $errorRegex and
#  $successRegex.  See the maya::MentalRayMayaJob.pm::processWork()
#  method for an example.
#
#  If $errorRegex given is the empty string, i.e. "", all error
#  messages will be ignored.
#
#  The $nudgeInterval is used to poll the $cmd execution-- more
#  precisely, a "\n" is fed to the maya process when the "mel: "
#  prompt doesn't come back for $nudgeInterval.  This value, if not
#  given, defaults to MAYA_DEFAULT_CMD_NUDGE_INTERVAL seconds.  If the
#  $cmd is expected to take longer or shorter, an appropriate value
#  should be given.
#
#  The $maxNudges is used to tell when to give up on waiting for the
#  $cmd to return the "mel: " prompt.  If the "mel: " prompt is not
#  seen after $maxNudges, we terminate.  So, in effect, the $cmd will
#  timeout after $maxNudges * $nudgeInterval seconds.  Be duly aware
#  that the "timeout" in this case will call our abort() method, which
#  will kill all subprocesses and throw an exception via die().  If
#  $maxNudges is not given or set to undef, $cmd never times out.
#
sub exec
{
	my $self = shift;
	my $cmd = shift || "";

	# $errorRegex is matched against stdout/stderr to determine if an
	# error occured while processing a command.  If the regex include
	# a pair of parentheses, the match within the parentheses
	# (i.e. $1) will be saved in the results().

	my $errorRegex = shift;
	if(not defined $errorRegex) {
		$errorRegex = '^Error: (.*)';
	}
	my $successRegex = shift;
	if(not defined $successRegex) {
		$successRegex = '^Result: (.*)';
	}
	my $nudgeInterval = shift ||
		$maya::MelProcessor::MAYA_DEFAULT_CMD_NUDGE_INTERVAL;
 	my $maxNudges = shift;		# defaults to undef
	my $nudgeCount = 0;

# 	if(not defined $cmd) {
# 		warn("WARNING: no command was given");
# 		return;
# 	}

	$self->result("");			# clear the result

	if(not $self->started()) {
		$self->start();
	}

	my $h = $self->_mayaharness();
	my $in = $self->_mayastdin();
	my $out = $self->_mayastdout();
	my $err = $self->_mayastderr();
	my $t = $self->_mayatimer();

	# clear/flush any output that may be potentially "leftover" in the
	# pipe from a previous interaction
	${$out} = "";
	${$err} = "";

	$t->interval($nudgeInterval);
	$t->start();				# start the timer

	# feed the $cmd to Maya
	if($cmd) {
		if($errorRegex eq "") {
			warn("INFO: All error messages output from Maya will be ".
				 "ignored during execution of the next command: [$cmd]\n");
		}
		print STDERR "$cmd\n" if $self->echo();
 		${$in} .= "$cmd\n";
	}

	my $outbuf = "";
	my $errbuf = "";

	# we loop until we get the "mel: " prompt back
	while($h->pump()) {
		# make sure all input goes first.
		next if defined ${$in} and length ${$in};

		# get output from Maya
		my $outdelta = ${$out};
		my $errdelta = ${$err};
		$outbuf .= $outdelta;
		$errbuf .= $errdelta;
		${$out} = "";
		${$err} = "";

		print "$outdelta";
		print STDERR "$errdelta";

		if(checkForFatalMayaErrors($errbuf) or
		   checkForFatalMayaErrors($outbuf)) {
		  #### there was a fatal error-- raise an exception
		  die("ERROR: fatal error!!");
		}

		if($outbuf =~ /mel: /ms) {
			last;
		}

		if($t->is_expired()) {
			# we've hit a timeout on $t, and nothings being output to
			#  stdout or stderr
			warn("INFO: timer of [" . $t->interval() . " secs] expired-- ".
				 "\"nudging\" maya for 'mel:' prompt");
			$nudgeCount++;

			# we check for fatal maya errors here also (in addition to
			# after this while($h->pump) loop), just in case maya
			# didn't properly release/flush the stdout/err file
			# handles and "choked"
# 			if (checkForFatalMayaErrors($errbuf) or
# 				checkForFatalMayaErrors($outbuf)) {
# 				#### there was a fatal error-- raise an exception
# 				die("ERROR: fatal error!!");
# 			}

			if (defined $maxNudges and $nudgeCount > $maxNudges) {
				warn("ERROR: maximum nudge count [$maxNudges] reached on " .
					 "command [$cmd]\n"."timed out-- aborting!");
				# abort!
				$self->abort();
				return;
			}
			# timer expired, so we have perhaps missed the "mel: "
			# prompt, or it was never printed although the command
			# completed-- so let's give maya a nudge!
			${$in} .= "\n";

			$t->start();	# reset and restart the timer
# 			next;
		}
	} # while($h->pump())

	$t->reset();				# stop and rewind the timer

	# save the outputs
	$self->stdout($outbuf);
	$self->stderr($errbuf);

	my ($status, $result);
# 	if(checkForFatalMayaErrors($errbuf) or
# 	   checkForFatalMayaErrors($outbuf)) {
# 		#### there was a fatal error-- raise an exception
# 		die("ERROR: fatal error!!");
# 	}

	# check to make sure that maya is still running
	if(not $h->pumpable() and $cmd !~ /\bquit\b/) {
		#### handle error: raise an exception
		die("ERROR: lost pipe to maya-- has it crashed?");
	}

	# first, scan the stderr and stdout for any line containing $errorRegex.
	#  note that we ignore error messages containing the word "ignored".
	if($errorRegex ne "" and
	   (($errbuf =~ m/$errorRegex/m or $outbuf =~ m/$errorRegex/m) and
		$1 !~ m/\bignored\b/)) {
		$status = 0;
		$result = $1;
	} else {
		# $errorRegex didn't match, so we assume successful status
		$status = 1;

		# search for a line containing $successRegex, and if it's
		# found, set $result accordingly
# 		if($errbuf =~ m/$successRegex/m or $outbuf =~ m/$successRegex/m) {
# 			$result = $1;
# 		}

		# search for line(s) containg $successRegex, and if it's
		# found, set $result accordingly
		my @results = ();
		if ((@results = $errbuf =~ m/$successRegex/mg) or
			(@results = $outbuf =~ m/$successRegex/mg)) {
			$result = join ",", @results;
		}
	}
	$result ||= "";

	# the following is same as 'chomp $result;', but also works w/ DOS CRLF
	$result =~ s/\x0D?\x0A?$//;

	# Some commands, such as "setAttr" won't return any results, so
	# the $result and $status will both be empty.

	$self->result($result);		# remember the result

	return $status;
}

#
# checkForFatalMayaErrors($str)
#
#  Check for indications of fatal errors in the $str, which,
#  presumably, is the stderr output from Maya.
#
#  Return true (1) if error, false (0) otherwise.
#
sub checkForFatalMayaErrors
{
	my $str = shift;
	my $ret = 0;

	my @fatal_regexs
		= ('maya\s+encountered\s+a\s+fatal\s+error',
		   'Exit\s+1',
		   'could not get a license',
		   'Error: An error has occurred. Rendering aborted.',
		   'Fatal Error. Attempting to save in ',
		  );
	for(@fatal_regexs) {
		if($str =~ m/$_/) {
			$ret = 1;
			last;
		}
	}
	return $ret;
}

1;
