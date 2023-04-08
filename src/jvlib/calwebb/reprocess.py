from pathlib import Path

from astropy.io.fits import open as fits_open


class CalwebbReprocessExposure:
    '''Manage a calwebb job to reprocess an exposure.

    Arguments:
        inputpath (str, Path) _uncal.fits, _rate.fits, or _rateints.fits file
        outdir (str, Path) directory to store all output. Default is CWD
        loglevel (str) DEBUG (default), INFO, WARNING, ERROR, or CRITICAL
    '''
    def __init__(self, inputfile, outdir='.', loglevel='DEBUG'):
        self.inputpath = Path(inputfile).expanduser().absolute()
        self.outdir = Path(outdir).absolute()
        self.loglevel = loglevel
        self.prefix, self.suffix = self.inputpath.name.rsplit('_', 1)
        self.exptype, self.pipeline = self._select_pipeline()
        self.outdir.mkdir(mode=0o750, parents=True, exist_ok=True)
        self.symlink = self._create_link_to_inputfile()
        self.logcfgpath, self.logpath = self._create_logcfg_file()
        self.scriptpath = self._create_python_script()
        self.nextstage = self._determine_next_stage()

    def _create_link_to_inputfile(self):
        '''Create symbolic link to input file, unless file is in outdir.'''
        if self.inputpath.parent == self.outdir:
            return self.inputpath
        linkpath = self.outdir / self.inputpath.name
        if linkpath.exists():
            assert linkpath.is_symlink()
            linkpath.unlink()
        linkpath.symlink_to(self.inputpath)
        return linkpath

    def _create_logcfg_file(self):
        '''Create file in outdir that configures calwebb logging.'''
        stem = self.inputpath.stem
        logcfgpath = self.outdir / f'{stem}.cfglog'
        logpath = self.outdir / f'{stem}.log'
        text = (
            f'[*]\n'
            f'handler = file:{logpath}\n'
            f'level = {self.loglevel}\n')
        with open(logcfgpath, 'w') as textio:
            textio.write(text)
        return logcfgpath, logpath

    def _create_python_script(self):
        '''Create python script to execute calwebb reprocessing job.'''
        assert self.symlink.parent == self.outdir
        assert self.logcfgpath.parent == self.outdir
        text = (
            f'#!/usr/bin/env python\n\n'
            f'from jwst.pipeline import {self.pipeline}Pipeline\n\n'
            f'outdir = "{self.outdir}"\n'
            f'result = {self.pipeline}Pipeline.call(\n'
            f'    f"{{outdir}}/{self.symlink.name}",\n'
            f'    logcfg=f"{{outdir}}/{self.logcfgpath.name}",\n'
            f'    save_results=True)\n')
        scriptpath = self.outdir / f'{self.inputpath.stem}.py'
        with open(scriptpath, 'w') as textio:
            textio.write(text)
        scriptpath.chmod(0o750)
        return scriptpath

    def _determine_next_stage()
        '''If input is uncal, return pipeline to handle next stage.'''
        if self.suffix == 'uncal':
            return {'rate': self.pipeline, 'rateints': self.pipeline}
        elif self.suffix in ['rate', 'rateints']:
            return {}
        else:
            raise ValueError(f'next stage unknown for suffix={self.suffix}')

    def _select_pipeline(self):
        '''Determine which pipeline to invoke when reprocessing input file.'''
        try:
            with fits_open(self.inputpath) as hdulist:
                exptype = hdulist['primary'].header['exp_type']
        except FileNotFoundError as e:
            raise Exception(f'Input file not found: {self.inputpath}')
        if self.suffix == 'uncal':
            return exptype, 'Detector1'
        elif exptype in ['NRS_WATA', 'NRS_TACONFIRM']:
            return exptype, 'Image2'
        elif exptype in ['NRS_FIXEDSLIT']:
            return exptype, 'Spec2'
        else:
            raise ValueError(f'No pipeline for exptype={exptype}')
