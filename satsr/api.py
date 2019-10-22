"""
This is a file to make the package compatible with the DEEPaaS API.

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import os
import pkg_resources
import json
import builtins
import mimetypes
from collections import OrderedDict
from datetime import datetime

import flask
import requests
from werkzeug.exceptions import BadRequest

from satsr import config, paths, main_sat
from satsr.train_runfile import train_fn
from satsr.test_runfile import test
from satsr.utils import misc


# FIXME: There is a memory leak from using flask.send_file to return the prediction.
# --> fixed with cache_timeout flag?
# Flask.send_files stores the response in cache/buffer that means I am losing 100MB of RAM memory (which is the size
# of an typical output with the default parameters) at each iteration (at each POST request for the predict method).
# This bug is NOT fixed by using send_files with BytesIO or using send_from_directory (instead of send_file)
# This bug IS probably fixed by sending to the user an url to download the file instead of the file itself.
# Maybe the file has to be saved in the static folder from flask?


def catch_error(f):
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise BadRequest(e)
    return wrap


def update_user_conf(user_args):
    """
    Update the default YAML configuration with the user's input
    """
    # Update the default conf with the user input
    CONF = config.CONF
    for group, val in sorted(CONF.items()):
        for g_key, g_val in sorted(val.items()):
            if g_key in user_args:
                g_val['value'] = json.loads(user_args[g_key])

    # Check and save the configuration
    config.check_conf(conf=CONF)
    config.conf_dict = config.get_conf_dict(conf=CONF)


@catch_error
def train(args):
    """
    Train a super-resolution model
    """
    update_user_conf(user_args=args)
    CONF = config.conf_dict
    TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    if CONF['training']['max_res'] is None:
        # Train one model for each possible resolution to super-resolve in the satellite
        resolutions = main_sat.res_to_bands().keys()
        min_res = min(resolutions)
        train_res = [res for res in resolutions if res != min_res]
        for res in train_res:
            timestamp = TIMESTAMP + '_model_{}m'.format(res)
            CONF['training']['max_res'] = res
            train_fn(TIMESTAMP=timestamp, CONF=CONF)

    else:
        train_fn(TIMESTAMP=TIMESTAMP, CONF=CONF)


@catch_error
def predict_url(args):
    """
    Perform super-resolution on a satellite tile hosted on the web
    """
    update_user_conf(user_args=args)
    conf = config.conf_dict['testing']

    # Use a compressed file hosted on the web
    url = args['urls'][0]
    resp = requests.get(url, stream=True, allow_redirects=True)

    file_format = mimetypes.guess_extension(resp.headers['content-type'])
    if file_format is None:
        file_format = os.path.splitext(resp.headers['X-Object-Meta-Orig-Filename'])[1][1:]

    # Download and extract the compressed file
    print('Downloading the file ...')
    tile_path = misc.open_compressed(byte_stream=resp.raw.read(),
                                     file_format=file_format,
                                     output_folder=os.path.join(paths.get_test_dir(), 'sat_tiles'))

    # Predict and save the output
    output_path = test(tile_path=tile_path,
                       output_path=conf['output_path'],
                       roi_x_y=conf['roi_x_y_test'],
                       roi_lon_lat=conf['roi_lon_lat_test'],
                       max_res=conf['max_res_test'],
                       copy_original_bands=conf['copy_original_bands'],
                       output_file_format=conf['output_file_format'])

    # Stream the file back
    return flask.send_file(filename_or_fp=output_path,
                           as_attachment=True,
                           attachment_filename=os.path.basename(output_path),
                           cache_timeout=60)


@catch_error
def predict_data(args):
    """
    Perform super-resolution on a satellite tile
    """
    update_user_conf(user_args=args)
    conf = config.conf_dict['testing']

    # Process data stream of bytes
    file_format = mimetypes.guess_extension(args['files'][0].content_type)[1:]
    tile_path = misc.open_compressed(byte_stream=args['files'][0].read(),
                                     file_format=file_format,
                                     output_folder=os.path.join(paths.get_test_dir(), 'sat_tiles'))

    # Predict and save the output
    output_path = test(tile_path=tile_path,
                       output_path=conf['output_path'],
                       roi_x_y=conf['roi_x_y_test'],
                       roi_lon_lat=conf['roi_lon_lat_test'],
                       max_res=conf['max_res_test'],
                       copy_original_bands=conf['copy_original_bands'],
                       output_file_format=conf['output_file_format'])

    # Stream the file back
    return flask.send_file(filename_or_fp=output_path,
                           as_attachment=True,
                           attachment_filename=os.path.basename(output_path),
                           cache_timeout=60)


@catch_error
def get_args(default_conf):
    """
    Returns a dict of dicts with the following structure to feed the deepaas API parser:
    { 'arg1' : {'default': '1',     #value must be a string (use json.dumps to convert Python objects)
                'help': '',         #can be an empty string
                'required': False   #bool
                },
      'arg2' : {...
                },
    ...
    }
    """
    args = OrderedDict()
    for group, val in default_conf.items():
        for g_key, g_val in val.items():
            gg_keys = g_val.keys()

            # Load optional keys
            help = g_val['help'] if ('help' in gg_keys) else ''
            type = getattr(builtins, g_val['type']) if ('type' in gg_keys) else None
            choices = g_val['choices'] if ('choices' in gg_keys) else None

            # Additional info in help string
            help += '\n' + "<font color='#C5576B'> Group name: **{}**".format(str(group))
            if choices:
                help += '\n' + "Choices: {}".format(str(choices))
            if type:
                help += '\n' + "Type: {}".format(g_val['type'])
            help += "</font>"

            # Create arg dict
            opt_args = {'default': json.dumps(g_val['value']),
                        'help': help,
                        'required': False}
            if choices:
                opt_args['choices'] = [json.dumps(i) for i in choices]
            # if type:
            #     opt_args['type'] = type # this breaks the submission because the json-dumping
            #                               => I'll type-check args inside the test_fn

            args[g_key] = opt_args
    return args


@catch_error
def get_train_args():

    default_conf = config.CONF
    default_conf = OrderedDict([('general', default_conf['general']),
                                ('training', default_conf['training'])])
    return get_args(default_conf)


@catch_error
def get_test_args():

    default_conf = config.CONF
    default_conf = OrderedDict([('general', default_conf['general']),
                                ('testing', default_conf['testing'])])
    return get_args(default_conf)


@catch_error
def get_metadata():
    """
    Function to read metadata
    """

    module = __name__.split('.', 1)

    pkg = pkg_resources.get_distribution(module[0])
    meta = {
        'Name': None,
        'Version': None,
        'Summary': None,
        'Home-page': None,
        'Author': None,
        'Author-email': None,
        'License': None,
    }

    for line in pkg.get_metadata_lines("PKG-INFO"):
        for par in meta:
            if line.startswith(par):
                _, value = line.split(": ", 1)
                meta[par] = value

    return meta
