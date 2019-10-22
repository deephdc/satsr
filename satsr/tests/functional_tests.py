"""
File to run unit tests on the API
"""

from werkzeug.datastructures import FileStorage

from satsr import config
from satsr.api import predict_data, predict_url
from satsr.test_runfile import test


def test_predict_url():
    url = 'https://cephrgw01.ifca.es:8080/swift/v1/satellite_samples/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE.zip'
    args = {'urls': [url]}
    results = predict_url(args)


def test_predict_data():
    """
    This function doesn't work because mimetype is not able to recover the correct file format when we create a
    FileStorage object manually like this.
    """
    fpath = '/media/ignacio/Datos/datasets/satelites/sentinel2_tiles/L2A/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE'
    conf = config.conf_dict
    output_path = test(tile_path=fpath,
                       output_path=conf['testing']['output_path'],
                       roi_x_y=conf['testing']['roi_x_y_test'],
                       roi_lon_lat=conf['testing']['roi_lon_lat_test'],
                       max_res=conf['testing']['max_res_test'],
                       copy_original_bands=conf['testing']['copy_original_bands'],
                       output_file_format=conf['testing']['output_file_format'])


if __name__ == '__main__':
    pass
    # test_predict_data()
    # test_predict_url()
