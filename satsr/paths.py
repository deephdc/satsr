"""
Miscellaneous functions manage paths.

Date: September 2018
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import os.path
from datetime import datetime

from satsr import config


homedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONF = config.get_conf_dict()
timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')


def get_timestamp():
    return timestamp


def get_base_dir():
    base_dir = CONF['general']['base_directory']
    if os.path.isabs(base_dir):
        return base_dir
    else:
        return os.path.abspath(os.path.join(homedir, base_dir))


def get_tiles_dir():
    tiles_dir = CONF['training']['tiles_directory']
    if os.path.isabs(tiles_dir):
        return tiles_dir
    else:
        return os.path.abspath(os.path.join(homedir, tiles_dir))


def get_data_dir():
    return os.path.join(get_base_dir(), "data")


def get_splits_dir():
    return os.path.join(get_data_dir(), "dataset_files")


def get_test_dir():
    return os.path.join(get_data_dir(), "test")


def get_patches_dir():
    return os.path.join(get_data_dir(), "patches")


def get_models_dir():
    return os.path.join(get_base_dir(), "models")


def get_timestamped_dir():
    return os.path.join(get_models_dir(), timestamp)


def get_checkpoints_dir():
    return os.path.join(get_timestamped_dir(), "ckpts")


def get_logs_dir():
    return os.path.join(get_timestamped_dir(), "logs")


def get_conf_dir():
    return os.path.join(get_timestamped_dir(), "conf")


def get_stats_dir():
    return os.path.join(get_timestamped_dir(), "stats")


def get_ts_splits_dir():
    return os.path.join(get_timestamped_dir(), "dataset_files")


def get_predictions_dir():
    return os.path.join(get_timestamped_dir(), "predictions")


def get_dirs():
    return {'base dir': get_base_dir(),
            'tiles dir': get_tiles_dir(),
            'data splits dir': get_splits_dir(),
            'models_dir': get_models_dir(),
            'timestamped dir': get_timestamped_dir(),
            'logs dir': get_logs_dir(),
            'checkpoints dir': get_checkpoints_dir(),
            'configuration dir': get_conf_dir(),
            'statistics dir': get_stats_dir(),
            'timestamped data splits dir': get_ts_splits_dir(),
            'predictions dir': get_predictions_dir(),
            }


def print_dirs():
    dirs = get_dirs()
    max_len = max([len(v) for v in dirs.keys()])
    for k,v in dirs.items():
        print('{k:{l:d}s} {v:3s}'.format(l=max_len + 5, v=v, k=k))


def main():
    return print_dirs()


if __name__ == "__main__":
    main()
