"""
File to run unit tests on the API
"""

from werkzeug.datastructures import FileStorage

from satsr.api import predict_data, predict_url


def test_predict_url():
    url = 'https://cephrgw01.ifca.es:8080/swift/v1/satellite_samples/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE.zip'
    args = {'urls': [url]}
    results = predict_url(args)


def test_predict_data():
    """
    This function doesn't work because mimetype is not able to recover the correct file format when we create a
    FileStorage object manually like this.
    """
    fpath = '/media/ignacio/Datos/datasets/satelites/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE.zip'
    file = FileStorage(open(fpath, 'rb'))
    args = {'files': [file]}
    results = predict_data(args)


if __name__ == '__main__':
    pass
    # test_predict_data()
    # test_predict_url()
