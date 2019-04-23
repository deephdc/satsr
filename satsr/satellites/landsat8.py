"""
This file intends to gather code specific to LandSat 8

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

from __future__ import division
import os
import re
from functools import reduce
import operator
import json

import numpy as np
from osgeo import gdal

from satsr.utils import gdal_utils


upscaling_factor = {15: 1,
                    30: 2}

# Bands per resolution (bands should be load always in the same order)
res_to_bands = {15: ['B8'],
                30: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B9', 'B10', 'B11']}

input_shapes = {str(res): (len(band_list), None, None) for res, band_list in res_to_bands.items()}

band_desc = {'B1': 'B1 Ultra Blue (coastal/aerosol) [435nm-451nm]',
             'B2': 'B2 Blue [452nm-512nm]',
             'B3': 'B3 Green [533nm-590nm]',
             'B4': 'B4 Red [636nm-673nm]',
             'B5': 'B5 Near Infrared (NIR)	[851nm-879nm]',
             'B6': 'B6 Shortwave Infrared (SWIR) 1	[1566nm-1651nm]',
             'B7': 'B7 Shortwave Infrared (SWIR) 2	[2107nm-2294nm]',
             'B8': 'B8 Panchromatic [503nm-676nm]',
             'B9': 'B9 Cirrus [1363nm-1384nm]',
             'B10': 'B10 Thermal Infrared (TIRS) 1 [1060nm-1119nm]',
             'B11': 'B11 Thermal Infrared (TIRS) 2 [1150nm-1251nm]'}

# Borders and patch_sizes for inference
patch_sizes = {30: 128}
borders = {30: 8}


def read_bands(tile_path, roi_x_y=None, roi_lon_lat=None, max_res=30, select_UTM=''):
    """

    Parameters
    ----------
    tile_path : str
    roi_x_y : list of ints
    roi_lon_lat : list of floats
    max_res : int
    select_UTM : str

    Returns
    -------
    A dict where the keys are int of the resolutions and values are numpy arrays (H, W, N)
    """

    print('Print performing inference with {}'.format(tile_path))

    # Select bands
    resolutions = [res for res in res_to_bands.keys() if res <= max_res]
    selected_bands = []
    for res in resolutions:
        selected_bands.extend(res_to_bands[res])

    # Select ROIs
    if roi_lon_lat:
        roi_lon1, roi_lat1, roi_lon2, roi_lat2 = roi_lon_lat
    if roi_x_y:
        roi_x1, roi_y1, roi_x2, roi_y2 = roi_x_y

    # Read config
    r = re.compile("^(.*?)MTL.txt$")
    matches = list(filter(r.match, os.listdir(tile_path)))
    if matches:
        mtl_path = os.path.join(tile_path, matches[0])
    else:
        raise ValueError('No MTL config file found.')
    config = read_config_file(mtl_path)
    config = config['L1_METADATA_FILE']

    # Read dataset bands in GDAL
    ds_bands = {res: None for res in resolutions}
    for res in resolutions:
        print("Loading selected data from GDAL: {}m".format(res))
        ds_bands[res] = []
        for band_name in res_to_bands[res]:
            file_path = os.path.join(tile_path, '{}_{}.TIF'.format(config['METADATA_FILE_INFO']['LANDSAT_PRODUCT_ID'], band_name))
            tmp_ds = gdal.Open(file_path)
            ds_bands[res].append(tmp_ds)

    # Find the pixel coordinates
    ds = ds_bands[15][0]

    if roi_lon_lat:  # transform lonlat coordinates to pixels
        roi_x1, roi_y1 = gdal_utils.lonlat_to_xy(roi_lon1, roi_lat1)
        roi_x2, roi_y2 = gdal_utils.lonlat_to_xy(roi_lon2, roi_lat2)

    if roi_x_y or roi_lon_lat:
        tmxmin = max(min(roi_x1, roi_x2, ds.RasterXSize - 1), 0)
        tmxmax = min(max(roi_x1, roi_x2, 0), ds.RasterXSize - 1)
        tmymin = max(min(roi_y1, roi_y2, ds.RasterYSize - 1), 0)
        tmymax = min(max(roi_y1, roi_y2, 0), ds.RasterYSize - 1)

    else:  # if no user input, use all the image
        tmxmin = 0
        tmxmax = ds.RasterXSize - 1
        tmymin = 0
        tmymax = ds.RasterYSize - 1

    # Enlarge to the nearest 30 pixel boundary for the super-resolution
    mult = upscaling_factor[max_res]
    xmin = int(tmxmin / mult) * mult
    xmax = int((tmxmax + 1) / mult) * mult - 1
    ymin = int(tmymin / mult) * mult
    ymax = int((tmymax + 1) / mult) * mult - 1

    print("Selected pixel region: xmin=%d, ymin=%d, xmax=%d, ymax=%d:" % (xmin, ymin, xmax, ymax))
    print("Image size: width=%d x height=%d" % (xmax - xmin + 1, ymax - ymin + 1))

    # Reading dataset bands into an array
    data_bands = {res: None for res in resolutions}
    for res in resolutions:
        print("Loading arrays from: {}m".format(res))
        data_bands[res] = []
        uf = upscaling_factor[res]
        for tmp_ds in ds_bands[res]:
            tmp_arr = tmp_ds.ReadAsArray(xoff=xmin // uf, yoff=ymin // uf,
                                         xsize=(xmax - xmin + 1) // uf, ysize=(ymax - ymin + 1) // uf,
                                         buf_xsize=(xmax - xmin + 1) // uf, buf_ysize=(ymax - ymin + 1) // uf)
            data_bands[res].append(tmp_arr)
        data_bands[res] = np.array(data_bands[res])
        data_bands[res] = np.moveaxis(data_bands[res], 0, -1)  # move to channels last

    # Get coordinates
    coord = {'xmin': xmin,
             'ymin': ymin,
             'geotransform': ds_bands[15][0].GetGeoTransform(),
             'geoprojection': ds_bands[15][0].GetProjection()}

    return data_bands, coord


def get_by_path(root, items):
    """
    Access a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    return reduce(operator.getitem, items, root)


def set_by_path(root, items, value):
    """
    Set a value in a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    get_by_path(root, items[:-1])[items[-1]] = value


def read_config_file(filepath):
    """
    Read a LandSat MTL config file to a Python dict
    """
    config = {}
    f = open(filepath)
    group_path = []
    for line in f:
        line = line.lstrip(' ').rstrip()  # remove leading whitespaces and trainling newlines

        if line.startswith('GROUP'):
            group_name = line.split(' = ')[1]
            group_path.append(group_name)
            set_by_path(root=config, items=group_path, value={})

        elif line.startswith('END_GROUP'):
            del group_path[-1]

        elif line.startswith('END'):
            continue

        else:
            key, value = line.split(' = ')
            try:
                set_by_path(root=config, items=group_path + [key], value=json.loads(value))
            except Exception:
                set_by_path(root=config, items=group_path + [key], value=value)
    f.close()
    return config


if __name__ == '__main__':
    read_bands(tile_path='/media/ignacio/Datos/datasets/satelites/LandSat_tiles/LC80200362019035LGN00',
               roi_x_y=[5000,5000,5500,5500])
