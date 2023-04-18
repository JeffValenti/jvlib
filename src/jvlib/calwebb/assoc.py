from json import load as json_load


class JwstAssociationFile:
    '''Represent contents of a JWST associations file (_asn.json).'''
    def __init__(self, path):
        self.filename = path.name
        with open(path) as fp:
            self.data = json_load(fp)
        for key in ['asn_type', 'code_version', 'asn_id', 'target']:
            setattr(self, key, self.data[key])
        self.pipeline = f'{self.asn_type.title()}Pipeline'

    @property
    def expnames(self):
        '''Members of this association.'''
        expnames = []
        for product in self.data['products']:
            for member in product['members']:
                expnames.append(member['expname'])
        return sorted(set(expnames))
