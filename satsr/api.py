"""
This is a file to make the package compatible with the DEEPaaS API.

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import io
import os
import pkg_resources
import json
import builtins
import mimetypes
from collections import OrderedDict
from datetime import datetime
import shutil

import requests
from webargs import fields, validate
from aiohttp.web import HTTPBadRequest

from satsr import config, paths, main_sat
from satsr.train_runfile import train_fn
from satsr.test_runfile import test, load_models
from satsr.utils import misc


# FIXME: There is a memory leak? --> outputs should be periodically cleared


# def catch_error(f):
#     def wrap(*args, **kwargs):
#         try:
#             return f(*args, **kwargs)
#         except Exception as e:
#             raise HTTPBadRequest(reason=e)
#     return wrap


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


def warm():
    load_models()


def train(**args):
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


# @catch_error
def predict(**args):

    if (not any([args['urls'], args['files']]) or
            all([args['urls'], args['files']])):
        raise Exception("You must provide either 'url' or 'data' in the payload")

    if args['files']:
        args['files'] = [args['files']]  # patch until list is available
        return predict_data(args)
    elif args['urls']:
        args['urls'] = [args['urls']]  # patch until list is available
        return predict_url(args)


def predict_url(args):
    """
    Perform super-resolution on a satellite tile hosted on the web
    """
    update_user_conf(user_args=args)
    conf = config.conf_dict['testing']

    # Use a compressed file hosted on the web
    url = args['urls'][0]
    resp = requests.get(url, stream=True, allow_redirects=True)

    file_format = mimetypes.guess_extension(resp.headers['content-type'])[1:]
    if file_format is None:
        file_format = os.path.splitext(resp.headers['X-Object-Meta-Orig-Filename'])[1][1:]

    # Download and extract the compressed file
    print('Downloading the file ...')
    tile_path = misc.open_compressed(byte_stream=io.BytesIO(resp.raw.read()),
                                     file_format=file_format,
                                     output_folder=os.path.join(paths.get_test_dir(), 'sat_tiles'))

    # Predict and save the output
    try:
        output_path = test(tile_path=tile_path,
                           output_path=conf['output_path'],
                           roi_x_y=conf['roi_x_y_test'],
                           roi_lon_lat=conf['roi_lon_lat_test'],
                           max_res=conf['max_res_test'],
                           copy_original_bands=conf['copy_original_bands'],
                           output_file_format=conf['output_file_format'])
    finally:
        shutil.rmtree(tile_path, ignore_errors=True)

    return open(output_path, 'rb')


def predict_data(args):
    """
    Perform super-resolution on a satellite tile
    """
    update_user_conf(user_args=args)
    conf = config.conf_dict['testing']

    # Process data stream of bytes
    file_format = mimetypes.guess_extension(args['files'][0].content_type)[1:]
    tile_path = misc.open_compressed(byte_stream=open(args['files'][0].filename, 'rb'),
                                     file_format=file_format,
                                     output_folder=os.path.join(paths.get_test_dir(), 'sat_tiles'))

    # Predict and save the output
    try:
        output_path = test(tile_path=tile_path,
                           output_path=conf['output_path'],
                           roi_x_y=conf['roi_x_y_test'],
                           roi_lon_lat=conf['roi_lon_lat_test'],
                           max_res=conf['max_res_test'],
                           copy_original_bands=conf['copy_original_bands'],
                           output_file_format=conf['output_file_format'])
    finally:
        shutil.rmtree(tile_path, ignore_errors=True)

    return open(output_path, 'rb')


def populate_parser(parser, default_conf):
    """
    Fill a parser with arguments
    """
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
            opt_args = {'missing': json.dumps(g_val['value']),
                        'description': help,
                        'required': False,
                        }
            if choices:
                opt_args['enum'] = [json.dumps(i) for i in choices]

            parser[g_key] = fields.Str(**opt_args)

    return parser


def get_train_args():
    parser = OrderedDict()
    default_conf = config.CONF
    default_conf = OrderedDict([('general', default_conf['general']),
                                ('training', default_conf['training'])])
    return populate_parser(parser, default_conf)


def get_predict_args():
    parser = OrderedDict()
    default_conf = config.CONF
    default_conf = OrderedDict([('general', default_conf['general']),
                                ('testing', default_conf['testing'])])

    # Add data and url fields
    parser['files'] = fields.Field(required=False,
                                   missing=None,
                                   type="file",
                                   data_key="data",
                                   location="form",
                                   description="Select the file you want to classify.")

    parser['urls'] = fields.Url(required=False,
                                missing=None,
                                description="Select an URL of the file you want to classify.")
    # missing action="append" --> append more than one url

    # Add format type of the response
    parser['accept'] = fields.Str(description="Media type(s) that is/are acceptable for the response.",
                                  validate=validate.OneOf(["image/tiff"]))

    return populate_parser(parser, default_conf)


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
