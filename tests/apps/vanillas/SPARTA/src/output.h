/* ----------------------------------------------------------------------
   SPARTA - Stochastic PArallel Rarefied-gas Time-accurate Analyzer
   http://sparta.github.io
   Steve Plimpton, sjplimp@gmail.com, Michael Gallis, magalli@sandia.gov
   Sandia National Laboratories

   Copyright (2014) Sandia Corporation.  Under the terms of Contract
   DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains
   certain rights in this software.  This software is distributed under
   the GNU General Public License.

   See the README file in the top-level SPARTA directory.
------------------------------------------------------------------------- */

#ifndef SPARTA_OUTPUT_H
#define SPARTA_OUTPUT_H

#include "pointers.h"

namespace SPARTA_NS {

class Output : protected Pointers {
 public:
  bigint next;                 // next timestep for any kind of output

  bigint next_stats;           // next timestep for stats output
  int stats_every;             // stats output every this many steps
  bigint last_stats;           // last timestep stats was output
  char *var_stats;             // variable name for stats frequency
  int ivar_stats;              // variable index for stats frequency
  class Stats *stats;          // statistical output

  int ndump;                   // # of Dumps defined
  int max_dump;                // max size of Dump list
  bigint next_dump_any;        // next timestep for any Dump
  int *every_dump;             // output of each Dump every this many steps
  bigint *next_dump;           // next timestep to do each Dump
  bigint *last_dump;           // last timestep each snapshot was output
  char **var_dump;             // variable name for dump frequency
  int *ivar_dump;              // variable index for dump frequency
  class Dump **dump;           // list of defined Dumps

  Output(class SPARTA *);
  ~Output();
  void init();
  void setup(int);                   // initial output before run/min
  void write(bigint);                // output for current timestep
  void write_dump(bigint);           // force output of dump snapshots
  void reset_timestep(bigint);       // reset next timestep for all output

  void add_dump(int, char **);       // add a Dump to Dump list
  void modify_dump(int, char **);    // modify a Dump
  void delete_dump(char *);          // delete a Dump from Dump list

  void set_stats(int, char **);      // set stats output frequency
  void create_stats(int, char **);   // create a Stats style

  void memory_usage();               // print out memory usage
};

}

#endif

/* ERROR/WARNING messages:

E: Variable name for stats every does not exist

Self-explanatory.

E: Variable for stats every is invalid style

It must be an equal-style variable.

E: Variable name for dump every does not exist

Self-explanatory.

E: Variable for dump every is invalid style

Only equal-style variables can be used.

E: Dump every variable returned a bad timestep

The variable must return a timestep greater than the current timestep.

E: Stats every variable returned a bad timestep

The variable must return a timestep greater than the current timestep.

E: Stats_modify every variable returned a bad timestep

The variable must return a timestep greater than the current timestep.

E: Illegal ... command

Self-explanatory.  Check the input script syntax and compare to the
documentation for the command.  You can use -echo screen as a
command-line option when running SPARTA to see the offending line.

E: Reuse of dump ID

A dump ID cannot be used twice.

E: Invalid dump frequency

Dump frequency must be 1 or greater.

E: Invalid dump style

The choice of dump style is unknown.

E: Cound not find dump_modify ID

Self-explanatory.

E: Could not find undump ID

A dump ID used in the undump command does not exist.

*/
