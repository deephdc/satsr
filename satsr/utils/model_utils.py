from __future__ import division
import os
import json

import numpy as np

from satsr import paths, main_sat
from satsr.utils.DSen2Net import s2model
from satsr.utils.patches import recompose_images, get_test_patches


def super_resolve(data_bands, model, patch_size=128, border=8):
    """
    Parameters
    ----------
    data_bands : dict
    model : Keras model
    patch_size : int
    border : int

    Returns
    -------
    Numpy array with the super-resolved image
    """
    # Normalize pixel values  and put image in float32 format
    for res in data_bands.keys():
        data_bands[res] = data_bands[res].astype(np.float32)
        data_bands[res] = (data_bands[res] - main_sat.min_val()) / (main_sat.max_val() - main_sat.min_val())

    # Get the patches and predict
    patches = get_test_patches(data_bands=data_bands, patch_size=patch_size, border=border)
    patches = {str(res): data for res, data in patches.items()}
    prediction = model.predict(patches, verbose=1)

    # Recompose the image from the patches
    min_res = min(data_bands.keys())
    images = recompose_images(prediction, border=border, size=data_bands[min_res].shape)

    # Undo the pixel normalization and clip to allowed pixel values
    images = images * (main_sat.max_val() - main_sat.min_val()) + main_sat.min_val()
    images = np.clip(images, a_min=main_sat.min_val(), a_max=main_sat.max_val())

    return images


def load_model(input_shape, modelname):
    """
    Load Keras model from weights
    """
    paths.timestamp = modelname
    model_path = os.path.join(paths.get_checkpoints_dir(), 'final_model.h5')
    model = s2model(input_shape, num_layers=6, feature_size=128)
    model.load_weights(model_path)
    return model


def save_conf(conf):
    """
    Save CONF to a txt file to ease the reading and to a json file to ease the parsing.
    Parameters
    ----------
    conf : 1-level nested dict
    """
    save_dir = paths.get_conf_dir()

    # Save dict as json file
    with open(os.path.join(save_dir, 'conf.json'), 'w') as outfile:
        json.dump(conf, outfile, sort_keys=True, indent=4)

    # Save dict as txt file for easier readability
    txt_file = open(os.path.join(save_dir, 'conf.txt'), 'w')
    txt_file.write("{:<25}{:<30}{:<30} \n".format('group', 'key', 'value'))
    txt_file.write('=' * 75 + '\n')
    for key, val in sorted(conf.items()):
        for g_key, g_val in sorted(val.items()):
            txt_file.write("{:<25}{:<30}{:<15} \n".format(key, g_key, str(g_val)))
        txt_file.write('-' * 75 + '\n')
    txt_file.close()
