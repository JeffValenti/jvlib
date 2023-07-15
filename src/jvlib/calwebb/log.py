class CalwebbSpec2Log:
    '''Provide content in a calwebb_spec2 log file.'''
    def __init__(self, path):
        self.path = path
        self.sub = self._define_substrings()
        self._parse_log_file()

    def __str__(self):
        try:
            return f'{self.slit}: ' \
                f'x=({self.xstart:g}, {self.xstop:g}); ' \
                f'y=({self.ystart:g}, {self.ystop:g}); ' \
                f'dyspec={self.dy_spectrum:g}'
        except AttributeError:
            return 'No slit information'

    def _define_substrings(self):
        '''Return substrings that trigger parsing of a line in log file.'''
        return {
            'slit': 'source type in slit',
            'current_slit': 'INFO - Working on slit',
            'dy_spectrum': 'INFO - Applying position offset of',
            'extraction_limits': 'INFO - Using extraction limits:',
            }

    def _parse_log_file(self):
        '''Parse content in the log file.'''
        with open(self.path) as textio:
            for line in textio:
                if 'Spec2Pipeline' in line:
                    for subid, sub in self.sub.items():
                        if sub in line:
                            self._parse_log_line(subid, sub, line)

    def _parse_log_line(self, subid, sub, line):
        '''Parse content in the line from a log file.'''
        pre, post = [s.strip() for s in line.split(sub)]
        if subid == 'slit':
            self.extent = pre.split()[-1]
            self.slit = post
        elif subid == 'current_slit':
            self.current_slit = post
        elif subid == 'dy_spectrum':
            if self.current_slit == self.slit:
                self.dy_spectrum = float(post.split()[0])
        elif subid == 'extraction_limits':
            if self.current_slit == self.slit:
                for keyval in post.split(','):
                    key, value = keyval.split('=')
                    setattr(self, key.strip(), float(value))
