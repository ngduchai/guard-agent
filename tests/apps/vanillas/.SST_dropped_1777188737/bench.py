"""SST validation benchmark — 16-component ring on simpleElementExample.basicLinks.

Each component sends EVENTS messages around a 16-rank ring topology.  Sized for
~120s wall time at 4 MPI ranks on a typical dev machine so the LLM checkpoint
cadence has multiple opportunities to fire before the 95% injection delay.
No checkpoint flags are set in the config itself; the validation framework
adds them on the CLI for the resilient run only.
"""
import sst

N = 16
EVENTS = 33000000

comps = []
for i in range(N):
    c = sst.Component(f"c{i}", "simpleElementExample.basicLinks")
    c.addParams({
        "eventsToSend": EVENTS,
        "eventSize": 16,
        "rngSeedZ": 12 + i,
        "rngSeedW": 438949 + i,
    })
    comps.append(c)

# Ring topology: c[i].port_handler ↔ c[(i+1)%N].port_polled
for i in range(N):
    j = (i + 1) % N
    sst.Link(f"l{i}").connect(
        (comps[i], "port_handler", "1ns"),
        (comps[j], "port_polled", "1ns"),
    )
