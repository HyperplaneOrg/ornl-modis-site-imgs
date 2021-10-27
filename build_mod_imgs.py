#!/usr/bin/env python3

# See the README.md file

import json
import logging
import sys
import os
import time
import tarfile
from datetime import datetime
import pandas as pd
import requests

URL = "https://modis.ornl.gov/rst/api/v1/"
ORDURL = "https://modis.ornl.gov/subsetdata"
HEADER = {'Accept': 'application/json'}

# The site file, of the format: site_tag, product, latitude, longitude, email, start_date, end_date, km_above_below, km_left_right
CSV = "sites.csv"

#---------------------------------------------------
def post_myd_mod_09a1(tar_arch):
    logging.debug('rgb debug view images for MODIS/Aqua Surface Reflectance (SREF) 8-Day L3 Global 500m : %s', tar_arch)
    fdir, tname = os.path.split(tar_arch)
    tar = tarfile.open(tar_arch)
    tar.extractall(path=fdir)
    tar.close()
#post_myd_mod_09a1

#---------------------------------------------------
def order(csv):
    coordinates = pd.read_csv(csv)
    logging.debug(coordinates)

    # Convert start_date and end_date columns to datetimes
    coordinates['start_date'] =  pd.to_datetime(coordinates['start_date'])
    coordinates['end_date'] =  pd.to_datetime(coordinates['end_date'])

    # Make new columns for MODIS start and end dates
    coordinates['start_MODIS_date'] = ''
    coordinates['end_MODIS_date'] = ''

    for index, row in coordinates.iterrows():
        len_sid = len(row['site_tag'])
        if len_sid > 8:
            logging.error("The site id %s is too long for the api (max 8, got %d)", row['site_tag'], len_sid)
            sys.exit(1)

        url = URL + row['product'] + '/dates?latitude=' + str(row['latitude']) + '&longitude='+ str(row['longitude'])
        logging.debug(url)
        response = requests.get(url, headers=HEADER)
        # Get dates object as list of python dictionaries
        dates = json.loads(response.text)['dates']
        # Convert to list of tuples; change calendar_date key values to datetimes
        dates = [(datetime.strptime(date['calendar_date'], "%Y-%m-%d"), date['modis_date']) for date in dates]
        # Get MODIS dates nearest to start_date and end_date and add to new pandas columns
        coordinates.loc[index, 'start_MODIS_date'] = min(date[1] for date in dates if date[0] > row['start_date'])
        coordinates.loc[index, 'end_MODIS_date'] = max(date[1] for date in dates if date[0] < row['end_date'])
    #done

    logging.debug(coordinates)

    # Make list to collect order UIDs
    ord_fname = datetime.now().strftime("order_%Y%m%d_%H%M.csv")
    coordinates['order'] = ''

    for index, row in coordinates.iterrows():
        # Build request URL
        url = URL + row['product'] + "/subsetOrder?latitude=" + str(row['latitude']) + \
              "&longitude=" + str(row['longitude']) + "&email=" + row['email'] + "&uid=" + \
              row['site_tag'] + "&startDate=" + row['start_MODIS_date'] + "&endDate=" + \
              row['end_MODIS_date'] + "&kmAboveBelow=" + str(row['kmAboveBelow']) + \
              "&kmLeftRight=" + str(row['kmLeftRight'])

        logging.debug(url)
        response = requests.get(url, headers=HEADER)
        if response.status_code != 200:
            logging.error("Request failed %s", str(response.text))

        orid = json.loads(response.text)['order_id']
        logging.debug("order %s", str(orid))
        coordinates.loc[index, 'order'] = orid
    #done
    logging.debug("writing completed orders to %s ...", ord_fname)
    coordinates.to_csv(ord_fname)
    return ord_fname
#order

#---------------------------------------------------
def retrieve(csv, rest_secs=8):
    """This routine will spin until the orders show up"""
    coordinates_worders = pd.read_csv(csv)
    logging.debug(coordinates_worders)

    #prue the name
    base_dir = csv[:-4]
    ord_done = []

    while True:
        for index, row in coordinates_worders.iterrows():
            if index in ord_done:
                continue
            url = ORDURL +'/' + row['order'] + '/tif/GTiff.tar.gz'
            logging.debug(url)
            response = requests.get(url, headers=HEADER)
            if response.status_code != 200:
                logging.warning("the request may not be ready %s", str(response.text))
                continue
            else:
                fdir = os.path.join(base_dir, row['site_tag'], 'tif')
                if not os.path.exists(fdir):
                    os.makedirs(fdir)
                fname = os.path.join(fdir, 'GTiff.tar.gz')
                with open(fname, "wb") as fout:
                    fout.write(response.content)
                if row['product'] == 'MYD09A1' or row['product'] == 'MOD09A1':
                    post_myd_mod_09a1(fname)
                ord_done.append(index)
        #done
        time.sleep(rest_secs)
    #done
#retrieve

if __name__ == '__main__':
    LOGFILE = None # Add a path to log to file...
    logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)
    try:
        ORDRS = order(CSV)
        #ORDRS = 'order_20211026_2143.csv' # test retrieval
        retrieve(ORDRS) 
    except KeyboardInterrupt as kbex:
        logging.warning("aborted by user...")
        sys.exit(1)
