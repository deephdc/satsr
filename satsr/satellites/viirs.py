"""
This file intends to gather code specific to VIIRS

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


upscaling_factor = {375: 1,
                    750: 2}

# Bands per resolution (bands should be load always in the same order)
res_to_bands = {375: ['I1', 'I2', 'I3'],
                750: ['M1', 'M2', 'M3', 'M4', 'M5', 'M7', 'M8', 'M10', 'M11']}

input_shapes = {str(res): (len(band_list), None, None) for res, band_list in res_to_bands.items()}

band_desc = {'I1': '375m Surface Reflectance Band I1 (16-bit integer)',
             'I2': '375m Surface Reflectance Band I2 (16-bit integer)',
             'I3': '375m Surface Reflectance Band I3 (16-bit integer)',
             'M1': '750m Surface Reflectance Band M1 (16-bit integer)',
             'M2': '750m Surface Reflectance Band M2 (16-bit integer)',
             'M3': '750m Surface Reflectance Band M3 (16-bit integer)',
             'M4': '750m Surface Reflectance Band M4 (16-bit integer)',
             'M5': '750m Surface Reflectance Band M5 (16-bit integer)',
             'M7': '750m Surface Reflectance Band M7 (16-bit integer)',
             'M8': '750m Surface Reflectance Band M8 (16-bit integer)',
             'M10': '750m Surface Reflectance Band M10 (16-bit integer)',
             'M11': '750m Surface Reflectance Band M11 (16-bit integer)'}

# Borders and patch_sizes for inference
patch_sizes = {750: 128}
borders = {750: 8}

# Define pixel values
max_val = 16000
min_val = -100
fill_val = -28672


def read_bands(tile_path, roi_x_y=None, roi_lon_lat=None, max_res=750):

    print('Loading {}'.format(tile_path))

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

    # Read metadata
    hdf_file = gdal.Open(tile_path)
    metadata = hdf_file.GetMetadata()

    # Read dataset bands in GDAL
    sub_datasets = hdf_file.GetSubDatasets()
    sub_datasets_desc = [sd[1].split('] ')[1] for sd in sub_datasets]
    ds_bands = {res: None for res in resolutions}
    for res in resolutions:
        # print("Loading selected data from GDAL: {}m".format(res))
        ds_bands[res] = []
        for band_name in res_to_bands[res]:
            i = sub_datasets_desc.index(band_desc[band_name])
            tmp_ds = gdal.Open(sub_datasets[i][0])
            ds_bands[res].append(tmp_ds)

    # Find the pixel coordinates
    ds = ds_bands[375][0]

    if roi_lon_lat:  # transform lonlat coordinates to pixels
        roi_x1, roi_y1 = gdal_utils.lonlat_to_xy(roi_lon1, roi_lat1, ds)
        roi_x2, roi_y2 = gdal_utils.lonlat_to_xy(roi_lon2, roi_lat2, ds)

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

    ####################
    # FIXME: Try to find what is the projection and the geotransform (degrees not meters?) for VIIRS
    #  (this one has been hardcoded from Sentinel 2)

    # https://lists.osgeo.org/pipermail/gdal-dev/2013-January/035291.html
    # https://www.youtube.com/watch?v=jDgn1ktZpBU&feature=youtu.be&t=33m42s
    # https://gis.stackexchange.com/questions/204282/gdal-for-reprojection-of-vscmo-viirs-data
    # https://gis.stackexchange.com/questions/81361/how-to-reproject-modis-swath-data-to-wgs84
    # https://gis.stackexchange.com/questions/286089/snpp-viirs-swath-data-reprojection-to-wgs84

    # Get coordinates
    coord = {'xmin': xmin,
             'ymin': ymin,
             'geotransform': (0.0, 375.0, 0.0, 0.0, 0.0, -375.0),
             'geoprojection': 'PROJCS["WGS 84 / UTM zone 30N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-3],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32630"]]'}

    # # Get coordinates
    # coord = {'xmin': xmin,
    #          'ymin': ymin,
    #          'geotransform': ds_bands[375][0].GetGeoTransform(),
    #          'geoprojection': ds_bands[375][0].GetProjection()}
    ####################

    return data_bands, coord


def save_as(input_path, format='GTiff'):
    """
    Save original VIIRS hdf file to another format so that it can be visualized with other programs like QGIS.
    We save a diffent tiff for each resolution to allow for the different geotransforms
    """
    data_bands, coord = read_bands(tile_path=input_path)

    for res, bands in res_to_bands.items():

        # Create the lists of output variables to save
        output_bands, output_desc, output_shortnames = [], [], []
        for bi, bn in enumerate(bands):
            output_bands.append(data_bands[res][:, :, bi])
            output_desc.append(band_desc[bn])
            output_shortnames.append(bn)

        # Adapt geotransform to resolution
        geot = list(coord['geotransform'])
        geot[1] = res
        geot[5] = -res

        gdal_utils.save_gdal(output_path=input_path[:-4] + '_{}m.tif'.format(res),
                             bands=output_bands,
                             descriptions=output_desc,
                             geotransform=tuple(geot),
                             geoprojection=coord['geoprojection'],
                             file_format=format)


if __name__ == '__main__':
    save_as(input_path = '/media/ignacio/Datos/datasets/satelites/viirs_tiles/VNP09.A2019021.2142.001.2019035204543.hdf')
