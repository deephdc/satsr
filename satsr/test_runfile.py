"""
This is a file to make inference on a new satellite tile.

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import os

import numpy as np
from keras import backend as K


from satsr import paths, main_sat, config
from satsr.utils.model_utils import super_resolve, load_model
from satsr.utils import gdal_utils


# Load the models for different resolutions in a dict
models, models_sat = None, None


def load_models():
    global models, models_sat
    K.clear_session()
    models_sat = config.conf_dict['general']['satellite']
    models = {}
    default_shapes = main_sat.input_shapes()
    min_res = min(default_shapes.keys())
    for res in default_shapes.keys():
        if res == min_res:  # no need to build a model for the minimum resolution
            continue
        input_shape = {tmp_res: default_shapes[tmp_res] for tmp_res in default_shapes.keys() if int(tmp_res) <= int(res)}
        models[int(res)] = load_model(input_shape=input_shape, modelname='{}_model_{}m'.format(models_sat, res))


def test(tile_path, max_res, output_path=None, roi_x_y=None, roi_lon_lat=None, copy_original_bands=True,
         output_file_format='GTiff'):

    # Load models if needed
    if (models is None) or (models_sat != config.conf_dict['general']['satellite']):
        load_models()

    # Process output file name and format
    if output_path is None:
        print("Error: you must provide the name of an output file. I will set it identical to the input...")
        output_name = os.path.split(tile_path)[1] + '.tif'
        output_path = os.path.join(paths.get_test_dir(), 'outputs', output_name)

    if output_file_format == 'ENVI' and output_path[-4:].lower() == '.hdr':
        output_path = output_path[:-4] + '.bin'  # ENVI file name should be the .bin, not the .hdr

    if not gdal_utils.check_gdal_format(output_file_format):
        print("Gdal doesn't support creating %s files" % output_file_format)
        gdal_utils.print_gdal_file_formats()
        print("\n")
        print("Writing to npz as a fallback")
        output_file_format = "npz"

    # Load bands
    data_bands, coord = main_sat.read_bands()(tile_path=tile_path, max_res=max_res, roi_x_y=roi_x_y,
                                              roi_lon_lat=roi_lon_lat)

    # Check image
    min_res = min(data_bands.keys())
    if not np.any(data_bands[min_res]):
        raise Exception('Empty image')

    # Perform super resolution
    sr_bands = {res: None for res in data_bands.keys() if res != min_res}
    for res in sr_bands.keys():
        print('Super resolving {}m ...'.format(res))
        tmp_bands = {tmp_res: bands for tmp_res, bands in data_bands.items() if tmp_res <= res}
        min_side = min(tmp_bands[res].shape[:2])
        tmp_patchsize = min(main_sat.patch_sizes()[res], min_side)
        sr_bands[res] = super_resolve(data_bands=tmp_bands, model=models[res],
                                      patch_size=tmp_patchsize, border=main_sat.borders()[res])

    # Keep only the values that where different from zero in the original array (filter with mask)
    mask = (data_bands[min_res][:, :, 0] != 0)
    sr_bands = {res: bands * mask[:, :, None] for res, bands in sr_bands.items()}

    # Join the non-empty super resolved bands
    sr, validated_sr_bands = [], []
    for k, v in sr_bands.items():
        sr.append(v)
        validated_sr_bands += main_sat.res_to_bands()[k]
    sr = np.concatenate(sr, axis=2)

    # Create the lists of output variables to save
    output_bands, output_desc, output_shortnames = [], [], []

    if copy_original_bands:
        for bi, bn in enumerate(main_sat.res_to_bands()[min_res]):
            output_bands.append(data_bands[min_res][:, :, bi])
            output_desc.append(main_sat.band_desc()[bn])
            output_shortnames.append(bn)

    for bi, bn in enumerate(validated_sr_bands):
        output_bands.append(sr[:, :, bi])
        output_desc.append("SR" + main_sat.band_desc()[bn])
        output_shortnames.append("SR" + bn)

    # Translate the image upper left corner. We multiply x10 to transform from pixel position in the 10m_band to meters.
    geot = list(coord['geotransform'])
    geot[0] += coord['xmin'] * min_res
    geot[3] -= coord['ymin'] * min_res

    # Save output
    if output_file_format == "npz":
        output_dict = dict(zip(output_shortnames,
                               output_bands))
        np.savez(output_path, **output_dict)

    else:
        gdal_utils.save_gdal(output_path=output_path,
                             bands=output_bands,
                             descriptions=output_desc,
                             geotransform=tuple(geot),
                             geoprojection=coord['geoprojection'],
                             file_format=output_file_format)

    return output_path


if __name__ == '__main__':
    pass

    ############ REMOVE #################
    # config.conf_dict['general']['satellite'] = 'sentinel2'
    # test(tile_path='/media/ignacio/Datos/datasets/satelites/S2_tiles/L1C/S2A_MSIL1C_20170608T105651_N0205_R094_T30TWM_20170608T110453.SAFE',
    #      # roi_x_y=[500, 500, 2500, 1500],
    #      roi_x_y=[6, 6, 495, 495],
    #      max_res=60)

    # config.conf_dict['general']['satellite'] = 'landsat8'
    # test(tile_path='/media/ignacio/Datos/datasets/satelites/LandSat_tiles/LC82150652019025LGN00',
    #      # roi_x_y=[5000, 5000, 8000, 8000],
    #      roi_x_y=[2000, 2000, 4000, 3000],
    #      # roi_x_y=[0, 0, 300, 300],
    #      max_res=30)

    # config.conf_dict['general']['satellite'] = 'sentinel2'
    # test(tile_path='/media/ignacio/Datos/datasets/satelites/S2_tiles/L2A/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE',
    #      roi_x_y=[500, 500, 2500, 1500],
    #      # roi_x_y=[6, 6, 495, 495],
    #      max_res=60)
    #####################################
