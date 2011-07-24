#!/usr/bin/perl
##################################################################
#  The above lines is dependant upon the location of perl.
##################################################################
#
#  perl bootstrap script for the custom job type
#
##################################################################
# include qube! perl api
BEGIN {
	$ENV{QB_DIR} = $ENV{QBDIR} = "/app/pfx/qube" if (not defined $ENV{QBDIR});
}
use lib ".";
use lib "..";
use lib "$ENV{QB_DIR}/api/perl";
use lib "$ENV{QBDIR}/api/perl";
use qb;

# obtain input job
my $jobarchive = shift(@ARGV) || "job.qja";
my $backend = shift(@ARGV) || "execute.pm";

# setup development env
qb::_qb_setjob($jobarchive);

# launch execution script
print "INFO: bootstrap script loading execute module\n";
require $backend;
1;

