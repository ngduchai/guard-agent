#!/usr/bin/env nix-shell
#!nix-shell -p perl -i perl

use strict;
use warnings;

$ENV{LC_ALL} = "C";

sub check_file_paths {
    my @files = `git ls-files`;

    my $found_bad = 0;

    foreach my $file (@files) {
        chomp($file);

        # Ignore files in the "apps/*" directory
        next if $file =~ /^apps\//;

        if ($file =~ /\s/) {
            print STDERR "Error: File path contains whitespace: $file.\n";
            $found_bad = 1;
        }
    }

    if ($found_bad) {
        exit(1);
    }
}

# Do the work :-)

# Check file paths
check_file_paths();

# all OK
exit(0);
