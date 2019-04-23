"""
This is a placeholder for the functions and variables of the satellite you selected.
"""

from satsr import config


CONF = config.get_conf_dict()
selected_sat = CONF['general']['satellite']


def load_modules():
    print('Loading satellite functions for {}...'.format(selected_sat))

    global sat_fns
    global sat_download

    if selected_sat == 'sentinel2':
        import satsr.satellites.sentinel2 as sat_fns
        import satsr.satellites.sentinel_download as sat_download

    elif selected_sat == 'landsat8':
        import satsr.satellites.landsat8 as sat_fns
        import satsr.satellites.landsat_download as sat_download

    else:
        raise Exception('Invalid satellite name')


load_modules()


def check_reloading():
    # Reload the modules if the satellite name as changed after main_sat.py was imported
    global selected_sat
    CONF = config.conf_dict

    if CONF['general']['satellite'] != selected_sat:
        selected_sat = CONF['general']['satellite']
        load_modules()


# List of objects used by the package
# ===================================

# Dictionaries
# ------------

def upscaling_factor():
    """
    User defined
    """
    check_reloading()
    return getattr(sat_fns, 'upscaling_factor')


def res_to_bands():
    """
    User defined
    """
    check_reloading()
    return getattr(sat_fns, 'res_to_bands')


def band_desc():
    """
    Optionally user defined.
    """
    check_reloading()
    try:
        return getattr(sat_fns, 'band_desc')
    except AttributeError:
        return {k: k for k in res_to_bands().keys()}


def patch_sizes():
    """
    Optionally user defined.
    """
    check_reloading()
    try:
        return getattr(sat_fns, 'patch_sizes')
    except AttributeError:
        return {k: 128 for k in res_to_bands().keys()}


def borders():
    """
    Optionally user defined.
    """
    check_reloading()
    try:
        return getattr(sat_fns, 'borders')
    except AttributeError:
        return {k: 8 for k in res_to_bands().keys()}


def input_shapes():
    """
    Shapes to feed the network
    """
    check_reloading()
    return {str(res): (len(band_list), None, None) for res, band_list in res_to_bands().items()}


# Dictionaries
# ------------

def read_bands():
    """
    User defined
    """
    check_reloading()
    return getattr(sat_fns, 'read_bands')


# Classes
# -------

def Satellite():
    """
    User defined
    """
    check_reloading()
    return getattr(sat_download, 'Satellite')

