#
#########################################################################################
#
#	PipelineFX L.L.C.
#
#	Author: Anthony Higa
#
#	This file is an example module on how to write a 'priority scheme' replacement
#	module.	
#
#	This is specifically designed to allow Qube! administrators to create their own
#	priority scheme which best fits their studio.
#
#	To use this module: Modify the supervisor's /etc/qb.conf
#
#	Add or change supervisor_queue_binding to:
#		supervisor_queue_binding = Perl
#		supervisor_queue_library = /path/to/this/module/algorithm.pm
#
#########################################################################################

#
# qb_init
#
#  This function is used to initialize stuff like databases, etc... in preparation
#  for qb_jobcmp and qb_hostcmp.  
#
sub qb_init
{
print <<INIT;
#########################################################################################

	Copyright: PipelineFX L.L.C. 
		All Rights Reserved.
	
	Software: Qube!

	Purpose: supervisor queuing algoritm replacement perl module.

		This is an example module to be used for reference in 
	building a custom queuing algoritm.

	Qube! license holders may modify this module for their own private use.

#########################################################################################
INIT
}

#
# qb_jobcmp
#
#  This is the definition of the jobcmp function.  It is a simple function designed
#	to compare 2 jobs together relative to a single host.
#
#	return 1 if a > b 
#	return -1 if b > a
#	return 0 if a == b
#
#
#	These are the available fields for the job hash:
#
#		id, pid, pgrp, priority, user, status, name, label, cluster, cpus, prototype, 
#		requirements, reservations, restrictions, account
#
#	These are the available fields for the host hash:
#
#		name, state, cluster, resources, restrictions, address
#


#
#  This example implements PipelineFX's Patent Pending Algorithm.
#

'''
    First prioritize by cluster.
    Then by priority.
    Then by cpus. Least goes first.
'''
sub qb_jobcmp
{
	my $joba = shift;
	my $jobb = shift;
	my $host = shift;
	
        # we first check to see if they are the same... if they are we short circuit now.
	return $jobb->{priority} <=> $joba->{priority} if ($joba->{"cluster"} eq $jobb->{"cluster"});

	# now we check for exact matches... this is cause it's faster to check now than later.
	return 1 if ($joba->{"cluster"} eq $host->{"cluster"});
	return -1 if ($jobb->{"cluster"} eq $host->{"cluster"});

	# at this point, we don't have a chioce... we'll have to compare the clusters
	my @clustera = split(/\//, $joba->{"cluster"});
	my @clusterb = split(/\//, $jobb->{"cluster"});
	my @clusterh = split(/\//, $host->{"cluster"});

	my $weighta = 0;
	my $weightb = 0;

	my $mismatcha = 0;
	my $mismatchb = 0;

	# who ever scores the highest weight is the winner.
	for (my $i = 0; $i < @clusterh; $i++) {
		if ($clusterh[$i] eq $clustera[$i] and not $mismatcha) {
			$weighta++;
		} else {
			$mismatcha = 1;
		}

		if ($clusterh[$i] eq $clusterb[$i] and not $mismatchb) {
			$weightb++;
		} else {
			$mismatchb = 1;
		}
	}

	my $result = $weighta <=> $weightb;
	return $result if ($result);


	# fall back comparison - note: we'll leave the jobid or jobsubmit date comparison to the supervisor
	# we're only concerned about priority and cluster
	return $jobb->{priority} <=> $joba->{priority};
}

sub qb_hostcmp
{
	my $hosta = shift;
	my $hostb = shift;
	my $job = shift;
	
        # we first check to see if they are the same... if they are we short circuit now.
	return 0 if ($hosta->{"cluster"} eq $hostb->{"cluster"});

	# now we check for exact matches... this is cause it's faster to check now than later.
	return 1 if ($hosta->{"cluster"} eq $job->{"cluster"});
	return -1 if ($hostb->{"cluster"} eq $job->{"cluster"});

	# at this point, we don't have a chioce... we'll have to compare the clusters
	my @clustera = split(/\//, $hosta->{"cluster"});
	my @clusterb = split(/\//, $hostb->{"cluster"});
	my @clusterj = split(/\//, $job->{"cluster"});

	my $weighta = 0;
	my $weightb = 0;

	my $mismatcha = 0;
	my $mismatchb = 0;

	# who ever scores the highest weight is the winner.
	for (my $i = 0; $i < @clusterj; $i++) {
		if ($clusterj[$i] eq $clustera[$i] and not $mismatcha) {
			$weighta++;
		} else {
			$mismatcha = 1;
		}

		if ($clusterj[$i] eq $clusterb[$i] and not $mismatchb) {
			$weightb++;
		} else {
			$mismatchb = 1;
		}
	}

	return $weighta <=> $weightb;
}

sub qb_jobreject
{
	my $job = shift;
	my $host = shift;

	# note: we're supposed to implement the Restrictions portion of the algorithm here, but due to the fact
	# that the native Qube! implementation takes advantage of internal parser components, we'll just skip
	# this portion.

	#
	#  return 0 if nothing is wrong.
	#
	return 0;
}





