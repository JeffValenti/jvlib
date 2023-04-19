from pathlib import Path
from shutil import copy
from subprocess import run as subprocess_run

from astropy.io.fits import open as fits_open

from jvlib.util.path import pathlist
from jvlib.calwebb.assoc import JwstAssociationInfo


class CalwebbReprocessAssociations:
    '''Reprocess JWST associations with calwebb in conda environment.'''
    def __init__(
            self, condaenv, jsonspec, indir='.', outdir='.', loglevel='DEBUG'):
        self.condaenv = condaenv
        self.jsonspec = jsonspec
        self.indir = Path(indir).expanduser().absolute().resolve()
        self.outdir = Path(outdir).expanduser().absolute().resolve()
        self.loglevel = loglevel
        self.jsonpaths = pathlist(jsonspec)
        if not self.jsonpaths:
            raise FileNotFoundError(f'No files match jsonspec: {jsonspec}')
        self._check_filenames()

    def reprocess(self):
        '''Loop through paths. Setup and run reprocessing job.'''
        print(f'condaenv = {self.condaenv}')
        print(f'indir = {self.indir}')
        print(f'outdir = {self.outdir}')
        print(f'loglevel = {self.loglevel}')
        for jsonpath in self.jsonpaths:
            print(f'jsonfile = {jsonpath.name}')
            reprocess = CalwebbReprocessAssociationSetup(
                jsonpath, indir=self.indir, outdir=self.outdir,
                loglevel=self.loglevel)
            reprocess.run(self.condaenv)

    def _check_filenames(self):
        '''Check that input filenames have expected format.'''
        badpaths = [
            path for path in self.jsonpaths if path.name[-9:] != '_asn.json']
        if badpaths:
            badnames = ','.join([path.name for path in badpaths])
            raise ValueError(f'Bad suffix for jsonspec files: {badnames}')

class CalwebbReprocessAssociationSetup:
    '''Create directory to reprocess an input association file with calwebb.

    Arguments:
        jsonpath (str, Path) _asn.json file
        indir (str, Path) directory containing all input data. Default is CWD
        outdir (str, Path) directory to store all output. Default is CWD
        loglevel (str) DEBUG (default), INFO, WARNING, ERROR, or CRITICAL
    '''
    def __init__(self, injson, indir='.', outdir='.', loglevel='DEBUG'):
        self.injson = Path(injson).expanduser().absolute()
        self.indir = Path(indir).expanduser().absolute()
        self.outdir = Path(outdir).expanduser().absolute()
        self.loglevel = loglevel
        self.name = self.injson.stem
        self.outdir.mkdir(mode=0o750, parents=True, exist_ok=True)
        self.json = copy(self.injson, self.outdir / self.injson.name)
        self.info = JwstAssociationInfo(self.json)
        self.pipeline = self.info.pipeline
        self.members = self._create_link_to_members()
        self.logcfgpath, self.logpath = self._create_logcfg_file()
        self.scriptpath = self._create_python_script()

    def run(self, condaenv):
        '''Run the reprocessing script in the specified conda environment.'''
        cmdstr = (
            f'conda run -n {condaenv} --cwd {self.outdir} '
            f'python {self.scriptpath}')
        subprocess_run(cmdstr, shell=True, check=True)

    def _create_link_to_members(self):
        '''Create symbolic link to members, unless file is in outdir.'''
        linkpaths = []
        for member in self.info.members:
            memberpath = self.indir / member
            if not memberpath.is_file():
                raise FileNotFoundError(f'Member not found: {memberpath}')
            linkpath = self.outdir / member
            if linkpath != memberpath:
                if linkpath.is_symlink():
                    linkpath.unlink()
                if linkpath.is_file():
                    raise Exception(f'Member already exists: {linkpath}')
                linkpath.symlink_to(memberpath)
            linkpaths.append(linkpath)
        return linkpaths

    def _create_logcfg_file(self):
        '''Create file in outdir that configures calwebb logging.'''
        logcfgpath = self.outdir / f'{self.name}.cfglog'
        logpath = self.outdir / f'{self.name}.log'
        text = (
            f'[*]\n'
            f'handler = file:{logpath}\n'
            f'level = {self.loglevel}\n')
        with open(logcfgpath, 'w') as textio:
            textio.write(text)
        return logcfgpath, logpath

    def _create_python_script(self):
        '''Create python script to execute calwebb reprocessing job.'''
        for member in self.members:
            assert member.parent == self.outdir
        assert self.logcfgpath.parent == self.outdir
        text = (
            f'#!/usr/bin/env python\n\n'
            f'from jwst.pipeline import {self.pipeline}\n\n'
            f'outdir = "{self.outdir}"\n'
            f'result = {self.pipeline}.call(\n'
            f'    f"{{outdir}}/{self.json.name}",\n'
            f'    logcfg=f"{{outdir}}/{self.logcfgpath.name}",\n'
            f'    save_results=True)\n')
        scriptpath = self.outdir / f'{self.name}.py'
        with open(scriptpath, 'w') as textio:
            textio.write(text)
        scriptpath.chmod(0o750)
        return scriptpath


class CalwebbReprocessExposures:
    '''Reprocess the specified input exposure files with calwebb pipeline.'''
    def __init__(self, condaenv, pathspec, outdir='.', loglevel='DEBUG'):
        self.condaenv = condaenv
        self.pathspec = pathspec
        self.outdir = Path(outdir).expanduser().absolute()
        self.loglevel = loglevel
        self.paths = pathlist(pathspec)
        self._check_filenames()

    def reprocess(self):
        '''Loop through paths. Setup and run reprocessing job.'''
        print(f'condaenv = {self.condaenv}')
        print(f'outdir = {self.outdir}')
        print(f'loglevel = {self.loglevel}')
        for path in self.paths:
            print(f'inputfile = {path.name}')
            reprocess = CalwebbReprocessExposureSetup(
                path, outdir=self.outdir, loglevel=self.loglevel)
            reprocess.run(self.condaenv)
            for nextpath in reprocess.nextpath:
                print(f'    nextpath = {nextpath.name}')
                nextstage = CalwebbReprocessExposureSetup(
                    nextpath, outdir=self.outdir, loglevel=self.loglevel)
                nextstage.run(self.condaenv)

    def _check_filenames(self):
        '''Check that input filenames have expected format.'''
        badpaths = [
            path for path in self.paths
            if path.stem[:2] != 'jw'
            or not path.stem[2:13].isdigit()
            or path.stem.rsplit('_', 1)[1] not in ['uncal', 'rate', 'rateints']
            or path.suffix != '.fits']
        if badpaths:
            badnames = ','.join([path.name for path in badpaths])
            raise ValueError(f'Unexpected input filenames: {badnames}')

class CalwebbReprocessExposureSetup:
    '''Create directory to reprocess an input exposure file with calwebb.

    Arguments:
        inputpath (str, Path) _uncal.fits, _rate.fits, or _rateints.fits file
        outdir (str, Path) directory to store all output. Default is CWD
        loglevel (str) DEBUG (default), INFO, WARNING, ERROR, or CRITICAL
    '''
    def __init__(self, inputfile, outdir='.', loglevel='DEBUG'):
        self.inputpath = Path(inputfile).expanduser().absolute()
        self.outdir = Path(outdir).expanduser().absolute()
        self.loglevel = loglevel
        self.prefix, self.suffix = self.inputpath.stem.rsplit('_', 1)
        self.exptype, self.nints, self.pipeline = self._select_pipeline()
        self.outdir.mkdir(mode=0o750, parents=True, exist_ok=True)
        self.symlink = self._create_link_to_inputfile()
        self.logcfgpath, self.logpath = self._create_logcfg_file()
        self.scriptpath = self._create_python_script()
        self.nextpath = self._predict_next_stage_inputs()

    def run(self, condaenv):
        '''Run the reprocessing script in the specified conda environment.'''
        cmdstr = (
            f'conda run -n {condaenv} --cwd {self.outdir} '
            f'python {self.scriptpath}')
        subprocess_run(cmdstr, shell=True, check=True)

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

    def _predict_next_stage_inputs(self):
        '''Predict input files (if any) for next calwebb pipeline stage.'''
        if self.suffix == 'uncal':
            if self.nints == 1:
                return [Path(f'{self.outdir}/{self.prefix}_rate.fits')]
            else:
                return [
                    Path(f'{self.outdir}/{self.prefix}_{suffix}.fits')
                    for suffix in ['rate', 'rateints']]
        elif self.suffix in ['rate', 'rateints']:
            return []
        else:
            raise ValueError(f'next stage unknown for suffix={self.suffix}')

    def _select_pipeline(self):
        '''Determine which pipeline to invoke when reprocessing input file.'''
        try:
            with fits_open(self.inputpath) as hdulist:
                exptype = hdulist['primary'].header['exp_type']
                nints = hdulist['primary'].header['nints']
        except FileNotFoundError as e:
            raise Exception(f'Input file not found: {self.inputpath}')
        if self.suffix == 'uncal':
            return exptype, nints, 'Detector1'
        elif exptype in ['NRS_WATA', 'NRS_TACONFIRM', 'MIR_TACQ', 'MIR_IMAGE']:
            return exptype, nints, 'Image2'
        elif exptype in ['NRS_FIXEDSLIT', 'MIR_MRS']:
            return exptype, nints, 'Spec2'
        else:
            raise ValueError(f'No pipeline for exptype={exptype}')
