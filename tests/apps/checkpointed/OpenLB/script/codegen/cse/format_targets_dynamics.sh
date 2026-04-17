#!/usr/bin/env bash

# file where dynamics information is dumped via SuperLattice::describe()
TARGET_IN=$1

# list containing C++ dynamics type information for performing cse
TARGET_OUT=$2

# define type of target
TYPE=dynamics

# Only look at optimizable dynamics with manageable complexity
awk -F\; '$3 == 1 && $6 > 0 && $6 < 100e6 { print $1 }' $TARGET_IN > tmp.$TYPE

# Reformat full dynamics name, set Expr type, remove all but tags from descriptor
awk 'NF > 0 {
    line=$0
    gsub(/double/, "Expr", line)
    gsub(/float/, "Expr", line)

    out_line = ""
    remain = line
    while (match(remain, /descriptors::D[23]Q[0-9]+<[^>]+>/)) {
        out_line = out_line substr(remain, 1, RSTART - 1)
        hit = substr(remain, RSTART, RLENGTH)
        open_pos = index(hit, "<")
        desc_head = substr(hit, 1, open_pos)
        content = substr(hit, open_pos + 1, length(hit) - open_pos - 1)
        n = split(content, args, ",")
        new_content = ""
        sep = ""
        for (i = 1; i <= n; i++) {
            if (args[i] ~ /tag::/) {
                gsub(/^ +| +$/, "", args[i])
                new_content = new_content sep args[i]
                sep = ","
            }
        }
        out_line = out_line desc_head new_content ">"
        remain = substr(remain, RSTART + RLENGTH)
    }
    out_line = out_line remain
    print out_line
}' tmp.$TYPE | sort | uniq > "$TARGET_OUT"

rm tmp.$TYPE
