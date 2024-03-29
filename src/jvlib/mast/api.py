from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from requests import get as requests_get
from os import getenv

from astropy.table import Column, unique as table_unique
from astropy.time import Time
from astroquery.mast import Mast, Observations
from numpy import isnan as np_isnan, sum as np_sum


class JwstProgramData:
    '''Interface with MAST archive for specified JWST program.'''
    def __init__(self, progid):
        self.progid = int(progid)
        self.datasets = Observations.query_criteria(
            obs_collection='Jwst', proposal_id=progid)
        self.files = Observations.get_product_list(self.datasets)
        self.files = table_unique(self.files, keys='productFilename')
        self.files['name'] = self.files['productFilename']
        self._add_metadata()
        self._set_valid_constraints()
        self.set_constraints()

    def _add_metadata(self):
        '''Add useful metadata columns to table of files in MAST.'''
        self._set_inst()
        self._set_filetype()
        self._set_obs()

    def _force_list_containing_type(self, obj, elemtype):
        '''Return a list containing elements with the specified type.'''
        if obj is None:
            return []
        elif isinstance(obj, str):
            return [elemtype(obj)]
        try:
            return [elemtype(value) for value in obj]
        except TypeError:
            return [elemtype(obj)]

    def _infer_filetype(self, filename):
        '''Return a filetype inferred from the specified filename.'''
        stem, exten = filename.split('.')
        suffix = stem.split('_')[-1]
        if exten in ['jpg']:
            return exten
        elif '_gs-' in stem:
            prefix = stem.split('_gs-')[1].split('_')[0]
            return f'{prefix}_{suffix}'
        else:
            return suffix

    def _set_filetype(self):
        '''Set filetype based on filename.'''
        self.files['filetype'] = [
            self._infer_filetype(f) for f in self.files['productFilename']]

    def _set_inst(self):
        '''Set instrument based on filename and parent_obsid.'''
        inst_names = dict(
            gs='fgs', mir='mir', nis='nis', niriss='nis',
            nrc='nrc', nircam='nrc', nrs='nrs', nirspec='nrs')
        self.files['inst'] = Column([''] * len(self.files), dtype='object')
        for file in self.files:
            for substr in inst_names:
                if substr in file['productFilename']:
                    file['inst'] = inst_names[substr]
        for file in self.files:
            if file['inst'] != '':
                continue
            siblings = self.files['parent_obsid'] == file['parent_obsid']
            inst = [i for i in self.files['inst'][siblings] if i != '']
            if inst and all([i in [inst[0], 'fgs'] for i in inst]):
                file['inst'] = inst[0]

    def _set_obs(self):
        '''Set observation number based on filename and parent_obsid.'''
        prefix = f'jw{self.progid:05d}'
        self.files['obs'] = [
            int(f[7:10]) if f[:7] == prefix and f[7:10].isdecimal() else 0
            for f in self.files['productFilename']]
        for file in self.files:
            if file['obs'] != 0:
                continue
            siblings = self.files['parent_obsid'] == file['parent_obsid']
            obs = [o for o in self.files['obs'][siblings] if o != 0]
            if obs and all([o == obs[0] for o in obs]):
                file['obs'] = obs[0]

    def _set_valid_constraints(self):
        self.valid_inst = ['fgs', 'mir', 'nrc', 'nis', 'nrs']
        self.valid_filetype = [
            'acq1_cal', 'acq1_stream', 'acq1_uncal', 'acq2_cal',
            'acq2_stream', 'acq2_uncal', 'asn', 'cal', 'calints',
            'crfints', 'fg_cal', 'fg_stream', 'fg_uncal', 'id_cal',
            'id_stream', 'id_uncal', 'jpg', 'pool', 'ramp', 'rate',
            'rateints', 's2d', 'track_cal', 'track_stream',
            'track_uncal', 'uncal', 'whtlt', 'x1d', 'x1dints']

    def _parse_constraint_string(self, constraint_string):
        '''Parse string with comma-separated constraints.'''
        instlist = None
        obslist = None
        filetypelist = None
        constraint_list = [c.strip() for c in constraint_string.split(',')]
        if constraint_list != ['']:
            for constraint in constraint_list:
                if constraint in self.valid_inst:
                    if instlist:
                        instlist.append(constraint)
                    else:
                        instlist = [constraint]
                elif constraint in self.valid_filetype:
                    if filetypelist:
                        filetypelist.append(constraint)
                    else:
                        filetypelist = [constraint]
                else:
                    try:
                        if obslist:
                            obslist.append(int(constraint))
                        else:
                            obslist = [int(constraint)]
                    except ValueError as e:
                        raise Exception(
                            f'unrecognized constraint: {constraint}')
        return instlist, obslist, filetypelist

    @property
    def filenames(self):
        '''Return lsit of filenames that satisfy constraints.'''
        return [f for f in self.files['name'][self.subset]]

    def apply_constraint_string(self, constraint_string):
        '''Set inst, obs, and filetype constraints from constraint string.'''
        inst, obs, filetype = self._parse_constraint_string(constraint_string)
        self.set_constraints(inst=inst, obs=obs, filetype=filetype)

    def browse_files(self):
        '''Display self.files table in a browser window.'''
        self.files[self.subset].show_in_browser(jsviewer=True)

    def browse_datasets(self):
        '''Display self.datasets table in a browser window.'''
        self.datasets.show_in_browser(jsviewer=True)

    def download_files(self, existing='keep', auth=True):
        '''Download from MAST files that satisfy constraints.'''
        for filename in self.filenames:
            if existing == 'keep':
                if Path(filename).is_file():
                    print(f'keeping local {filename}')
                    continue
            elif existing == 'replace':
                pass
            else:
                raise ValueError('existing={existing} is not valid')
            print(f'downloading {filename}')
            get_jwst_file(filename, auth=auth)

    def set_constraints(self, inst=None, obs=None, filetype=None):
        '''Set mask for self.files that satisfies specified criteria.'''
        instlist = self._force_list_containing_type(inst, str)
        obslist = self._force_list_containing_type(obs, int)
        filetypelist = self._force_list_containing_type(filetype, str)
        self.subset = [
            True if (inst is None or f['inst'] in instlist)
            and (obs is None or f['obs'] in obslist)
            and (filetype is None or f['filetype'] in filetypelist)
            else False for f in self.files]

    def summarize(self, key):
        '''Summarize MAST data holdings for the program by specified key.'''
        table = self.files[key, 'size'][self.subset]
        table['nfile'] = 1
        grouped_table = table.group_by(key)
        grouped_table = grouped_table[key, 'nfile', 'size']
        return grouped_table.groups.aggregate(np_sum)


class JwstFilteredQuery:
    '''Manage MAST API query based on JWST FITS header keyword values.

    Example:
        query = JwstFilteredQuery('Nirspec')
        query.filter_by_values('readpatt', 'NRSRAPID, NRSIRS2RAPID')
        query.filter_by_minmax('nints', 2, 99)
        query.filter_by_timerange('date_beg', '2022-04-02 05:00:00', 59671.8)
        query.append_output_columns('pi_name')
        query.execute_query()
        query.get_caom_product_list()
        query.browse()
    '''
    def __init__(self, collection):
        self._collection = collection
        self._service = f'Mast.Jwst.Filtered.{collection}'
        self.set_output_columns_to_default()
        self.filters = []
        self._params = None
        self.result = None
        self.caom_product_list = None
        self._dataset = None

    @property
    def collection(self):
        '''Return JWST collection specified during instantiation.'''
        return self._collection

    @property
    def service(self):
        '''Return service access point for specified JWST collection.'''
        return self._service

    @property
    def params(self):
        '''Return parameter dictionary for most recent query.'''
        return self._params

    @property
    def dataset(self):
        '''Return dataset names for most recent query.'''
        return self._dataset

    @property
    def caom_obsid(self):
        '''Return CAOM obsid for datasets returned by the most recent query.'''
        return self._caom_obsid

    def filter_by_values(self, keyword, values):
        '''Require keyword value to be in enumerated list.

        Input values may be str with comma-separated values or list of str.
        Whitespace around commas is ignored
        Examples:
            filter_by_values('detector', 'NRS1')
            filter_by_values('detector', 'NRS1,NRS2')
            filter_by_values('detector', 'NRS1, NRS2')
            filter_by_values('detector', ['NRS1'])
            filter_by_values('detector', ['NRS1', 'NRS2'])
        '''
        try:
            valuelist = [v.strip() for v in values.split(',')]
        except AttributeError:
            valuelist = [str(v) for v in values]
        newfilter = {
            'paramName': str(keyword),
            'values': valuelist}
        self.filters.append(newfilter)

    def filter_by_minmax(self, keyword, minval, maxval):
        '''Require keyword value to be in specified range.

        Example:
            filter_by_values('nints', 2, 99)
        '''
        newfilter = {
            'paramName': str(keyword),
            'values': [{'min': minval, 'max': maxval}]}
        self.filters.append(newfilter)

    def filter_by_timerange(self, keyword, mintime, maxtime):
        '''Require time in keyword value to be in specified range.

        Specified keyword should have values that are absolute times.
        Apply filter to _mjd keyword because query fails for non-mjd keywords.
        Input times may be JD, MJD, astropy Time, datetime, or ISO 8601 string.
        Examples:
            filter_by_timerange('date_obs', '2022-04-02', '2022-04-03')
            filter_by_timerange('date_beg', '2022-04-02T11:00:00', 59671.5)
            filter_by_timerange('date_beg', '2022-04-02 11:00:00', 2459672)
        '''
        if keyword.lower().endswith('_mjd'):
            kw = keyword
        else:
            kw = keyword + '_mjd'
        try:
            minmjd = mjd_from_time(mintime)
            maxmjd = mjd_from_time(maxtime)
        except ValueError as e:
            raise e.with_traceback(e.__traceback__)
        newfilter = {
            'paramName': str(kw),
            'values': [{'min': minmjd, 'max': maxmjd}]}
        self.filters.append(newfilter)

    def set_output_columns(self, column_names):
        '''Set output columns as specified.

        column_names: str or list of str
            Comma-separated column names or list of column names
        '''
        self.columns = []
        self.append_output_columns(column_names)

    def set_output_columns_to_default(self):
        '''Set list of output columns to default value.'''
        inst_configs = {
            'Fgs': 'lamp',
            'GuideStar': 'gdstarid, gs_order',
            'Miri': 'filter, coronmsk, lamp',
            'Nircam': 'module, channel, pupil, filter, coronmsk',
            'Niriss': 'pupil, filter, lamp',
            'Nirspec': 'filter, grating, msastate, lamp',
            }
        self.columns = []
        self.append_output_columns('date_beg, obs_id, category, targname')
        if self.collection != 'GuideStar':
            self.append_output_columns('template, expripar, numdthpt')
        self.append_output_columns('apername')
        try:
            self.append_output_columns(inst_configs[self.collection])
        except KeyError:
            raise ValueError(
                f"unknown collection: {self.collection}\n"
                f"known collections: {' '.join(inst_configs)}")
        self.append_output_columns('exp_type, detector, subarray')
        self.append_output_columns('readpatt, nints, ngroups, duration')
        # self.append_output_columns('productLevel, filename')

    def set_output_columns_to_all(self):
        '''Specify that all columns ('*') should be output.'''
        self.columns = '*'

    def prepend_required_output_columns(self):
        '''Prepend required output columns and remove duplicates.

        Require fileSetName and detector columns to construct the CAOM obsid.
        Use list(dict.fromkeys()) to remove duplicates, while preserving order.
        '''
        if self.columns == '*':
            return
        required_columns = ['filename']
        columns = list(dict.fromkeys(
            required_columns + self.columns))
        self.set_output_columns(columns)

    def append_output_columns(self, column_names):
        '''Append one or more output column names to current list.

        column_names: str or list of str
            Comma-separated column names or list of column names
        '''
        try:
            names = column_names.split(',')
        except AttributeError:
            names = column_names
        for name in names:
            stripped = name.strip()
            if stripped not in self.columns:
                self.columns.append(stripped)

    def remove_output_columns(self, column_names):
        '''Remove one or more output column names from current list.

        column_names: str or list of str
            Comma-separated column names or list of column names
        '''
        try:
            names = column_names.split(',')
        except AttributeError:
            names = column_names
        for name in names:
            stripped = name.strip()
            if stripped in self.columns:
                self.columns.remove(stripped)

    def execute_query(self, convert_dates=True):
        '''Execute query by calling MAST service with specified parameters.'''
        if not self.filters:
            raise ValueError('add search filter(s) before executing query')
        self.prepend_required_output_columns()
        params = {
            'columns': ','.join(self.columns),
            'filters': self.filters}
        self._params = params
        self.result = Mast.service_request(self.service, params)
        if convert_dates:
            self.convert_dates()

    def convert_dates(self):
        '''Convert table values containing /Date()/ to datetime objects.'''
        if self.result is None:
            raise RuntimeError('execute query before parsing dates')
        if len(self.result) == 0:
            return
        for colname in self.result.colnames:
            values = list(self.result[colname].data.data)
            newval = [
                datetime.utcfromtimestamp(int(v[6:19]) / 1000)
                if isinstance(v, str) and len(v) == 21 and
                v[:6] == '/Date(' and v[-2:] == ')/' and v[6:19].isdigit()
                else v for v in values]
            if all([isinstance(v, datetime) for v in newval]):
                self.result[colname] = newval
            elif any([
                    n != v and not np_isnan(v)
                    for n, v in zip(newval, values)]):
                self.result[colname] = [v.isoformat()[:-3] for v in newval]

    def get_caom_obsid(self):
        '''Get CAOM obsid for archive files returned by JWST filtered query.

        References:
            https://mast.stsci.edu/api/v0/pyex.html#MastCaomFilteredPy
            https://mast.stsci.edu/api/v0/_services.html#MastCaomFiltered
            https://mast.stsci.edu/api/v0/_c_a_o_mfields.html
        '''
        if self.result is None:
            raise RuntimeError('execute query before getting CAOM obsid')
        dataset = [
            '_'.join(f.split('_')[:-1])
            for f in self.result['filename']]
        self._dataset = sorted(list(set(dataset)))
        service = 'Mast.Caom.Filtered'
        filters = [
            {'paramName': 'obs_collection', 'values': ['JWST']},
            {'paramName': 'instrument_name', 'values': [f'{self.collection}']},
            {'paramName': 'obs_id', 'values': self.dataset}]
        params = {'columns': 'obsid', 'filters': filters}
        caom_filtered_result = Mast.service_request(service, params)
        self._caom_obsid = ','.join(caom_filtered_result['obsid'].data)

    def get_caom_product_list(self):
        self.get_caom_obsid()
        self.caom_product_list = CaomProductList(self.caom_obsid)

    def browse(self, unique=True):
        '''Show unique query results in a browser window.'''
        if self.result is None:
            raise RuntimeError('execute query before trying to show result')
        if unique:
            unique_result = table_unique(self.result, keys='filename')
            unique_result.show_in_browser(jsviewer=True)
        else:
            self.result.show_in_browser(jsviewer=True)
        if self.caom_product_list:
            self.caom_product_list.browse(unique=unique)


class CaomProductList:
    '''Get list of CAOM products for one or more CAOM product group IDs.

    Examples:
        CaomProductList('71738577')
        CaomProductList('71738577, 71738600')
        CaomProductList(['71738577'])
        CaomProductList(['71738577', '71738600'])
        CaomProductList(71738577)
        CaomProductList([71738577])
        CaomProductList([71738577, 71738600])

    References:
        https://mast.stsci.edu/api/v0/pyex.html#MastCaomProductsPy
        https://mast.stsci.edu/api/v0/_services.html#MastCaomProducts
        https://mast.stsci.edu/api/v0/_productsfields.html
    '''
    def __init__(self, caom_obsid):
        self._obsid = self.parse_caom_obsid(caom_obsid)
        self.product_list = self.get_product_list()

    @property
    def obsid(self):
        '''Return CAOM obsid list as a comma-separated string.'''
        return self._obsid

    def parse_caom_obsid(self, caom_obsid):
        '''Parse input specification of one or more CAOM obsid.

        caom_obsid: str or int or iterable yielding those types
            specification of one or more CAOM obsid
        '''
        try:
            obsid = caom_obsid.split(',')
        except AttributeError:
            obsid = caom_obsid
        try:
            return ','.join([str(int(obsid))])
        except TypeError:
            pass
        try:
            return ','.join([str(int(i)) for i in obsid])
        except (TypeError, ValueError):
            raise TypeError(
                f'CAOM obsid must evaluate to integer(s): {caom_obsid}')

    def get_product_list(self):
        '''Get list of CAOM products for specified CAOM obsid.'''
        service = 'Mast.Caom.Products'
        params = {'obsid': self.obsid}
        return Mast.service_request(service, params)

    def browse(self, unique=True):
        '''Show product list in a browser window.'''
        columns = 'obsID,productFilename,size,calib_level,' \
            'productSubGroupDescription,productType,dataproduct_type'
        product_list = self.product_list[columns.split(',')]
        if unique:
            product_list = table_unique(product_list, keys='productFilename')
        product_list.show_in_browser(jsviewer=True)


def mjd_from_time(time):
    '''Return modified Julian date equivalent to input time specification.

    time: JD/MJD float, astropy Time, tz aware/naive datetime, or ISO 8601 str
          Treat float-compatible input as MJD or JD, de[ending on value.
          Assume astropy Time is UTC.
          Treat timezone-naive datetime object as UTC.
          Treat ISO 8601 string without timezone specification as UTC.
    '''
    # Input is JD or MJD as numeric or str.
    try:
        jd_or_mjd = float(time)
        if jd_or_mjd > 2400000.5:
            mjd = jd_or_mjd - 2400000.5
        else:
            mjd = jd_or_mjd
        return mjd
    except (TypeError, ValueError):
        pass
    # Input is astropy Time object
    if isinstance(time, Time):
        return time.mjd
    # Input is python datetime object.
    if isinstance(time, datetime):
        dt = time
    else:
        try:
            dt = datetime.fromisoformat(time)
        except (TypeError, ValueError):
            raise ValueError(f'unable to parse time specification: {time}')
    # If timezone was not specified, assume UTC.
    naive = dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None
    if naive:
        return Time(dt.replace(tzinfo=timezone.utc)).mjd
    else:
        return Time(dt).mjd


def get_mast_api_token(mast_api_token=None, prompt=False):
    '''Get MAST API token. Precedence: argument, environment, file, prompt.'''
    if not mast_api_token:
        mast_api_token = getenv('MAST_API_TOKEN')
    if not mast_api_token:
        path = Path.home() / '.mast_api_token'
        try:
            with open(path, 'r') as fp:
                lines = fp.read().splitlines()
                if len(lines) == 1:
                    mast_api_token = lines[0]
                else:
                    print('Ignoring ~/.mast_api_token, expected one line')
        except FileNotFoundError:
            pass
    if not mast_api_token and prompt:
        mast_api_token = getpass('Enter MAST API token: ')
    try:
        assert mast_api_token
        assert isinstance(mast_api_token, str)
        assert len(mast_api_token) == 32
        assert mast_api_token.isalnum()
        return mast_api_token
    except AssertionError:
        raise ValueError(
            f"MAST API token is not a string "
            f"with 32 alphanumeric characters: '{mast_api_token}'")


def get_jwst_file(name, auth=True):
    """Retrieve a JWST data file from MAST archive."""
    mast_url = "https://mast.stsci.edu/api/v0.1/Download/file"
    params = dict(uri=f"mast:JWST/product/{name}")
    if auth:
        headers = dict(Authorization=f"token {get_mast_api_token()}")
    else:
        headers = {}
    r = requests_get(mast_url, params=params, headers=headers, stream=True)
    r.raise_for_status()
    with open(name, "wb") as fobj:
        for chunk in r.iter_content(chunk_size=1024000):
            fobj.write(chunk)
