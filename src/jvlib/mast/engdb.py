from csv import reader as csv_reader
from datetime import datetime
from json import loads as json_loads
from re import compile as re_compile, ASCII, IGNORECASE
from requests import get as requests_get
from statistics import mode

from .api import get_mast_api_token


class UnauthorizedError(Exception):
    '''Handle MAST authorization exception.'''

    def __init__(self, message):
        super(UnauthorizedError, self).__init__(message)
        self.message = message


class EngdbMnemonicMetadata(list):
    '''Fetch mnemonic metadata for JWST engineering database.

    Example:
        >>> from jvlib.mast.engdb import EngdbMnemonicMetadata
        >>> meta = EngdbMnemonicMetadata()
        >>> print(meta.subsystems)
        ['ACS', 'DRV', ...]
        >>> metasub = meta.filter_by_subsystem(['ACS', 'ISIM', 'NIRSPEC'])
        >>> print(metasub.subsystems)
        ['ACS', 'ISIM', 'NIRSPEC']
        >>> print(metasub.mnemonics)
        ['IDAQ_EXP_STATUS1', 'IDAQ_EXP_STATUS2', ...]
        >>> metamnem = metasub.filter_by_mnemonic('.*TEMP.*')
        >>> print(metamnem.mnemonics)
        ['IGDP_NRSD_ALG_A1_TEMP', 'IGDP_NRSD_ALG_A2_TEMP', ...]
        >>> for item in metamnem[:2]:
        >>>     print(item)
        {'subsystem': 'NIRSPEC', 'tlmMnemonic': 'IGDP_NRSD_ALG_A1_TEMP',
        'tlmIdentifier': 424001, 'description': 'NIRSpec converted ASIC #1
        Temperature (K) (derived ground data point)', 'sqlDataType': 'real',
        'unit': 'K'}
        {'subsystem': 'NIRSPEC', 'tlmMnemonic': 'IGDP_NRSD_ALG_A2_TEMP',
        'tlmIdentifier': 424002, 'description': 'NIRSpec converted ASIC #2
        Temperature (K) (derived ground data point)', 'sqlDataType': 'real',
        'unit': 'K'}
    '''

    def __init__(self, items=None):
        self.url = 'https://mast.stsci.edu/viz/api/v0.1/info/mnemonics'
        if items:
            self.extend(items)
        else:
            json = requests_get(self.url).text
            self.extend(json_loads(json)['data'])
            if self[-1]['tlmMnemonic'] == 'ZZZZZZ':
                del self[-1]

    @property
    def mnemonics(self):
        '''Return list of all mnemonics.'''
        return [item['tlmMnemonic'] for item in self]

    @property
    def subsystems(self):
        '''Return list of all subsystems.'''
        return sorted(set([item['subsystem'] for item in self]))

    @property
    def sqldatatypes(self):
        '''Return list of all SQL data types.'''
        return sorted(set([item['sqlDataType'] for item in self]))

    def filter_by_subsystem(self, keeplist):
        '''Return new instance containing only the specified subsystems.'''
        items = [item for item in self if item['subsystem'] in keeplist]
        return EngdbMnemonicMetadata(items)

    def filter_by_mnemonic(self, regex):
        '''Return new instance containing mnemonics that match expression.'''
        crex = re_compile(regex, ASCII | IGNORECASE)
        items = [item for item in self if crex.match(item['tlmMnemonic'])]
        return EngdbMnemonicMetadata(items)


class EngdbTimeSeries:
    '''Handle time series data from the JWST engineering database.'''

    def __init__(self, mnemonic, lines):
        self.mnemonic = mnemonic
        self.time, self.time_mjd, self.value = self.parse(lines)
        self._cadence = None
        self._largest_gap = None

    def __len__(self):
        '''Return number of points in time series.'''
        return len(self.time)

    @property
    def timestep_seconds(self):
        '''Return time step between successive times in seconds.'''
        try:
            return [(b - a).total_seconds() for a, b in zip(
                self.time[:-1], self.time[1:])]
        except IndexError:
            return None

    @property
    def cadence_seconds(self):
        '''Return most common time step in seconds.'''
        timestep_seconds = self.timestep_seconds
        if timestep_seconds:
            self._cadence = mode(timestep_seconds)
            self._largest_gap = max(timestep_seconds)
        return self._cadence

    @property
    def largest_gap_seconds(self):
        '''Return most common time step in seconds.'''
        timestep_seconds = self.timestep_seconds
        if timestep_seconds:
            self._cadence = mode(timestep_seconds)
            self._largest_gap = max(timestep_seconds)
        return self._largest_gap

    def parse(self, lines):
        '''Parse lines of text returned by MAST EDB interface.'''
        # Define python analog of SQL data types.
        # https://docs.microsoft.com/en-us/sql/machine-learning/python
        #     /python-libraries-and-data-types?view=sql-server-ver15
        cast = {'bigint': float,
                'binary': bytes,
                'bit': bool,
                'char': str,
                'date': datetime,
                'datetime': datetime,
                'float': float,
                'nchar': str,
                'nvarchar': str,
                'nvarchar(max)': str,
                'real': float,
                'smalldatetime': datetime,
                'smallint': int,
                'tinyint': int,
                'uniqueidentifier': str,
                'varbinary': bytes,
                'varbinary(max)': bytes,
                'varchar': str,
                'varchar(n)': str,
                'varchar(max)': str}
        time = []
        time_mjd = []
        value = []
        for field in csv_reader(lines, delimiter=',', quotechar='"'):
            if field[0] == 'theTime':
                continue
            sqltype = field[3]
            time.append(datetime.fromisoformat(field[0]))
            time_mjd.append(float(field[1]))
            value.append(cast[sqltype](field[2]))
        return time, time_mjd, value


class EngineeringDatabase:
    '''Access JWST engineering database hosted by MAST at STScI.'''

    def __init__(self, mast_api_token=None):
        self.token = get_mast_api_token(mast_api_token)
        self.baseurl = 'https://mast.stsci.edu/jwst/api/v0.1/' \
            'Download/file?uri=mast:jwstedb'

    def format_date(self, date):
        '''Convert datetime object or ISO 8501 string to EDB date format.'''
        if type(date) is str:
            dtobj = datetime.fromisoformat(date)
        elif type(date) is datetime:
            dtobj = date
        else:
            raise ValueError('date must be ISO 8501 string or datetime obj')
        return dtobj.strftime('%Y%m%dT%H%M%S')

    def timeseries(self, mnemonic, start, end):
        '''Get engineering data for specified mnemonic and time interval.'''
        startdate = self.format_date(start)
        enddate = self.format_date(end)
        filename = f'{mnemonic}-{startdate}-{enddate}.csv'
        url = f'{self.baseurl}/{filename}'
        headers = {'Authorization': f'token {self.token}'}
        with requests_get(url, headers=headers, stream=True) as response:
            if response.status_code == 401:
                raise UnauthorizedError('check that MAST API token is valid')
            response.raise_for_status()
            return EngdbTimeSeries(mnemonic, response.text.splitlines())


class EventMessages:
    '''Fetch and interpret OSS event messages for specified time interval.'''

    def __init__(self, start, end, engdb=None):
        '''Instantiate an EventMessages object.

        :param start: earliest UTC date and time
        :type start: datetime, str parsable by datetime.fromisoformat()
        :param end: end of time interval to use when fetching messages
        :type end: datetime, str parsable by datetime.fromisoformat()
        :param engdb: existing interface to engineering database
        :type engdb: jwstuser.engdb.EngineeringDatabase

        :Example:

        >>> from datetime import datetime
        >>> from jwstuser.engdb import EventMessages
        >>> utcnow = datetime.utcnow()
        >>> em = EventMessages('2022-05-01 23:59:59', utcnow)
        >>> print(f'{len(em)} event messages')
        10555
        >>> print(f'{em.time[0]} -- {em.value[0]}')
        2022-05-01 23:41:58.623000 -- SCS ID 511 reached specified step 255
        '''

        if not engdb:
            engdb = EngineeringDatabase()
        self._timeseries = engdb.timeseries('ICTM_EVENT_MSG', start, end)

    def __len__(self):
        '''Return number of event messages.'''
        return len(self._timeseries)

    @property
    def time(self):
        '''Return datetime of each event message.'''
        return self._timeseries.time

    @property
    def mjd(self):
        '''Return modified Julian date for each event message.'''
        return self._timeseries.time_mjd

    @property
    def value(self):
        '''Return list of event messages.'''
        return self._timeseries.value
