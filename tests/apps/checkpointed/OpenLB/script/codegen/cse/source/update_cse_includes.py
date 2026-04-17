# This file is part of the OpenLB library
#
# Copyright (C) 2026 Shota Ito, Adrian Kummerlaender
# E-mail contact: info@openlb.net
# The most recent release of OpenLB can be downloaded at
# <http://www.openlb.net/>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

import sys
import os
import re
import glob

def get_cse_files(directory):
    return glob.glob(os.path.join(directory, "*.cse.h"))

def parse_generated_cse(filepath):
    entries = {}
    if not os.path.exists(filepath):
        return entries

    with open(filepath, 'r') as f:
        lines = f.readlines()

    current_comment = None
    for line in lines:
        line = line.strip()
        if line.startswith("//") and not line.startswith("//#include"):
            current_comment = line[2:].strip()
        elif line.startswith("#include") and current_comment:
            match = re.search(r'"([a-f0-9]{64}\.cse\.h)"', line)
            if match:
                filename = match.group(1)
                entries[filename] = current_comment
            current_comment = None

    return entries

def extract_template_args(content, dynamic_type):
    if dynamic_type == 'dynamics':
        match = re.search(r'struct\s+CSE\s*<\s*(.*)\s*>\s*\{', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    elif dynamic_type == 'operator':
        match = re.search(r'struct\s+CSE_O\s*<\s*(.*)\s*>\s*\{', content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None

def reconstruct_comment(args_str, dynamic_type):
    # Common replacements to match convention
    s = args_str.replace("T, ", "Expr, ")
    s = s.replace("<T>", "<Expr>")
    s = s.replace("typename... FIELDS", "")

    # Clean up descriptors: descriptors::D2Q5<FIELDS...> -> descriptors::D2Q5<>
    s = re.sub(r'(descriptors::D\dQ\d{1,2})<FIELDS\.\.\.>', r'\1<>', s)

    if dynamic_type == 'operator':
        # For operators, we split Name and Descriptor with ;
        # args_str: Op, Desc

        balance = 0
        split_idx = -1
        for i, char in enumerate(s):
            if char == '<':
                balance += 1
            elif char == '>':
                balance -= 1
            elif char == ',' and balance == 0:
                split_idx = i
                break

        if split_idx != -1:
            op = s[:split_idx].strip()
            desc = s[split_idx+1:].strip()
            s = f"{op};{desc}"

    return s

def write_generated_cse(filepath, entries, dynamic_type):
    # entries: filename -> comment
    # Sort by comment string
    sorted_entries = sorted(entries.items(), key=lambda x: x[1])

    with open(filepath, 'w') as f:
        f.write("/*  ========================================================\n")
        f.write(" *  ==  WARNING: This is an automatically generated file, ==\n")
        f.write(" *  ==                  do not modify.                    ==\n")
        f.write(" *  ========================================================\n")
        f.write(" */\n\n")
        f.write("#ifndef DISABLE_CSE\n\n")

        for filename, comment in sorted_entries:
            f.write(f"//{comment}\n")
            f.write(f'#include "{filename}"\n\n')

        f.write("#endif\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_cse_includes.py <type> <olb_root>")
        sys.exit(1)

    dynamic_type = sys.argv[1] # 'dynamics' or 'operator'
    olb_root = sys.argv[2]

    base_dir = os.path.join(olb_root, "src/cse", dynamic_type)
    generated_file = os.path.join(base_dir, "generated_cse.h")

    entries = parse_generated_cse(generated_file)

    cse_files = get_cse_files(base_dir)

    for cse_file in cse_files:
        filename = os.path.basename(cse_file)
        if filename == "generated_cse.h":
            continue

        if filename not in entries:
            # Reconstruct comment
            with open(cse_file, 'r') as f:
                content = f.read()

            if not content.strip():
                print(f"Warning: Empty file {filename}. Skipping.")
                continue

            args_str = extract_template_args(content, dynamic_type)
            if args_str:
                comment = reconstruct_comment(args_str, dynamic_type)
                entries[filename] = comment
            else:
                print(f"Warning: Could not extract template args from {filename}")
                entries[filename] = "Unknown dynamics/operator"

    # Remove entries that no longer exist on disk
    existing_filenames = set(os.path.basename(f) for f in cse_files)
    entries = {k: v for k, v in entries.items() if k in existing_filenames}

    write_generated_cse(generated_file, entries, dynamic_type)
