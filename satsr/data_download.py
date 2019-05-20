"""
File to download data for different satellites

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

from satsr import config


# User configuration
satellite_name = 'MODIS'
inidate = "2019-01-21T18:00:14Z"
enddate = "2019-02-21T18:00:14Z"
keep_first = True

if satellite_name == 'Sentinel':

    from satsr.satellites.sentinel_download import Satellite

    credentials = config.load_credentials('sentinel')
    output_folder = '/media/ignacio/Datos/datasets/satelites/S2_tiles'
    args = {'inidate': inidate,
            'enddate': enddate,
            'coordinates': None,
            'platform': 'Sentinel-2',
            'producttype': 'S2MSI2A',  # 'S2MSI1C'
            'username': credentials['user'],
            'password': credentials['password']}

elif satellite_name == 'LandSat':

    from satsr.satellites.landsat_download import Satellite

    credentials = config.load_credentials('landsat')
    output_folder = '/media/ignacio/Datos/datasets/satelites/LandSat_tiles'
    args = {'inidate': inidate,
            'enddate': enddate,
            'coordinates': None,
            'producttype': 'LANDSAT_8_C1',
            'username': credentials['user'],
            'password': credentials['password']}

elif satellite_name == 'VIIRS':

    from satsr.satellites.laads_download import Satellite

    output_folder = '/media/ignacio/Datos/datasets/satelites/viirs_tiles'
    args = {'inidate': inidate,
            'enddate': enddate,
            'coordinates': None,
            'producttype': 'VNP09',
            'collection': 5000,
            'username': None,  # credentials not needed
            'password': None}

elif satellite_name == 'MODIS':
    # List of product types:
    # ----------------------
    # Level 1B:
    #   * 250m: MOD02HKM
    #   * 750m: MOD02QKM
    #   * 1km:  MOD021KM
    # Level 2A: MOD09

    from satsr.satellites.laads_download import Satellite

    output_folder = '/media/ignacio/Datos/datasets/satelites/modis_tiles'
    args = {'inidate': inidate,
            'enddate': enddate,
            'coordinates': None,
            'producttype': 'MOD09',
            'collection': 6,
            'username': None,  # credentials not needed
            'password': None}


else:
    raise Exception('Invalid satellite name')


regions = {"CdP": {"id": 210788, "coordinates": {"W": -2.830, "S": 41.820, "E": -2.690, "N": 41.910}},
           "Francia": {"id": 234185, "coordinates": {"W": 1.209, "S": 47.807, "E": 2.314, "N": 48.598}},
           "Niger": {"id": 874916, "coordinates": {"W": 11.162, "S": 18.380, "E": 12.338, "N": 19.554}},
           "Brasil": {"id": 187392, "coordinates": {"W": -37.764, "S": -10.602, "E": -32.047, "N": -7.384}},
           "Oceano Pacifico": {"id": 187392, "coordinates": {"W": -155.204, "S": -0.656, "E": -155.195, "N": -0.649}},
           "Siberia": {"id": 187392, "coordinates": {"W": 106.573, "S": 54.158, "E": 106.676, "N": 54.219}},
           "India": {"id": 187392, "coordinates": {"W": 75.889, "S": 22.786, "E": 78.026, "N": 24.965}},
           "Canada": {"id": 187392, "coordinates": {"W": -122.106, "S": 51.229, "E": -122.049, "N": 51.261}},
           "USA": {"id": 187392, "coordinates": {"W": -86.136, "S": 34.960, "E": -86.084, "N": 35.001}},
           "Polonia": {"id": 187392, "coordinates": {"W": 18.345, "S": 50.958, "E": 18.463, "N": 51.027}},
           "Tunez": {"id": 187392, "coordinates": {"W": 9.777, "S": 36.260, "E": 10.921, "N": 36.924}},
           "Antartida": {"id": 187392, "coordinates": {"W": 83.571, "S": -74.779, "E": 83.578, "N": -74.777}},
           "Australia": {"id": 187392, "coordinates": {"W": 139.876, "S": -21.880, "E": 139.880, "N": -21.875}},
           "China": {"id": 187392, "coordinates": {"W": 107.623, "S": 28.631, "E": 107.626, "N": 28.634}},
           "Finlandia": {"id": 187392, "coordinates": {"W": 19.769, "S": 60.967, "E": 23.465, "N": 62.250}},
           "South Africa": {"id": 187392, "coordinates": {"W": 21.796, "S": -29.419, "E": 21.948, "N": -29.284}},
           "Japon": {"id": 187392, "coordinates": {"W": 137.460, "S": 35.587, "E": 141.360, "N": 36.813}},
           "Alemania": {"id": 187392, "coordinates": {"W": 9.938, "S": 50.467, "E": 9.978, "N": 50.486}}}

########## REMOVE ############
# regions = {'CdP': regions['CdP']}
##############################

# Search and download
search_results = []
for k, v in regions.items():
    print('{}'.format(k))
    args['coordinates'] = v['coordinates']
    sat = Satellite(**args)

    results = sat.search()
    if len(results) == 0:
        print('Search returned no results.')
    if len(results) > 1 and keep_first:
        results = [results[0]]

    search_results.extend(results)

sat.download(results=search_results,
             output_folder=output_folder)
