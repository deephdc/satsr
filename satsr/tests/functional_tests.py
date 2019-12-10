"""
File to run unit tests on the API
"""

from deepaas.model.v2.wrapper import UploadedFile

from satsr.api import predict_data, predict_url


def test_predict_url():
    url = 'https://cephrgw01.ifca.es:8080/swift/v1/satellite_samples/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE.zip'
    args = {'urls': [url], 'roi_x_y_test': "[2000, 2000, 2500, 2500]", 'max_res_test': "20"}
    results = predict_url(args)


def test_predict_data():
    """
    This function doesn't work because mimetype is not able to recover the correct file format when we create a
    FileStorage object manually like this.
    """
    # fpath = '/media/ignacio/Datos/datasets/satelites/S2A_MSIL1C_20170608T105651_N0205_R094_T30TWM_20170608T110453.SAFE.tar.xz'
    # content_type = 'application/x-xz'

    fpath = '/media/ignacio/Datos/datasets/satelites/S2A_MSIL2A_20190123T040041_N0211_R004_T48UXF_20190123T061251.SAFE.zip'
    content_type = 'application/zip'

    file = UploadedFile(name='data', filename=fpath, content_type=content_type)
    args = {'files': [file], 'roi_x_y_test': "[2000, 2000, 2500, 2500]", 'max_res_test': "20"}
    results = predict_data(args)


if __name__ == '__main__':
    pass
    # test_predict_data()
    # test_predict_url()
