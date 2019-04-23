"""
Utils to interact with GDAL.

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import re
import os

from osgeo import gdal, osr


def print_gdal_file_formats():
    """
    List all output file formats
    """
    print("Supported format by GDAL")
    dcount = gdal.GetDriverCount()
    for didx in range(dcount):
        driver = gdal.GetDriver(didx)
        if driver:
            metadata = driver.GetMetadata()
        if (gdal.DCAP_CREATE in (driver and metadata) and metadata[gdal.DCAP_CREATE] == 'YES' and
                gdal.DCAP_RASTER in metadata and metadata[gdal.DCAP_RASTER] == 'YES'):
            name = driver.GetDescription()
            if "DMD_LONGNAME" in metadata:
                name += ": " + metadata["DMD_LONGNAME"]
            else:
                name = driver.GetDescription()
            if "DMD_EXTENSIONS" in metadata: name += " (" + metadata["DMD_EXTENSIONS"] + ")"
            print(name)


def lonlat_to_xy(lon, lat, ds):
    """

    Parameters
    ----------
    lon: str
    lat: str
    ds: GDAL Dataset

    Returns
    -------
    A pair of coordinates in meters/pixels ????
    """

    xoff, a, b, yoff, d, e = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())
    srsLatLon = osr.SpatialReference()
    srsLatLon.SetWellKnownGeogCS("WGS84")
    ct = osr.CoordinateTransformation(srsLatLon, srs)

    (xp, yp, h) = ct.TransformPoint(lon, lat, 0.)
    xp -= xoff
    yp -= yoff
    # matrix inversion
    det_inv = 1. / (a * e - d * b)
    x = (e * xp - b * yp) * det_inv
    y = (-d * xp + a * yp) * det_inv
    return int(x), int(y)


def get_short_description(description, output_file_format='GTiff'):
    """
    Get a short band description from full description
    """
    m = re.match("(.*?), central wavelength (\d+) nm", description)
    if m:
        return m.group(1) + " (" + m.group(2) + " nm)"
    # Some HDR restrictions... ENVI band names should not include commas
    if output_file_format == 'ENVI' and ',' in description:
        pos = description.find(',')
        return description[:pos] + description[(pos + 1):]
    return description


def get_short_name(description):
    """
    Get short band name from full description
    """
    if ',' in description:
        return description[:description.find(',')]
    if ' ' in description:
        return description[:description.find(' ')]
    return description[:3]


def check_gdal_format(file_format):
    """
    Check if a file format can be written with GDAL

    Parameters
    ----------
    file_format : str
    """
    driver = gdal.GetDriverByName(file_format)
    if driver:
        metadata = driver.GetMetadata()
        if gdal.DCAP_CREATE in metadata and metadata[gdal.DCAP_CREATE] == 'YES':
            return True
    else:
        return False


def save_gdal(output_path, bands, descriptions, geotransform, geoprojection, file_format='GTiff'):
    """
    Function to save bands into a gdal format

    Parameters
    ----------
    output_path : str
        Output path of the file
    bands : list of 2D np.arrays
        Bands to save. List of len(C)
    descriptions : list of strs
        Descriptions of the bands. List of len(C)
    geotransform
    geoprojection
    file_format
    """
    # Create output path if needed
    path_dir = os.path.dirname(output_path)
    if not os.path.exists(path_dir):
        os.makedirs(path_dir)

    # Create GDAL dataset
    driver = gdal.GetDriverByName(file_format)
    result_dataset = driver.Create(output_path,
                                   bands[0].shape[1], bands[0].shape[0], len(bands),
                                   gdal.GDT_Float64)
    result_dataset.SetGeoTransform(geotransform)
    result_dataset.SetProjection(geoprojection)

    # Save bands and descriptions
    for i, desc in enumerate(descriptions):
        print('Saving {}'.format(desc))
        result_dataset.GetRasterBand(i+1).SetDescription(desc)
        result_dataset.GetRasterBand(i+1).WriteArray(bands[i])
