#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
├─ DESCRIPTION ─┤
├ Ce script permet de récupérer et de traiter les formes d'ondes pour
│ calculer les PPSD et le déplacement RMS

├─ UTILISATION ─┤
│ Pour l'exécution du fichier depuis un terminal : 
├ ./recup_data.py data_path start_time end_time

├─ EXEMPLE ─┤ 
├ ./recup_data.py "DATA/st_metadata/stations_fr.txt" "2020-01-01" "2020-07-01"
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
import urllib.request
import zipfile



#############################################
# Paramètres initiaux                       #
#############################################

time_zone = "Europe/Brussels"     # Format d'heure
dl_PPSD = True                    # Téléchargement des PPSDs
dl_noise = False                   # Téléchargement des données
proc_PPSD = False                  # Calcul des PPSDs
proc_DRMS = True                  # Calcul du déplacement RMS
delete_MSEED = False              # Suppression des fichiers MSEED
PPSD_FOLDER  = "/media/flavien/Stockage/SeismicNoiseData/PPSD"
DRMS_FOLDER  = "/media/flavien/Stockage/SeismicNoiseData/DRMS"
MSEED_FOLDER = "/media/flavien/Stockage/SeismicNoiseData/MSEED"
freqs = [(0.01, 0.03), (0.1, 0.25), (0.3, 1), (1, 3), (5, 15), (20, 50)]                 # Bandes de fréquence à étudier



#############################################
# Entrées dans le programme directement     #
#############################################

start_date = "2020-01-01"    # Date de début
end_date = "2021-01-01"      # Date de fin
st_file = "DATA/st_metadata/stations_fr.txt"  # Fichier de stations


#test github
#############################################
# Entrées par ligne de commande             #
#############################################

### Récupération des variables
try:
    file = sys.argv[1]
    start_date = sys.argv[2]
    end_date = sys.argv[3]
    start = UTCDateTime(start_date)
    end = UTCDateTime(end_date)
    all_stations = np.loadtxt(file, dtype=str)
except:
    start = UTCDateTime(start_date)
    end = UTCDateTime(end_date)
    all_stations = np.loadtxt(st_file, dtype=str)

### Liste des stations à traiter
try:
    len(all_stations)
except:
    all_stations = np.append(list(), all_stations)
    
### Création des répertoires de données
if not os.path.exists(MSEED_FOLDER): os.makedirs(MSEED_FOLDER)
if not os.path.exists(PPSD_FOLDER):  os.makedirs(PPSD_FOLDER)
if not os.path.exists(DRMS_FOLDER):  os.makedirs(DRMS_FOLDER)
    
period = [start, end]


    
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
    
    ### Téléchargement des données
    if dl_noise:
        print("[{}] [INFO]     Collecting ...".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        download_noise(start, end, time_zone, station_str, client, MSEED_FILES, datelist)
        
    ### Téléchargement des PPSDs
    if dl_PPSD:
        print("[{}] [INFO]     Collecting PPSDs ... ".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        filename = PPSD_FOLDER + 'data.zip'
        net, sta, loc, cha = tuple(station_str.split("."))
        url = "https://ws.resif.fr/resifws/ppsd/1/query?net={}&sta={}&loc={}&cha={}&starttime={}&endtime={}&format=npz&nodata=404".format(net,sta,loc,cha,start_date,end_date)
        try:
            urllib.request.urlretrieve(url, filename)
        except HTTPError:
            pass
        else:
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall(PPSD_FOLDER)
            os.remove(filename)
    
    ### Calcul des PPSDs
    if proc_PPSD:
        print("[{}] [INFO]     Processing PPSD ... ".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ppsds = process_PPSD(start, end, time_zone, station_str, client, MSEED_FILES, PPSD_FILES, datelist)
        if delete_MSEED:
            for f in glob.glob("{}*.mseed".format(MSEED_FILES)):
                try:
                    os.remove(f)
                except:
                    pass
    
    ### Calcul du déplacement RMS
    if proc_DRMS:
        print("[{}] [INFO]     Processing RMS ... ".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ppsds = load_PPSD(np.append(list(), station_str), period, PPSD_FILES)
        process_DRMS(ppsds, freqs, DRMS_FOLDER)
        
    k += 1

print("[{}] [INFO] FIN - Arrêt du programme".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))