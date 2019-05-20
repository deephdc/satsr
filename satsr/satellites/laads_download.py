"""
File to download data of the LAADS DAAC website.

It support many satellites among whom are VIIRS and MODIS.

Data can be manually downloaded from [1].

[1] https://ladsweb.modaps.eosdis.nasa.gov/search/

Date: February 2019
Author: Ignacio Heredia
Email: iheredia@ifca.unican.es
Github: ignacioheredia
"""

import os
from urllib.request import urlopen
from shutil import copyfileobj
import xml.etree.ElementTree as ET

import requests


class Satellite:

    def __init__(self, inidate, enddate, coordinates=None, producttype='VNP09', collection=5000,
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
        producttype : str
            Dataset type. A list of productypes can be found in https://lpdaac.usgs.gov/product_search/?query=viirs&page=1
        username: str
        password : str
        """
        self.session = requests.Session()

        # Search parameters
        self.inidate = inidate.split('T')[0]
        self.enddate = enddate.split('T')[0]
        self.coord = coordinates
        self.producttype = producttype
        self.collection = collection

        # API
        self.api_url = 'https://modwebsrv.modaps.eosdis.nasa.gov/axis2/services/MODAPSservices/'
        self.credentials = {'username': username, 'password': password}  # no credentials seem to be needed

    def search(self):
        # More methods
        # https://ladsweb.modaps.eosdis.nasa.gov/tools-and-services/lws-classic/quick-start.php

        # Post the query
        query = {'product': self.producttype,
                 'collection': self.collection,
                 'start': self.inidate,
                 'stop': self.enddate,
                 'north': self.coord['N'],
                 'south': self.coord['S'],
                 'west': self.coord['W'],
                 'east': self.coord['E'],
                 'coordsOrTiles': 'coords',
                 'dayNightBoth': 'D'}

        # Get file IDs
        response = self.session.get(self.api_url + 'searchForFiles', params=query)
        response.raise_for_status()
        resp_xml = ET.fromstring(response.text)
        id_list = [item.text for item in resp_xml.findall('return')]

        # Get file urls
        query = {'fileIds': ','.join(id_list)}
        response = self.session.get(self.api_url + 'getFileUrls', params=query)
        resp_xml = ET.fromstring(response.text)
        url_list = [item.text for item in resp_xml.findall('return')]

        # Get file properties
        query = {'fileIds': ','.join(id_list)}
        response = self.session.get(self.api_url + 'getFileProperties', params=query)
        resp_xml = ET.fromstring(response.text)

        # Compose the results list
        results = []
        for i, observation in enumerate(resp_xml):
            tmp_dict = {'url': url_list[i]}
            for property in observation:
                tmp_key = property.tag.split('}')[1]
                tmp_dict[tmp_key] = property.text
            results.append(tmp_dict)

        print('Found {} results for {}'.format(len(results), self.producttype))
        return results

    def download(self, results, output_folder):

        if not isinstance(results, list):
            results = [results]

        # Download the files
        for r in results:
            tile_id = r['fileId']
            print('Downloading {} ...'.format(tile_id))

            filepath = os.path.join(output_folder, r['fileName'])
            if os.path.isfile(filepath):
                print('File already downloaded')
                continue

            with urlopen(r['url']) as in_stream, open(filepath, 'wb') as out_file:
                copyfileobj(in_stream, out_file)
