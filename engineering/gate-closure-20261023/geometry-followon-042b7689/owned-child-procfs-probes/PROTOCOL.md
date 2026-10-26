# Own-child procfs mapping: actual diagnostic and r3 contract

## Actual result

The isolated stdlib diagnostic started exactly one new child and completed in
0.037779974 seconds. It used `python -I -S -B`, a separate 128 MiB address-space
limit, a 2-second CPU limit, a 9-second parent deadline and a target RSS below
32 MiB. These are diagnostic limits; no native guard changed.

The observed parent was PID 2 in its namespace and PID 423162 in the procfs view.
The child was `Popen.pid == os.getpid() == 5`, but its own `/proc/self` link was
423165. Its `NSpid` was `[423165, 5]`, procfs PPid was 423162, starttime was
2822296 ticks, and parent/child PID namespace links both read `pid:[4026532277]`.
The parent read the exact child's procfs RSS/HWM as 12,324,864 bytes. The child
reported its own `ru_maxrss` as 12,189,696 bytes; these are separately recorded
observations, not asserted to be identical. The child exited 0 and was reaped;
all dedicated pipe descriptors were closed. Stdout and stderr were saved,
including an empty stderr file. No unrelated procfs path was opened or scanned.

The first probe remains unchanged in the parent directory. It exited -6 before
handshake under an additional 32 MiB address-space limit. Its failure branch
did not preserve stderr; that execution therefore does not establish a child
mapping or the cause of the abort.

## Dedicated handshake framing

The supervisor creates a unique inherited pipe and a fresh random nonce for
its one worker. The worker emits exactly one UTF-8 JSON line, below 4096 bytes,
through the assigned file descriptor, then closes that write descriptor.
The diagnostic used a second dedicated release pipe to keep the child alive
while the parent inspected it. A production worker can use the same ready/
release arrangement before CAD imports so an unverified mapping cannot enter
heavy work.

The actual packet fields are:

```text
kind
nonce
source_sha256
os_getpid
os_getppid
proc_self_visible_pid
status: {Pid, PPid, NSpid, VmRSS_bytes, VmHWM_bytes}
stat: {pid, ppid, starttime_ticks, state, comm}
pid_namespace
pid_for_children_namespace
```

The probe's `isolated_python` and `no_site` flags belong only to this diagnostic;
they do not impose `-I -S` on the CAD worker's existing locked environment.

## Parent verification before using memory values

1. Verify the nonce, packet framing and the already frozen worker source hash.
   Require a positive numeric `proc_self_visible_pid`; never accept a path from
   the child, and never scan procfs to find a possible worker.
2. Require the packet's namespace PID to equal the original `Popen.pid` and its
   namespace PPID to equal the supervisor's `os.getpid()`.
3. Read only `/proc/<reported-visible-pid>/{status,stat,ns/pid,ns/pid_for_children}`.
   Require status/stat PID to equal that visible PID and procfs PPid to equal
   the supervisor's own `/proc/self` visible PID.
4. Require the observed `NSpid` chain to equal the child's self-report, its last
   entry to equal `Popen.pid`, and its first entry to equal the visible PID.
   Require the actual PID namespace and PID-for-children namespace to match
   the self-report and the ordinary parent/child namespace relationship.
5. Require `stat.starttime` to match the child's self-report. Read identity
   before and after RSS inspection; verify the same PID, PPid, starttime,
   namespaces and `NSpid`, while confirming the original Popen child remains
   alive. Repeat identity binding on later samples to detect stale paths.
6. Require positive, finite RSS/HWM observations in the expected `kB` units.
   Missing files/fields, empty dictionaries, zero values, malformed data or
   identity changes must stop qualification; they cannot mean zero memory.

Process termination and reaping must continue to use the original owned Popen
handle/PID in the parent's namespace. Do not signal the procfs-visible PID.
Pipe/JSON/procfs/save exceptions must reach the existing cleanup path.

The real diagnostic demonstrates that this mapping is available in the current
environment. It does not prove that an unreviewed implementation is correct,
that every later process has the same namespace layout, or that old native
executions had a working RSS sampler. r3 must verify the mapping afresh and
retain the original native memory/time/disk limits.

## Original invocation

```bash
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -I -S -B \
  /workspace/scratch/95cd2986fdf2/gates_audit/process-namespace-probe/v2/probe_child_proc_mapping.py \
  --output /workspace/scratch/95cd2986fdf2/gates_audit/process-namespace-probe/v2/executed-attempt
```

The output directory is immutable after this invocation. A new invocation
would require a fresh directory and separate authorization for another child.
