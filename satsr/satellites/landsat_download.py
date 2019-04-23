"""
File to download data of LandSat satellites.

This file has been adapted from [1]. Info about the API can be found in [2]. Credentials to use are the one used to
login in [3].

[1] https://github.com/IFCA/xdc_lfw_data/blob/master/wq_modules/landsat.py
[2] https://earthexplorer.usgs.gov/inventory/documentation
[3] https://ers.cr.usgs.gov/login/

Original author: Daniel Garcia Diaz
Date: Sep 2018

Adaptation
----------
Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import os
import json
import re

import requests

from satsr.utils import misc


class Satellite:

    def __init__(self, inidate, enddate, coordinates=None, producttype='LANDSAT_8_C1', username=None, password=None):
        """
        Parameters
        ----------
        inidate : str
            Initial date of the query in format '%Y-%m-%dT%H:%M:%SZ'
        enddate : str
            Final date of the query in format '%Y-%m-%dT%H:%M:%SZ'
        coordinates : dict
            Coordinates of the region to search.
            Example: {"W": -2.830, "S": 41.820, "E": -2.690, "N": 41.910}}
        producttype : str
            Dataset type. A list of productypes can be found in https://mapbox.github.io/usgs/reference/catalog/ee.html
        username: str
        password : str
        """
        self.session = requests.Session()

        # Search parameters
        self.inidate = inidate
        self.enddate = enddate
        self.coord = coordinates
        self.producttype = producttype

        # API
        api_version = '1.4.1'
        self.api_url = 'https://earthexplorer.usgs.gov/inventory/json/v/{}/'.format(api_version)
        self.login_url = 'https://ers.cr.usgs.gov/login/'
        self.credentials = {'username': username, 'password': password}

        # Fetching the API key
        data = {'username': username,
                'password': password,
                'catalogID': 'EE'}
        response = self.session.post(self.api_url + 'login?',
                                     data={'jsonRequest': json.dumps(data)})
        response.raise_for_status()
        json_feed = response.json()
        if json_feed['error']:
            raise Exception('Error while searching: {}'.format(json_feed['error']))
        self.api_key = json_feed['data']

    def search(self):

        # Post the query
        query = {'datasetName': self.producttype,
                 'includeUnknownCloudCover': False,
                 'maxResults': 100,
                 'temporalFilter': {'startDate': self.inidate,
                                    'endDate': self.enddate},
                 'spatialFilter': {'filterType': 'mbr',
                                   'lowerLeft': {'latitude': self.coord['S'],
                                                 'longitude': self.coord['W']},
                                   'upperRight': {'latitude': self.coord['N'],
                                                  'longitude': self.coord['E']}
                                   },
                 'apiKey': self.api_key
                 }

        response = self.session.post(self.api_url + 'search',
                                     params={'jsonRequest': json.dumps(query)})
        response.raise_for_status()
        json_feed = response.json()
        if json_feed['error']:
            raise Exception('Error while searching: {}'.format(json_feed['error']))
        results = json_feed['data']['results']

        print('Found {} results from Landsat'.format(len(results)))
        return results

    def download(self, results, output_folder):

        if not isinstance(results, list):
            results = [results]

        # Make the login
        response = self.session.get(self.login_url)
        data = {'username': self.credentials['username'],
                'password': self.credentials['password'],
                'csrf_token': re.findall(r'name="csrf_token" value="(.+?)"', response.text),
                '__ncforminfo': re.findall(r'name="__ncforminfo" value="(.+?)"', response.text)
                }
        response = self.session.post(self.login_url, data=data, allow_redirects=False)
        response.raise_for_status()

        # Download the files
        for r in results:
            tile_id = r['entityId']
            print('Downloading {} ...'.format(tile_id))
            url = 'https://earthexplorer.usgs.gov/download/12864/{}/STANDARD/EE'.format(tile_id)
            response = self.session.get(url, stream=True, allow_redirects=True)

            save_dir = os.path.join(output_folder, tile_id)
            if not os.path.isdir(save_dir):
                os.mkdir(save_dir)
            else:
                print('File already downloaded')
                continue

            tile_path = misc.open_compressed(byte_stream=response.raw.read(),
                                             file_format='gz',
                                             output_folder=save_dir)
