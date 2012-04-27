##############################################################################
#
#      Copyright: Pipelinefx @ 2006
#
##############################################################################
#
# execute.pm -- Maya jobtype backend module
#
#  This is what the Qube! worker executes via the proxy process for a
#  "maya" jobtype.
#
##############################################################################

local $| = 1;

use strict;

use File::Path;
use File::Copy;
use qb;
use Data::Dumper;
use maya::Package;
use maya::MayaJob;
use maya::PromptMayaJob;
use maya::SoftwareMayaJob;
use maya::VectorMayaJob;
use maya::TurtleMayaJob;
use maya::MentalRayMayaJob;
use maya::GenericMayaJob;
use maya::GelatoMayaJob;
use maya::CmdMayaJob;
use maya::UniversalMayaRenderJob;
use maya::Utils qw(sceneMayaVersion);

$main::WAITINGTIMEOUT = 30;

main();

###########################################################################
#
# MAIN
#
###########################################################################

sub main
{
	# fetch the job from Qube!
	my $job = qb::jobobj("maya::MayaJob");

	local $Data::Dumper::Indent = 1;
	print STDERR "\n" . Dumper($job) . "\n";

	print("====PACKAGE====\n");
	for(sort keys %{$job->package()}) {
		print "$_=" . $job->package()->{$_} . "\n";
	}
	print("===============\n\n");

# 	print STDERR "RENDERER: ", $job->package()->currentRenderer(), "\n";

	#### OOGA

	# satellite slave nodes don't need to do anything... just twiddle its
	#  thumbs while waiting for the master to complete
	my $satellite = $job->package()->{"mentalray_satellite"};
	$satellite = $satellite eq "None" ? "" : $satellite;
	if($satellite &&  ($ENV{QBSUBID} != 0)) {
		print "INFO: I am a satellite slave node\n";

		# just wait until the master node is done
		my $master_status = wait_for_master();

		print "INFO: master node is done [$master_status]. slave bailing...\n";

		# we just exit here
		if ($master_status =~ /^(complete|pending|blocked)$/) {
			qb::reportjob($master_status);
			exit 0;
		} else {
			qb::reportjob($master_status);
			exit 1;
		}
		# OOGA TODO: handle various statuses-- what to do when preempt, etc?
	}

	# satellite slave nodes will not run any code after this line.

	# check the version of the scenefile, to see what version of Maya
	#  we should run.
	#
	my $ver = sceneMayaVersion($job->package->scenefile());
	my @rayhostsFiles = ();

	$ENV{MAYA_UI_LANGUAGE} = "en_US";

	if ($job->package()->batchmode()) {

		# "batch mode"-- i.e., invoke command-line "render" command

		bless $job, "maya::CmdMayaJob";

	} elsif($ver >= 7.0 or $ver eq "") {

		# are we doing mray satellite?
		if($satellite) {
			print "INFO: I am the satellite master node\n";
			@rayhostsFiles = createRayhostsFile($job, $ver);
		}

		# Maya 7.0 and above use a new, cleaner back-end mechanism

		bless $job, "maya::UniversalMayaRenderJob";

	} else {

		# semi-legacy code for Maya versions 6.5 and below

		# bless the $job into the right class
		if ($job->package()->batchmode()) {
			bless $job, "maya::CmdMayaJob";
		} elsif ($job->package()->currentRenderer() eq "mayaSoftware" or
				 $job->package()->currentRenderer() eq "sw") {
			bless $job, "maya::SoftwareMayaJob";
			# 	} elsif ($job->package()->currentRenderer() eq "mayaHardware" or
			# 			 $job->package()->currentRenderer() eq "hw") {
			# 		bless $job, "maya::HardwareMayaJob";
		} elsif ($job->package()->currentRenderer() eq "mayaVector" or
				 $job->package()->currentRenderer() eq "vr") {
			bless $job, "maya::VectorMayaJob";
		} elsif ($job->package()->currentRenderer() eq "mentalRay" or
				 $job->package()->currentRenderer() eq "mr") {
			bless $job, "maya::MentalRayMayaJob";
		} elsif ($job->package()->currentRenderer() eq "turtle") {
			bless $job, "maya::TurtleMayaJob";
			# 	} elsif ($job->package()->currentRenderer() eq "gelato") {
			# 		bless $job, "maya::GelatoMayaJob";
		} else {
			# 		bless $job, "maya::PromptMayaJob";
			bless $job, "maya::GenericMayaJob";
		}
	}

	my $status = "";
	eval {
		$status = $job->run();
	};
	if($@) {
		# some exception occured in run()
		warn "ERROR: exception caught in $job->run()\n";
		warn "$@\n";
		$status = "failed";
	}

	# cleanup/restore mray satellite rayhosts files?
	if (@rayhostsFiles) {
		print "INFO: cleaning up rayhosts file\n";
		cleanupRayhostsFile(@rayhostsFiles);
	}

	# TODO: qb::reportjob() seems to immediately kill us, or kill the
	#   .err and .out pipes-- need to find out exactly what's happening
	if(!$status) {
		# for some reason $status is blank... so assume failure
		$status = "failed";
	}
	warn("INFO: reporting status [$status] to supe: qb::reportjob('$status')\n");
	qb::reportjob($status);

	if($status eq "complete" or
	   $status eq "pending") {
		exit 0;
	} else {
		exit 1;
	}
}


#
# createRayhostsFile
#
sub createRayhostsFile
{
	my $job = shift;
	my $mayaver = shift || "";

	# get the hostnames of the slave nodes (subjobs 1 and up)
	my $filter = {"id" => $ENV{QBJOBID}};
	my $fields = ["subjobs"];
	my @jobs = qb::jobinfo($fields, $filter);
	# 		local $Data::Dumper::Indent = 1;
	# 		local $Data::Dumper::Varname = "JOB";
	# 		print "\n" . Dumper(@jobs) . "\n";

	my @slaves = ();
	for (@{$jobs[0]->{"subjobs"}}) {
		push @slaves, $_->{"host"};
	}
	shift @slaves;
	print "INFO: slaves=[@slaves]\n";

	# write the hostnames into the maya.rayhosts file for now, we
	#  always write 2 files-- one in the 32-bit prefs directory, and
	#  another in the 64-bit (<ver>-x64) directory

	my @files = ();
	my $mayadir;
	if ($^O eq "MSWin32") {
		$mayadir = "$ENV{USERPROFILE}/My Documents/maya";
	} elsif ($^O eq "linux") {
		$mayadir = "$ENV{HOME}/maya";
	} elsif ($^O eq "darwin") {
		if($mayaver >= 8.5) {
			$mayadir = "$ENV{HOME}/Library/Preferences/Autodesk/maya";
		} else {
			$mayadir = "$ENV{HOME}/Library/Preferences/Alias/maya";
		}
	}

	for($mayaver, "$mayaver-x64") {
		my $prefsdir .= "$mayadir/$_/prefs";

		if(not -d $prefsdir) {
			mkpath($prefsdir) || die "ERROR: cannot mkpath($prefsdir)";
		}
		my $rayhosts_file = "$prefsdir/maya.rayhosts";

		my $satellite_port =
			qb::jobconfig($job->{prototype}, "mray_satellite_port_$mayaver");

		# use defaults if mray_satellite_port_<ver> is undefined in job.conf
		if (not $satellite_port) {
			if ($mayaver eq "2010") {
				$satellite_port = 7310;
			} elsif ($mayaver eq "2009") {
				$satellite_port = 7109;
			} elsif ($mayaver eq "2008") {
				$satellite_port = 7107;
			} elsif ($mayaver eq "8.5") {
				$satellite_port = 7106;
			} elsif ($mayaver eq "8.0") {
				$satellite_port = 7105;
			} elsif ($mayaver eq "7.0") {
				$satellite_port = 7103;
			} else {
				warn "WARNING: unknown maya version [$mayaver]\n";
				warn "  cannot determine mental ray satellite port number\n";
			}
		}

		# back up the original rayhosts file
		my $backup = "$rayhosts_file-$ENV{QBJOBID}.bak";
		if(-r $rayhosts_file) {
			print "INFO: backing up original rayhosts file [$rayhosts_file] " .
				"to [$backup]\n";
			move($rayhosts_file, $backup) or warn "ERROR: cannot move " .
				"rayhosts file [$rayhosts_file] to [$backup]\n";
		}

		# write to the rayhosts file
		print "INFO: writing satellite slave host list to rayhosts file " .
			"[$rayhosts_file]\n";
		open(RAYHOSTS, ">$rayhosts_file") or
			die "ERROR: cannot write to maya.rayhosts file [$rayhosts_file]";
		for (@slaves) {
			print RAYHOSTS "$_:$satellite_port\n";
		}
		close RAYHOSTS;
		push @files, $rayhosts_file;
	}

	return @files;
}

#
# cleanupRayhostsFile(@files)
#
sub cleanupRayhostsFile
{
	my @files = @_;

	for(@files) {
		# remove rayhosts file that we created, AND restore the original one
		#  if applicable
		print "INFO: removing rayhosts file [$_]\n";
		unlink or warn "ERROR: cannot unlink rayhosts file [$_]\n";
		my $backup = $_ . "-$ENV{QBJOBID}.bak";
		if(-r $backup) {
			print "INFO: restoring rayhosts file [$_] from backup [$backup]\n";
			move($backup, $_) or warn "ERROR: cannot restore backup rayhosts ".
				"file [$backup] to [$_]: $!\n";
		}
	}
}


#
#
#
sub wait_for_master
{
	my $elapsed = 0;
	my $polling_interval =
		qb::jobconfig("maya", "mray_satellite_slave_polling_interval") || 30;
	my $status = "";
	while(1) {
		sleep $polling_interval;
		$elapsed += $polling_interval;
		my $filter = {"id" => $ENV{QBJOBID}};
		my $fields = ["subjobs"];
		my @jobs = qb::jobinfo($fields, $filter);
		my $prevstatus = $status;
		$status = @{$jobs[0]->{"subjobs"}}[0]->{"status"};
		if($status ne $prevstatus) {
			print "INFO: master status: $status\n";
		}
		if($status !~ /^(running|waiting)$/) {
			print "INFO: master has exited... [$elapsed] seconds elapsed\n";
			return $status;
		}
	}
}

1;

