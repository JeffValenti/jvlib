from json import load as json_load


class JwstAssociationInfo:
    '''Information from a JWST association file (_asn.json).'''
    def __init__(self, path):
        self.filename = path.name
        with open(path) as fp:
            self.data = json_load(fp)
        for key in ['asn_type', 'code_version', 'asn_id', 'target']:
            setattr(self, key, self.data[key])
        self.pipeline = f'{self.asn_type.title()}Pipeline'

    @property
    def members(self):
        '''Members of this association.'''
        members = []
        for product in self.data['products']:
            for member in product['members']:
                members.append(member['expname'])
        return sorted(set(members))
