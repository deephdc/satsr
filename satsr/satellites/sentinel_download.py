"""
File to download data of Sentinel satellites from Copernicus Hub.
This file has been adapted from [1].
[1] https://github.com/IFCA/xdc_lfw_data/blob/master/wq_modules/sentinel.py

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

import requests

from satsr.utils import misc


class Satellite:

    def __init__(self, inidate, enddate, coordinates=None, platform='Sentinel-2', producttype='S2MSI1C',
                 username=None, password=None):
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
        platform : str
            Satellite to use from the Sentinel family
        producttype : str
            Dataset type.
        username: str
        password : str
        """
        self.session = requests.Session()

        # Search parameters
        self.inidate = inidate
        self.enddate = enddate
        self.coord = coordinates
        self.producttype = producttype
        self.platform = platform

        # API
        self.api_url = 'https://scihub.copernicus.eu/apihub/'
        self.credentials = {'username': username, 'password': password}

    def search(self, omit_corners=True):

        # Post the query to Copernicus
        query = {'footprint': '"Intersects(POLYGON(({0} {1},{2} {1},{2} {3},{0} {3},{0} {1})))"'.format(self.coord['W'],
                                                                                                        self.coord['S'],
                                                                                                        self.coord['E'],
                                                                                                        self.coord['N']),
                 'producttype': self.producttype,
                 'platformname': self.platform,
                 'beginposition': '[{} TO {}]'.format(self.inidate, self.enddate)
                 }

        data = {'format': 'json',
                'start': 0,  # offset
                'rows': 100,
                'limit': 100,
                'orderby': '',
                'q': ' '.join(['{}:{}'.format(k, v) for k, v in query.items()])
                }

        response = self.session.post(self.api_url + 'search?',
                                     data=data,
                                     auth=(self.credentials['username'], self.credentials['password']),
                                     headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        response.raise_for_status()

        # Parse the response
        json_feed = response.json()['feed']

        if 'entry' in json_feed.keys():
            results = json_feed['entry']
            if isinstance(results, dict):  # if the query returns only one product, products will be a dict not a list
                results = [results]
        else:
            results = []

        # Remove results that are mainly corners
        def keep(r):
            for item in r['str']:
                if item['name'] == 'size':
                    units = item['content'].split(' ')[1]
                    mult = {'KB': 1, 'MB': 1e3, 'GB': 1e6}[units]
                    size = float(item['content'].split(' ')[0]) * mult
                    break
            if size > 0.5e6:  # 500MB
                return True
            else:
                return False
        results[:] = [r for r in results if keep(r)]

        print('Found {} results'.format(json_feed['opensearch:totalResults']))
        print('Retrieving {} results'.format(len(results)))

        return results

    def download(self, results, output_folder):

        if not isinstance(results, list):
            results = [results]

        for r in results:
            url, tile_id = r['link'][0]['href'], r['title']
            print('Downloading {} ...'.format(tile_id))

            save_dir = os.path.join(output_folder, '{}.SAFE'.format(tile_id))
            if os.path.isdir(save_dir):
                print('File already downloaded')
                continue

            response = self.session.get(url, stream=True, allow_redirects=True, auth=(self.credentials['username'],
                                                                                      self.credentials['password']))
            tile_path = misc.open_compressed(byte_stream=response.raw.read(),
                                             file_format='zip',
                                             output_folder=output_folder)
