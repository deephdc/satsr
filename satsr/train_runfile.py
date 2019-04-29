"""
This is a file to train a super-resolution model for a new satellite.
As an example of training times: 8000 patches * (13 training + 3 validation) samples * 100 epochs =~ 13 hrs

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

from __future__ import division
import time
import os
from datetime import datetime
import json
import shutil

import tensorflow as tf
from keras.backend.tensorflow_backend import set_session
from keras.optimizers import Nadam
import keras.backend as K

from satsr import paths, config, main_sat
from satsr.utils.DSen2Net import s2model
from satsr.utils import misc, data_utils, model_utils

# TODO list
# =========
# TODO: Create a low_RAM version of the code --> ability to create patches for the full image without having to load the
# full image (do this for both TRAINING and PREDICT)
# TODO: Implement resuming training from weigths
# TODO: Move to tf.keras --> solve problems with channels_last
# TODO: Change test to behave like train: If max_res is None it will super-resolve all bands if not only the bands of
# that resolution
# TODO: Move pixel_max_value from patches.py to main_sat.py
# TODO: Define no_data_pixel_value in main_sat.py to use in test function


def train_fn(TIMESTAMP, CONF):

    # # ############# REMOVE #################################
    # CONF['general']['satellite'] = 'sentinel2'
    #
    # CONF['training']['use_tensorboard'] = True
    #
    # CONF['training']['overwrite'] = False
    # CONF['training']['epochs'] = 100
    # CONF['training']['batchsize'] = 64
    #
    # CONF['training']['max_res'] = 60
    # CONF['training']['num_patches'] = 30
    # CONF['training']['roi_x_y'] = [2000, 2000, 6000, 6000]
    # CONF['training']['tiles_directory'] = '/media/ignacio/Datos/datasets/satelites/Sentinel2_tiles/L1C'
    # #
    # # # CONF['training']['max_res'] = 30
    # # # CONF['training']['num_patches'] = 8000
    # # # CONF['training']['roi_x_y'] = [4000, 4000, 8000, 8000]
    # # # CONF['training']['tiles_directory'] = '/media/ignacio/Datos/datasets/satelites/LandSat_tiles'
    # # ########################################################

    if CONF['training']['max_res'] is None:
        CONF['training']['max_res'] = max(main_sat.res_to_bands().keys())

    paths.CONF = CONF
    paths.timestamp = TIMESTAMP
    max_res = CONF['training']['max_res']

    # Dynamically grow the memory used on the GPU
    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    sess = tf.Session(config=tf_config)
    set_session(sess)

    K.set_image_data_format('channels_first')  # TODO

    misc.create_dir_tree()
    misc.backup_splits()

    print('Creating symbolic model')
    default_shapes = main_sat.input_shapes()
    input_shape = {tmp_res: default_shapes[tmp_res] for tmp_res in default_shapes.keys() if int(tmp_res) <= int(max_res)}
    model = s2model(input_shape, num_layers=6, feature_size=128)

    print('Compiling model ...')
    nadam = Nadam(lr=1e-4, beta_1=0.9, beta_2=0.999, epsilon=1e-8, schedule_decay=0.004)  # clipvalue=5e-6
    model.compile(optimizer=nadam, loss='mean_absolute_error', metrics=['mean_squared_error'])
    model.count_params()
    # model.summary()

    # Create data generator for the training set
    train_tiles = data_utils.load_data_splits(splits_dir=paths.get_splits_dir(),
                                              split_name='train')

    # ########### REMOVE ##############
    # train_tiles = train_tiles[:5]
    # #################################

    if CONF['training']['overwrite']:
        # Clear directory from previous patches
        for tile_name in os.listdir(paths.get_patches_dir()):
            tile_path = os.path.join(paths.get_patches_dir(), tile_name)
            shutil.rmtree(tile_path)

        data_utils.create_patches(tiles=train_tiles,
                                  tiles_dir=CONF['training']['tiles_directory'],
                                  save_dir=paths.get_patches_dir(),
                                  roi_x_y=CONF['training']['roi_x_y'],
                                  max_res=max_res,
                                  num_patches=CONF['training']['num_patches'])

    train_gen = data_utils.data_sequence(tiles=train_tiles,
                                         batch_size=CONF['training']['batchsize'],
                                         max_res=max_res)

    # Create data generator for the validation set
    if 'val.txt' in os.listdir(paths.get_splits_dir()):
        val_tiles = data_utils.load_data_splits(splits_dir=paths.get_splits_dir(),
                                                split_name='val')

        if CONF['training']['overwrite']:
            data_utils.create_patches(tiles=val_tiles,
                                      tiles_dir=CONF['training']['tiles_directory'],
                                      save_dir=paths.get_patches_dir(),
                                      roi_x_y=CONF['training']['roi_x_y'],
                                      max_res=max_res,
                                      num_patches=CONF['training']['num_patches'])

        val_gen = data_utils.data_sequence(tiles=val_tiles,
                                           batch_size=CONF['training']['batchsize'],
                                           max_res=max_res)
        val_steps = val_gen.__len__()

    else:
        val_gen, val_steps = None, None

    # Launch the training
    t0 = time.time()

    history = model.fit_generator(generator=train_gen,
                                  steps_per_epoch=train_gen.__len__(),
                                  epochs=CONF['training']['epochs'],
                                  initial_epoch=0,
                                  validation_data=val_gen,
                                  validation_steps=val_steps,
                                  verbose=1,
                                  callbacks=misc.get_callbacks(),
                                  max_queue_size=5, workers=0, use_multiprocessing=False)

    # Saving everything
    print('Saving data to {} folder.'.format(paths.get_timestamped_dir()))
    print('Saving training stats ...')
    stats = {'epoch': history.epoch,
             'training time (s)': round(time.time() - t0, 2),
             'timestamp': TIMESTAMP}
    stats.update(history.history)
    stats_dir = paths.get_stats_dir()
    with open(os.path.join(stats_dir, 'stats.json'), 'w') as outfile:
        json.dump(stats, outfile, sort_keys=True, indent=4)

    print('Saving the configuration ...')
    model_utils.save_conf(CONF)

    print('Saving model yaml')
    model_yaml = model.to_yaml()
    with open(os.path.join(paths.get_conf_dir(), "model.yaml"), 'w') as yaml_file:
        yaml_file.write(model_yaml)

    print('Saving the model to h5...')
    fpath = os.path.join(paths.get_checkpoints_dir(), 'final_model.h5')
    model.save(fpath)

    print('Finished')


if __name__ == '__main__':

    CONF = config.conf_dict
    TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    train_fn(TIMESTAMP=TIMESTAMP, CONF=CONF)
