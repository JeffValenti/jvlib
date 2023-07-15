from time import monotonic_ns, process_time_ns
from tracemalloc import get_traced_memory, reset_peak, start as tm_start


class MonitorTimeMemory:
    '''Monitor execution time and memory usage.'''

    def __init__(self, autoprint=False):
        self.autoprint = autoprint
        self._history = ['   tep tei,  tpp tpi   |   Msp Msi, Mpc    | Label']
        tm_start()
        self.telapinit = monotonic_ns() / 1e9
        self.tprocinit = process_time_ns() / 1e9
        self.msizeinit, self.mpeakinit = [
            m / 1e9 for m in get_traced_memory()]
        self.telapcurr = self.telapinit
        self.tproccurr = self.tprocinit
        self.msizecurr = self.msizeinit
        self.mpeakcurr = self.mpeakinit

    def __call__(self, label):
        '''Measure execution time and memory usage. Print if autoprint.

        Parameters
        ----------
        label : str
            annotation to include at end of status line.

        Notes
        -----
        Adds status line to self.history.
        Prints status line if autoprint is True.
        '''
        time_snapshot = self.get_time()
        memory_snapshot = self.get_memory()
        line = self._make_status_line(time_snapshot, memory_snapshot, label)
        self._history.append(line)
        if self.autoprint:
            print(line)
        return line

    @property
    def history(self):
        '''Print all status lines in history.

        Notes
        -----
        Fromat of output lines:
            t tep tei, tpp tpi s | M Msp Msi, Mpc GB | label
        where:
            te is elapsed time, tp is process CPU time in seconds
            Ms is allocated memory size, Mp is peak memory in GB
            p is measure during previous call, i is increament this call
        '''
        return self._history

    def _make_status_line(self, time_snapshot, memory_snapshot, label):
        '''Return str with formatted status info for one measurement.

        Parameters
        ----------
        time_snapshot : tuple of float
            execution time measurements from get_time()
        memory_snapshot : tuple of float
            memory usage measurements from get_memory()
        label : str
            annotation to include at end of status line.
        '''
        tep, tei, tec, tpp, tpi, tpc = time_snapshot
        msp, msi, msc, mpp, mpi, mpc = memory_snapshot
        line = (
            f't {tep:4.0f}{tei:+4.0f}, {tpp:4.0f}{tpi:+4.0f} s | '
            f'M {msp:3.0f}{msi:+4.0f}, {mpc:3.0f} GB | {label}')
        return line

    def get_time(self):
        '''Return elapsed user+system CPU times for current process.

        Returns
        -------
        telapprev : float
            elapsed time during previous measurement [s]
        telapinc : float
            increment in elapsed time since previous measurement [s]
        telapcum : float
            cumulative elapsed time during this measurement [s]
        tprocprev : float
            user+system CPU time during previous measurement [s]
        tprocinc : float
            increment in user+system CPU time since previous measurement [s]
        tproccum : float
            cumulative user+system CPU time during this measurement [s]

        Notes
        -----
        We divide by 1e9 to convert times reported in ns to seconds.
        We subtract telapinit from telapprev so initial time is 0 s.
        '''
        self.telapprev = self.telapcurr
        self.tprocprev = self.tproccurr
        self.telapcurr = monotonic_ns() / 1e9
        self.tproccurr = process_time_ns() / 1e9
        telapinc = self.telapcurr - self.telapprev
        telapcum = self.telapcurr - self.telapinit
        tprocinc = self.tproccurr - self.tprocprev
        tproccum = self.tproccurr - self.tprocinit
        telapprev = self.telapprev - self.telapinit
        return (
            telapprev, telapinc, telapcum,
            self.tprocprev, tprocinc, tproccum)

    def get_memory(self):
        '''Return current and peak allocated memory  for current process.

        Returns
        -------
        msizeprev : float
            allocated memory during previous measurement [GB]
        msizeinc : float
            allocated memory increment since previous measurement [GB]
        msizecum : float
            cumulative allocated memory during this measurement [GB]
        mpeakprev : float
            peak allocated memory during previous measurement [GB]
        mpeakinc : float
            increment in peak allocated memory since previous measurement [GB]
        mpeakcum : float
            peak allocated memory during this measurement [GB]

        Notes
        -----
        We divide by 1e9 to convert memory reported in bytes to GB.
        '''
        self.msizeprev = self.msizecurr
        self.mpeakprev = self.mpeakcurr
        self.msizecurr, self.mpeakcurr = [
            m / 1e9 for m in get_traced_memory()]
        msizeinc = self.msizecurr - self.msizeprev
        msizecum = self.msizecurr - self.msizeinit
        mpeakinc = self.mpeakcurr - self.mpeakprev
        mpeakcum = self.mpeakcurr - self.mpeakinit
        return (
            self.msizeprev, msizeinc, msizecum,
            self.mpeakprev, mpeakinc, mpeakcum)
