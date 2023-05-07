from astropy.io.fits import open as fits_open


def calwebb_version(fitspath):
    '''Get version information for fits file produced by calwebb pipeline.'''
    descriptions = dict(
        date='file creation date',
        cal_ver='calibration software version',
        crds_ctx='calibration reference files version',
        prd_ver='project reference data version',
        sdp_ver='pre-calibration software version',
        crds_ver='reference file selection software version',
        oss_ver='observing scripts version')
    values = {}
    with fits_open(fitspath) as hdulist:
        header = hdulist['primary'].header
        for key in descriptions:
            try:
                if key == 'crds_ctx':
                    values[key] = header[key][5:9]
                elif key == 'date':
                    values[key] = header[key][:10]
                else:
                    values[key] = header[key]
            except KeyError:
                values[key] = '(missing)'
    text = f'We analyzed data files produced by version ' \
        f'cal_ver={values["cal_ver"]} ' \
        f'of the JWST Calwebb calibration software package ' \
        f'<href="https://github.com/spacetelescope/jwst">, ' \
        f'using calibration reference files from context ' \
        f'crds_ctx={values["crds_ctx"]}.'
    return values, descriptions, text
