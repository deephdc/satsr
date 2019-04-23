"""
This file intends to gather code specific to Sentinel-2

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

from __future__ import division
from collections import defaultdict
import os
import re
import sys

import numpy as np
from osgeo import gdal

from satsr.utils import gdal_utils


upscaling_factor = {10: 1,
                    20: 2,
                    60: 6}

# Bands per resolution (bands should be load always in the same order)
res_to_bands = {10: ['B4', 'B3', 'B2', 'B8'],
                20: ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'],
                60: ['B1', 'B9']}

input_shapes = {str(res): (len(band_list), None, None) for res, band_list in res_to_bands.items()}

band_desc = {'B4': 'B4 (665 nm)',
             'B3': 'B3 (560 nm)',
             'B2': 'B2 (490 nm)',
             'B8': 'B8 (842 nm)',
             'B5': 'B5 (705 nm)',
             'B6': 'B6 (740 nm)',
             'B7': 'B7 (783 nm)',
             'B8A': 'B8A (865 nm)',
             'B11': 'B11 (1610 nm)',
             'B12': 'B12 (2190 nm)',
             'B1': 'B1 (443 nm)',
             'B9': 'B9 (945 nm)'}

# Borders and patch_sizes for inference
patch_sizes = {20: 128, 60: 192}
borders = {20: 8, 60: 12}


def read_bands(tile_path, roi_x_y=None, roi_lon_lat=None, max_res=60, select_UTM=''):
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

    # Process input tile name
    r = re.compile("^MTD_(.*?)xml$")
    matches = list(filter(r.match, os.listdir(tile_path)))
    if matches:
        xml_path = os.path.join(tile_path, matches[0])
    else:
        raise ValueError('No .xml file found.')

    # Open XML file and read band descriptions
    if not os.path.isfile(xml_path):
        raise ValueError('XML path not found.')
    raster = gdal.Open(xml_path)
    if raster is None:
        raise Exception('GDAL does not seem to support this file.')
    datasets = raster.GetSubDatasets()
    sets = {10: [], 20: [], 60: [], 'unknown': []}
    for dsname, dsdesc in datasets:
        for res in sets.keys():
            if '{}m resolution'.format(res) in dsdesc:
                sets[res] += [(dsname, dsdesc)]
                break
        else:
            sets['unknown'] += [(dsname, dsdesc)]

    # Find the pixel coordinates and UTM to process the image
    utm_idx = 0
    utm = select_UTM
    all_utms = defaultdict(int)
    xmin, ymin, xmax, ymax = 0, 0, 0, 0
    largest_area = -1

    for tmidx, (dsname, dsdesc) in enumerate(sets[10] + sets['unknown']):
        ds = gdal.Open(dsname)

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

        # Enlarge to the nearest 60 pixel boundary for the super-resolution
        tmxmin = int(tmxmin / 6) * 6
        tmxmax = int((tmxmax + 1) / 6) * 6 - 1
        tmymin = int(tmymin / 6) * 6
        tmymax = int((tmymax + 1) / 6) * 6 - 1

        # Case where we have several UTM in the data set => select the one with maximal coverage of the study zone
        area = (tmxmax - tmxmin + 1) * (tmymax - tmymin + 1)
        current_utm = dsdesc[dsdesc.find("UTM"):]
        if area > all_utms[current_utm]:
            all_utms[current_utm] = area
        if current_utm == select_UTM:
            xmin, ymin, xmax, ymax = tmxmin, tmymin, tmxmax, tmymax
            utm_idx = tmidx
            utm = current_utm
            break
        if area > largest_area:
            xmin, ymin, xmax, ymax = tmxmin, tmymin, tmxmax, tmymax
            largest_area = area
            utm_idx = tmidx
            utm = dsdesc[dsdesc.find("UTM"):]

    print("Selected UTM Zone:", utm)
    print("Selected pixel region: xmin=%d, ymin=%d, xmax=%d, ymax=%d:" % (xmin, ymin, xmax, ymax))
    print("Image size: width=%d x height=%d" % (xmax - xmin + 1, ymax - ymin + 1))

    if xmax < xmin or ymax < ymin:
        raise ValueError("Invalid region of interest / UTM Zone combination")

    # Select the bands in that UTM
    selected_dataset = {res: None for res in resolutions}
    for res in selected_dataset.keys():
        for (dsname, dsdesc) in enumerate(sets[res]):
            if utm in dsdesc:
                selected_dataset[res] = (dsname, dsdesc)
                break
        else:
            selected_dataset[res] = sets[res][utm_idx]

    # Getting the bands shortnames and descriptions
    ds_bands = {res: gdal.Open(selected_dataset[res][0]) for res in selected_dataset.keys()}
    validated_bands = {res: [] for res in resolutions}
    validated_indices = {res: [] for res in resolutions}
    validated_descriptions = {}

    for res in ds_bands.keys():
        sys.stdout.write("Selected {}m bands:".format(res))
        for b in range(0, ds_bands[res].RasterCount):
            desc = gdal_utils.get_short_description(ds_bands[res].GetRasterBand(b + 1).GetDescription())
            shortname = gdal_utils.get_short_name(desc)

            if shortname in selected_bands:
                sys.stdout.write(" " + shortname)
                selected_bands.remove(shortname)
                validated_bands[res] += [shortname]
                validated_indices[res] += [b]
                validated_descriptions[shortname] = desc
    sys.stdout.write("\n")

    # Check the tile has all the necessary bands for predictions
    for res in validated_bands.keys():
        assert validated_bands[res]==res_to_bands[res], 'Error loading bands at {}m resolution. \n' \
                                                        'Expected band list: {} \n' \
                                                        'Actual band list: {}'.format(res, res_to_bands[res], validated_bands[res])

    # Reading dataset bands into an array
    data_bands = {res: None for res in resolutions}
    upscaling_factor = {10: 1, 20: 2, 60: 6}

    for res in validated_bands.keys():
        print("Loading selected data from: {}m".format(selected_dataset[res][1]))
        uf = upscaling_factor[res]
        data_bands[res] = ds_bands[res].ReadAsArray(xoff=xmin // uf, yoff=ymin // uf,
                                                    xsize=(xmax - xmin + 1) // uf, ysize=(ymax - ymin + 1) // uf,
                                                    buf_xsize=(xmax - xmin + 1) // uf, buf_ysize=(ymax - ymin + 1) // uf)
        data_bands[res] = np.moveaxis(data_bands[res], source=0, destination=-1)  # move to channels last
        data_bands[res] = data_bands[res][:, :, validated_indices[res]]

    coord = {'xmin': xmin,
             'ymin': ymin,
             'geotransform': ds_bands[10].GetGeoTransform(),
             'geoprojection': ds_bands[10].GetProjection()}

    return data_bands, coord
