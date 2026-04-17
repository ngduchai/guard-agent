#!/usr/bin/env nix-shell
#!nix-shell -p perl -i perl

use strict;
use warnings;

$ENV{LC_ALL} = "C";

sub check_whitespaces_and_tabs {
    my $src_endings = "c|cpp|cxx|h|hpp|hh";
    my @files = `git ls-files | grep -E "\\.($src_endings)\$"`;

    my $found_bad = 0;

    foreach my $file (@files) {
        chomp($file);
        my $content = `cat "$file"`;
        my @lines = split("\n", $content);

        for (my $i = 0; $i < scalar @lines; $i++) {
            my $line_number = $i + 1;
            my $line = $lines[$i];

            if ($line =~ /\t/) {
                print STDERR "Error: Indentation with Tab found in file $file at line $line_number.\n";
                $found_bad = 1;
            }

            if ($line =~ /[ \t]+$/) {
                print STDERR "Error: Trailing whitespace found in file $file at line $line_number.\n";
                $found_bad = 1;
            }
        }
    }

    if ($found_bad) {
        exit(1);
    }
}

# Do the work :-)

# Check whitespaces and tabs
check_whitespaces_and_tabs();

# all OK
exit(0);
