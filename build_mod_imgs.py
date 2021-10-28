#!/usr/bin/env python3

# See the README.md file

import json
import logging
import sys
import os
from datetime import datetime
import numpy
from PIL import Image
import pandas as pd
import requests

URL = "https://modis.ornl.gov/rst/api/v1/"
ORDURL = "https://modis.ornl.gov/subsetdata"
HEADER = {'Accept': 'application/json'}

# The site file, of the format: site_tag,latitude,longitude,start_date,end_date,kmAboveBelow,kmLeftRight
CSV = "sites-subset.csv"

BANDS = ['sur_refl_b01', 'sur_refl_b04', 'sur_refl_b03', 'sur_refl_qc_500m']
PROD = ['MYD09A1', 'MOD09A1']
# MOD Land QC
MDLND_QC = 3 # 11
# MXD09A1 QC, this runs parallel to BANDS, defs at https://lpdaac.usgs.gov/documents/925/MOD09_User_Guide_V61.pdf
BANDS_QC = [
    60,      # 111100, band 1
    15360,   # 11110000000000, band 3
    245760   # 111100000000000000, band 4
]
IMG_DIR= 'site-imgs'

#---------------------------------------------------
def json_2_channel(band_name, band_idx, data, qc_band):
    nsubs = len(data[band_name]['subset'])
    if nsubs > 1:
        logging.warning("using the first subset for %s ...", band_name)
    arr = numpy.array(data[band_name]['subset'][0]['data'], dtype='f4') * float(data[band_name]['scale'])
    dat = ((arr - arr.min()) * (1/(arr.max() - arr.min()) * 255)).astype('uint8')
    # clean with mod land qc
    qc = qc_band & MDLND_QC  
    dat = numpy.ma.masked_where(qc != 0, dat, copy=False)
    # clean with band qc 
    qc = qc_band & BANDS_QC[band_idx] 
    dat = numpy.ma.masked_where(qc != 0, dat, copy=False)
    return dat
#json_2_channel

#---------------------------------------------------
def post_m09a1(data):
    logging.debug('rgb debug images for MODIS Terra or Aqua Surface Reflectance (SREF) 8-Day L3 Global 500m...')
    qc = numpy.array(data['sur_refl_qc_500m']['subset'][0]['data'], dtype='u4')
    redish = json_2_channel('sur_refl_b01', 0, data, qc)
    greenish = json_2_channel('sur_refl_b04', 1, data, qc)
    blueish = json_2_channel('sur_refl_b03', 2, data, qc)
    msk = redish.mask | greenish.mask | blueish.mask
    alpha = numpy.where(msk == True, 0, 255).astype('uint8') 
    shp = data['sur_refl_b01']['nrows'], data['sur_refl_b01']['ncols'], 4
    rgba = numpy.dstack((redish, greenish, blueish, alpha)).reshape(shp)
    img = Image.fromarray(rgba ,'RGBA')
    img.save(data['name'])
#post_m09a1

#---------------------------------------------------
def subset_site_data(csv, prod):
    coordinates = pd.read_csv(csv)
    logging.debug(coordinates)

    # Convert start_date and end_date columns to datetimes
    coordinates['start_date'] =  pd.to_datetime(coordinates['start_date'])
    coordinates['end_date'] =  pd.to_datetime(coordinates['end_date'])

    # Make new columns for MODIS start and end dates
    coordinates['start_MODIS_date'] = ''
    coordinates['end_MODIS_date'] = ''
    time_idx = {}

    for index, row in coordinates.iterrows():
        url = URL + prod + '/dates?latitude=' + str(row['latitude']) + '&longitude='+ str(row['longitude'])
        logging.debug(url)
        response = requests.get(url, headers=HEADER)
        # Get dates object as list of python dictionaries
        dates = json.loads(response.text)['dates']
        # Convert to list of tuples; change calendar_date key values to datetimes
        dates = [(datetime.strptime(date['calendar_date'], "%Y-%m-%d"), date['modis_date']) for date in dates]
        # Get MODIS dates nearest to start_date and end_date and add to new pandas columns
        coordinates.loc[index, 'start_MODIS_date'] = min(date[1] for date in dates if date[0] >= row['start_date'])
        coordinates.loc[index, 'end_MODIS_date'] = max(date[1] for date in dates if date[0] <= row['end_date'])
        time_idx[row['site_tag']] = [date[1] for date in dates if date[0] <= row['end_date'] and date[0] >= row['start_date']]
    #done
    logging.debug(coordinates)

    for index, row in coordinates.iterrows():
        fdir = os.path.join(IMG_DIR, row['site_tag'])
        if not os.path.exists(fdir):
            os.makedirs(fdir)
        for doi in time_idx[row['site_tag']]:
            data_obj = {}
            data_obj['name'] = os.path.join(fdir, prod+'_'+doi+'_rgb.png')
            for band in BANDS:
                url = URL + prod + "/subset?latitude=" + str(row['latitude']) + "&longitude=" + str(row['longitude']) + \
                       "&startDate=" + doi + "&endDate=" + doi + "&kmAboveBelow=" + str(row['kmAboveBelow']) + \
                       "&kmLeftRight=" + str(row['kmLeftRight']) + "&band="+band

                logging.debug(url)
                response = requests.get(url, headers=HEADER)
                if response.status_code != 200:
                    logging.error("Request failed %s", str(response.text))
                    continue
                else:
                    subset = json.loads(response.text)
                    data_obj[band] = subset
            #done
            post_m09a1(data_obj)
            break
        #done
        break
    #done
    logging.debug("done writing subsets ...")
#subset_site_data

if __name__ == '__main__':
    LOGFILE = None # Add a path to log to file...
    logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)
    try:
        for PRD in PROD:
            subset_site_data(CSV, PRD)
    except KeyboardInterrupt as kbex:
        logging.warning("aborted by user...")
        sys.exit(1)
