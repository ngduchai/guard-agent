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
import re

def format_string(s):
    s = s.replace(" ", "")
    s = s.replace("double", "Expr")
    s = s.replace("float", "Expr")
    s = s.replace("olb::", "")

    # Process descriptors::NAME<...>
    # We want to find patterns like descriptors::Something<A,B,C> and filter the args.
    output = []
    i = 0
    n = len(s)

    while i < n:
        match = re.match(r'descriptors::(\w+)<', s[i:])
        if match:
            # We found a descriptor start
            prefix = match.group(0) # e.g. descriptors::D2Q9<
            output.append(prefix)
            i += len(prefix)

            # Now we are inside <...>. We need to capture until balanced >
            # and split by comma at top level.
            # Then filter and sort.
            args = []
            current_arg = []
            balance = 1
            while i < n and balance > 0:
                char = s[i]
                if char == '<':
                    balance += 1
                    current_arg.append(char)
                elif char == '>':
                    balance -= 1
                    if balance == 0:
                        # End of descriptor
                        if current_arg:
                            args.append("".join(current_arg))
                        break
                    current_arg.append(char)
                elif char == ',' and balance == 1:
                    args.append("".join(current_arg))
                    current_arg = []
                else:
                    current_arg.append(char)
                i += 1

            # Filter and sort args
            # Keep if contains "tag::" as this impacts static branching in some cases
            filtered_args = [arg for arg in args if "tag::" in arg]
            filtered_args.sort()

            output.append(",".join(filtered_args))
            output.append(">")
            i += 1 # Skip the closing >

        else:
            output.append(s[i])
            i += 1

    return "".join(output)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_str = sys.argv[1]
        print(format_string(input_str))
