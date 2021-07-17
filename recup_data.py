#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pour l'exécution du fichier depuis un terminal : 
./recup_data.py data_path start_time end_time

Exemples : 
./recup_data.py "DATA/st_metadata/stations_fr.txt" "2020-01-01" "2020-07-01"
./recup_data.py "DATA/st_metadata/st_test.txt" "2020-01-01" "2020-02-01"
"""



#############################################
# Importation des modules                   #
#############################################

import glob, os

import numpy as np
import pandas as pd
import warnings
import datetime
import sys

from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException
from obspy.signal import PPSD

from seismic_noise import download_noise, process_PPSD, load_PPSD, process_DRMS



#############################################
# Paramètres initiaux                       #
#############################################

time_zone = "Europe/Brussels"        # Format d'heure
dl_noise = True
proc_PPSD = True
proc_DRMS = True
PPSD_FOLDER  = "/media/flavien/Stockage/SeismicNoiseData/test/PPSD"
DRMS_FOLDER  = "/media/flavien/Stockage/SeismicNoiseData/test/DRMS"
MSEED_FOLDER = "/media/flavien/Stockage/SeismicNoiseData/test/MSEED"
delete_MSEED = False
freqs = [(4, 14)]



#############################################
# Entrées dans le programme directement     #
#############################################

start_date = "2020-01-01"    # Start Time
end_date = "2021-01-01"      # End Time
st_file = "DATA/st_metadata/stations_fr.txt"



#############################################
# Entrées par ligne de commande             #
#############################################

try:
    file = sys.argv[1]         # Nom du fichier complet
    start_date = sys.argv[2]   # Date de début au format AAAA-MM-JJ
    end_date = sys.argv[3]     # Date de FIN au format AAAA-MM-JJ
    start = UTCDateTime(start_date)    # Start Time
    end = UTCDateTime(end_date)             # End Time
    all_stations = np.loadtxt(file, dtype=str)
except:
    start = UTCDateTime(start_date)
    end = UTCDateTime(end_date)
    all_stations = np.loadtxt(st_file, dtype=str)

period = [start, end]
    
try:
    len(all_stations)
except:
    all_stations = np.append(list(), all_stations)

if not os.path.exists(MSEED_FOLDER): os.makedirs(MSEED_FOLDER)
if not os.path.exists(PPSD_FOLDER):  os.makedirs(PPSD_FOLDER)
if not os.path.exists(DRMS_FOLDER):  os.makedirs(DRMS_FOLDER)


    
#############################################
# Corps du programme                        #
#############################################

print("[{}] [INFO] Début du programme".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

datelist = pd.date_range(start.datetime, min(end, UTCDateTime()).datetime, freq="D")  # Jours à récupérer
client = Client("RESIF")  # Client utilisé pour récupérer les donnée via le webservice

k = 1
for station_str in all_stations:
    
    PPSD_FILES  = PPSD_FOLDER  + "/{}/".format(station_str)
    DRMS_FILES  = DRMS_FOLDER  + "/{}/".format(station_str)
    MSEED_FILES = MSEED_FOLDER + "/{}/".format(station_str)
    print("[{}] [INFO] Station {}/{} {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), k, len(all_stations), station_str))
    
    if dl_noise:
        print("[{}] [INFO]     Collecting ...".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        download_noise(start, end, time_zone, station_str, client, MSEED_FILES, datelist)
        
    if proc_PPSD:
        print("[{}] [INFO]     Processing PPSD ... ".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ppsds = process_PPSD(start, end, time_zone, station_str, client, MSEED_FILES, PPSD_FILES, datelist)
        if delete_MSEED:
            for f in glob.glob("{}*.mseed".format(MSEED_FILES)):
                try:
                    os.remove(f)
                except:
                    pass
            
    if proc_DRMS:
        print("[{}] [INFO]     Processing RMS ... ".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ppsds = load_PPSD(np.append(list(), station_str), period, PPSD_FILES)
        process_DRMS(ppsds, freqs, DRMS_FOLDER)
        
    k += 1

print("[{}] [INFO] FIN - Arrêt du programme".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))