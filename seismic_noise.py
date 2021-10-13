#!/usr/bin/env python3
# -*- coding: utf-8 -*-


#############################################
# Importation des modules                   #
#############################################

import os
import sys
import json
from glob import glob
import pyproj
import warnings

import urllib.request
from zipfile import ZipFile

import pandas as pd
import numpy as np
import datetime
from dateutil import tz

from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException
from obspy.signal import PPSD

# try:
#     os.environ['PROJ_LIB'] = '/home/flavien/anaconda3/envs/SeismicNoise/share/proj'
# except:
#     pass

from mpl_toolkits.basemap import Basemap

from seismosocialdistancing import *



#############################################
# Définition des fonctions                  #
#############################################




def load_google_mobility(data_path = "DATA/google_mobility",
                         data_url = "https://www.gstatic.com/covid19/mobility/Region_Mobility_Report_CSVs.zip",
                         download_data = False,
                         country_code = "FR",
                         data_type = "global"):
    """
    ├─ DESCRIPTION ─┤
    ├ Récupération des données de mobilités fournies par Google sous la forme d'un DataFrame.
    
    ├─ INPUT ─┤
    ├  data_path     : Emplacement des données en local
    ├  data_url      : URL du fichier ZIP contenant les données
    ├  download_data : Télécharger (True) ou charge des donnes existantes (False)
    ├  country_code  : Code du pays ("FR" pour France)
    ├  data_type     : Récupérer les données de tout le pays ("country"), ou les données par région ("region")
    
    ├─ OUTPUT ─┤
    ├ data_all       : DataFrame contenant l'ensemble des données
    """

    # Téléchargement des données
    if download_data:

        request = urllib.request.urlopen(data_url)
        zipfile = open(data_path+"/data.zip", "wb")
        zipfile.write(request.read())
        zipfile.close()
        zipfile = ZipFile(data_path+"/data.zip")
        zipfile.extractall(path=data_path)
        zipfile.close()
        
    # Lecture des données
    for year in ["2020", "2021"]:
        data = pd.read_csv(data_path + '/' + year + '_FR_Region_Mobility_Report.csv') 
        data = data[['sub_region_1',
                     'sub_region_2',
                     'date',
                     'retail_and_recreation_percent_change_from_baseline',
                     'grocery_and_pharmacy_percent_change_from_baseline',
                     'parks_percent_change_from_baseline',
                     'transit_stations_percent_change_from_baseline',
                     'workplaces_percent_change_from_baseline',
                     'residential_percent_change_from_baseline']]

        data = data.rename(columns={"retail_and_recreation_percent_change_from_baseline": "retail_and_recreation",
                                    "grocery_and_pharmacy_percent_change_from_baseline": "grocery_and_pharmacy",
                                    "parks_percent_change_from_baseline": "parks",
                                    "transit_stations_percent_change_from_baseline": "transit_stations",
                                    "workplaces_percent_change_from_baseline": "workplaces",
                                    "residential_percent_change_from_baseline": "residential"})

        if data_type == "country":
            data = data[data['sub_region_1'].isnull()]
        elif data_type == "region":
            data = data[data['sub_region_1'].notnull()]

        data['date'] = pd.to_datetime(data['date'])
        data = data[['date','sub_region_1','sub_region_2','retail_and_recreation', 'grocery_and_pharmacy', 'parks', 'transit_stations', 'workplaces', 'residential']]
        data = data.set_axis(data['date'], axis=0)
        data = data.drop(columns=['date'])
        
        if year == "2020":
            data_all = data
        else:
            data_all = pd.concat([data_all, data])

    return data_all



def load_apple_mobility(data_path = "DATA/apple_mobility",
                        json_url = "https://covid19-static.cdn-apple.com/covid19-mobility-data/current/v3/index.json",
                        download_data = False,
                        country = "France",
                        data_type = "country"):
    """
    ├─ DESCRIPTION ─┤
    ├ Récupération des données de mobilités fournies par Apple sous la forme d'un DataFrame.
    
    ├─ INPUT ─┤
    ├  data_path     : Emplacement des données en local
    ├  json_url      : URL du fichier json permettant de récupérer le dernier URL à jour
    ├  download_data : Télécharger (True) ou charge des donnes existantes (False)
    ├  country       : Nom du pays
    ├  data_type     : Récupérer les données de tout le pays ("country"), par région ("region"), ou par ville ("city")
    
    ├─ OUTPUT ─┤
    ├ data_all       : DataFrame contenant l'ensemble des données
    """

    # Téléchargement des données
    if download_data:
        with urllib.request.urlopen(json_url) as url:
            json_data = json.loads(url.read().decode())
        data_url = "https://covid19-static.cdn-apple.com" + json_data['basePath'] + json_data['regions']['en-us']['csvPath']
        urllib.request.urlretrieve(data_url, data_path + '/apple_mobility.csv')
        
    # Lecture des données
    data = pd.read_csv(data_path + '/apple_mobility.csv')
    
    if data_type == "country":
        data = data.loc[ (data["region"] == "France") & (data["geo_type"] == "country/region") ]  # France entière
        data = data.drop(columns=['geo_type', 'region', 'alternative_name', 'sub-region', 'country'])
        data_value = data.values[:,1:].T
        data_type = data.values[:,0]
        dates = pd.to_datetime(data.columns[1:])
        data = pd.DataFrame(np.array(data_value), columns=data_type)
        data = data.set_axis(dates, axis=0)
        data_all = data
    
    elif data_type == "region":
        data = data.loc[ (data["country"] == "France") & (data["geo_type"] == "sub-region") ]  # Régions
        data = data.drop(columns=['geo_type', 'alternative_name', 'sub-region', 'country'])
        rg_name = list(set(data["region"]))
        data_all = pd.DataFrame(columns=['region', 'driving', 'walking', 'transit'])
        for rg in rg_name:
            sub_data = data.loc[ data["region"] == rg ]
            type_list = []
            for row in sub_data.iterrows():
                type_list = type_list + [row[1][1]] 
            if not any("driving" in s for s in type_list):
                sub_data = sub_data.append({'region': rg, 'transportation_type': 'driving'}, ignore_index=True)
            if not any("walking" in s for s in type_list):
                sub_data = sub_data.append({'region': rg, 'transportation_type': 'walking'}, ignore_index=True)
            if not any("transit" in s for s in type_list):
                sub_data = sub_data.append({'region': rg, 'transportation_type': 'transit'}, ignore_index=True)
            data_value = sub_data.values[:,2:].T
            data_type = sub_data.values[:,1]
            dates = pd.to_datetime(sub_data.columns[2:])
            sub_data = pd.DataFrame(np.array(data_value), columns=data_type)
            sub_data = sub_data.set_axis(dates, axis=0)
            sub_data["region"] = [rg] * len(data_value)
            sub_data = sub_data[["region", "driving", "walking", "transit"]]
            data_all = pd.concat([data_all, sub_data])
            
    elif data_type == "city":
        data = data.loc[ (data["country"] == "France") & (data["geo_type"] == "city") ]  # Villes
        data = data.drop(columns=['geo_type', 'alternative_name', 'sub-region', 'country'])
        data = data.rename(columns={"region": "city"})
        city_name = list(set(data["city"]))
        data_all = pd.DataFrame(columns=['city', 'driving', 'walking', 'transit'])
        for city in city_name:
            sub_data = data.loc[ data["city"] == city ]
            type_list = []
            for row in sub_data.iterrows():
                type_list = type_list + [row[1][1]] 
            if not any("driving" in s for s in type_list):
                sub_data = sub_data.append({'city': city, 'transportation_type': 'driving'}, ignore_index=True)
            if not any("walking" in s for s in type_list):
                sub_data = sub_data.append({'city': city, 'transportation_type': 'walking'}, ignore_index=True)
            if not any("transit" in s for s in type_list):
                sub_data = sub_data.append({'city': city, 'transportation_type': 'transit'}, ignore_index=True)
            data_value = sub_data.values[:,2:].T
            data_type = sub_data.values[:,1]
            dates = pd.to_datetime(sub_data.columns[2:])
            sub_data = pd.DataFrame(np.array(data_value), columns=data_type)
            sub_data = sub_data.set_axis(dates, axis=0)
            sub_data["city"] = [city] * len(data_value)
            sub_data = sub_data[["city", "driving", "walking", "transit"]]
            data_all = pd.concat([data_all, sub_data])
    
    return data_all



def download_noise(start, end, time_zone, station_str, client, folder_out, datelist):
    """
    ├─ DESCRIPTION ─┤
    ├ Téléchargement des formes d'ondes.
    
    ├─ INPUT ─┤
    ├  start       : (UTCDateTime) Date de début
    ├  end         : (UTCDateTime) Date de fin
    ├  time_zone   : (string) Zone UTC
    ├  station_str : (string) Nom de la station
    ├  client      : (Client) Client pour accéder aux webservices
    ├  folder_out  : (string) Répertoire d'enregistrement des données
    ├  datelist    : (list) Liste des jours à considérer (datetime)
    
    ├─ OUTPUT ─┤
    ├ None
    """
    
    # Création du fichier où seront stockées les données
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)

    station = station_str.split(".")

    for day in datelist:
        
        date_str = day.strftime("%Y-%m-%d")
        file = "{}{}_{}.mseed".format(folder_out, date_str, station_str)
        
        if day != UTCDateTime().datetime and os.path.isfile(file):
            continue
        else:
            try: 
                stream = client.get_waveforms(station[0], station[1], station[2], station[3],
                                              UTCDateTime(day)-1801, UTCDateTime(day)+86400+1801,
                                              attach_response=True)
            except:
                continue
                
            stream.write(file)
        

    
def process_PPSD(start, end, time_zone, station_str, client, folder_in, folder_out, datelist):
    """
    ├─ DESCRIPTION ─┤
    ├ Calcul des PPSDs à partir des formes d'ondes.
    
    ├─ INPUT ─┤
    ├  start       : (UTCDateTime) Date de début
    ├  end         : (UTCDateTime) Date de fin
    ├  time_zone   : (string) Zone UTC
    ├  station_str : (string) Nom de la station
    ├  client      : (Client) Client pour accéder aux webservices
    ├  folder_in   : (string) Répertoire de récupération des données
    ├  folder_out  : (string) Répertoire d'enregistrement des données
    ├  datelist    : (list) Liste des jours à considérer (datetime)
    
    ├─ OUTPUT ─┤
    ├ None
    """
    
    force_reprocess = False
    station = station_str.split(".")
    
    # Création du fichier où seront stockées les données
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)

    for day in datelist:
        
        date_str = day.strftime("%Y-%m-%d")
        file_in = "{}{}_{}.mseed".format(folder_in, date_str, station_str)
        
        if not os.path.isfile(file_in):
            continue

        try:
            resp = client.get_stations(UTCDateTime(day), network=station[0], station=station[1], location=station[2],
                        channel=station[3], level="response")
            stall = read(file_in, headonly=True)
        except:
            continue
        
        for mseedid in list(set([tr.id for tr in stall])):
            file_out = "{}{}_{}.npz".format(folder_out, date_str, mseedid)
            
            if os.path.isfile(file_out) and not force_reprocess:
                continue
            
            try:    
                st = read(file_in, sourcename=mseedid)
            except:
                continue

            st.attach_response(resp)
            ppsd = PPSD(st[0].stats, metadata=resp,
                        ppsd_length=1800, overlap=0.0,
                        period_smoothing_width_octaves=0.025,
                        period_step_octaves=0.0125,
                        period_limits=(0.008, 50),
                        db_bins=(-200, 20, 0.25))
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ppsd.add(st)
                
            ppsd.save_npz(file_out[:-4])
            del st, ppsd
            
        del stall
    
        
        
        
def load_PPSD(list_stations, period, folder_in):
    """
    ├─ DESCRIPTION ─┤
    ├ Lecture des PPSDs déjà stockées au format .npz.
    
    ├─ INPUT ─┤
    ├  list_stations : (list) Liste des stations à étudier (string)
    ├  period        : (list) Date de début et de fin (UTCDateTime)
    ├  folder_in     : (string) Répertoire de récupération des données
    
    ├─ OUTPUT ─┤
    ├ ppsds          : (dict) Dictionnaire contenant un objet PPSD pour chaque
    │                  clé (1 clé = 1 station)
    """
    
    ppsds = {}

    for j in range(len(list_stations)):

        datelist = pd.date_range(period[0].datetime, min(period[1], UTCDateTime()).datetime, freq="D")
        station_str = "{}.{}.{}.{}".format(list_stations[j].split(".")[0], list_stations[j].split(".")[1], list_stations[j].split(".")[2], list_stations[j].split(".")[3])
        mseedid = "{}_{}_{}".format(station_str, datelist[0].strftime("%Y-%m-%d"),datelist[-1].strftime("%Y-%m-%d"))

        for day in datelist:
            date_str = day.strftime("%Y-%m-%d")
            file_pattern = "{}*.npz".format(folder_in, date_str)

            for file in glob(file_pattern):
                
                if mseedid not in ppsds:
                    try:
                        ppsds[mseedid] = PPSD.load_npz(file, allow_pickle=True)
                    except:
                        continue
                else:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        ppsds[mseedid].add_npz(file, allow_pickle=True)

#         try:
#             ppsds[mseedid].save_npz("{}{}.npz".format(folder_out, station_str))
#         except KeyError:
#             continue
            
    return ppsds



def process_DRMS(ppsds, freqs, folder_out):
    """
    ├─ DESCRIPTION ─┤
    ├ Calcul du déplacement RMS.
    
    ├─ INPUT ─┤
    ├  ppsds     : (dict) Dictionnaire contenant un objet PPSD pour chaque
    │              clé (1 clé = 1 station)
    ├  freqs     : (list) Liste des bandes de fréquences à étulier. Chaque
    │              élément contient un tuple au format (freq_min, freq_max)
    ├  folder_in : (string) Répertoire de récupération des données
    ├─ OUTPUT ─┤
    ├ None
    """
    
    # Création du fichier où seront stockées les données
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)

    displacement_RMS = {}
    

    for mseedid, ppsd in ppsds.items():
        ind_times = pd.DatetimeIndex([d.datetime for d in ppsd.current_times_used])
        if ind_times[0].second == 59:
            ind_times = ind_times + pd.Timedelta(1, unit='s')
        ind_times = ind_times.map(lambda x: x.replace(microsecond=0))
        data = pd.DataFrame(ppsd.psd_values, index=ind_times, columns=1./ppsd.period_bin_centers)
        ind_times_i = ind_times[10].replace(hour=0,minute=0,second=0)
        ind_times_f = ind_times[-10].replace(hour=23,minute=59,second=59)
        mask = (ind_times >= ind_times_i) & (ind_times < ind_times_f)
        data = data.loc[mask]
        data = data.sort_index(axis=1)
        displacement_RMS[mseedid] = df_rms(data, freqs, output="DISP")
        displacement_RMS[mseedid].to_csv("{}/{}.csv".format(folder_out, mseedid.split("_")[0]))
    
    del displacement_RMS
    
    
    
def create_map(latmin=41, latmax=52,
               lonmin=-5, lonmax=11,
               resol="i",
               resol_pixels=500,
               style=None,
               bar_width = 500,
               bar_pos = 3):
    
    
    # Définition du type de carte
    m = Basemap(llcrnrlon=lonmin,llcrnrlat=latmin,urcrnrlon=lonmax,urcrnrlat=latmax,\
                width=12000000,height=9000000,\
                rsphere=(6378137.00,6356752.3142), epsg=5520,\
                resolution=resol,area_thresh=1000.,projection='cyl',\
                lat_1=latmin,lat_2=lonmin,lat_0=latmax,lon_0=lonmax)
    
    
    if style==None:
        m.drawmapboundary(fill_color='#85C1E9')
        m.fillcontinents(color='#AB8D52',lake_color='#85C1E9')
    else:
        m.arcgisimage(service=style, xpixels = resol_pixels, verbose= True)
        """
        Services :
        - World_Physical_Map
        - World_Shaded_Relief
        - World_Topo_Map
        - NatGeo_World_Map
        - ESRI_Imagery_World_2D
        - World_Street_Map
        - World_Imagery
        - ESRI_StreetMap_World_2D
        - Ocean_Basemap
        """
    
        
    try:
        m.drawcountries(linewidth=1, zorder=10)
    except:
        pass
    
    try:
        m.drawcoastlines(linewidth=1, zorder=10)
    except:
        pass
    
    parallels = np.arange(latmin, latmax,2.)
    meridians = np.arange(lonmin, lonmax,2.)
    m.drawparallels(parallels,labels=[False,True,True,False], color="gray", zorder=1, linewidth=1)
    m.drawmeridians(meridians,labels=[False,True,True,False], color="gray", zorder=1, linewidth=1)
    
    
    # Positionnement dans les coins
    if bar_pos==1:
        a, b, c = -0.35, +1, 95
    elif bar_pos==2:
        a, b, c = 0.5, -1, 95
    elif bar_pos==3:
        a, b, c = -0.35, +1, 8
    else:
        a, b, c = 0.36, -1, 7
    
    lat_pos = np.linspace(latmin, latmax, 100)[c]
    lon_pos = a*abs(lonmax-lonmin) + b*bar_width/111.0/2.0 + 4.2e-2*lat_pos
    
    m.drawmapscale(lon_pos, lat_pos, lon_pos, lat_pos, bar_width, barstyle='fancy', zorder=100, yoffset=1500*abs(latmax-latmin))
    
    return m



def hourly_var(noise, periods):
    warnings.filterwarnings("ignore")


    ### On reshape l'array en prenant la médiane sur chaque demi-heure
    # noise = noise.resample("30min").median()


    ### On décale les données de 30min pour corriger l'effet de la médiane
    # noise = noise.tshift(30, "min")


    ### Conversion des heures en heures locales
    L = len(noise.index.values)
    utc_list = [ UTCDateTime(str(noise.index.values[i])) for i in range(L) ]
    # local_list = UTCToLocal(utc_list)
    local_list = utc_list
    local_list = [ np.datetime64(local_list[i].strftime("%Y-%m-%dT%H:%M:%S.%fZ")) for i in range(L) ]
    local_list = np.asarray(local_list, dtype='datetime64[ns]')

    new_noise = noise.reindex(local_list, method=None)
    for i in range(L):
        new_noise.iloc(0)[i] = noise.iloc(0)[i]
    noise = new_noise


    ### Création du vecteur temporel
    nDays = int( (periods[0][1]-periods[0][0]) / (3600*24) )  # Nombre de jours de la période étudiée
    tStart = pd.Timestamp(periods[0][0].strftime('%Y-%m-%d'))
    tEnd = pd.Timestamp(periods[0][1].strftime('%Y-%m-%d'))
    t = np.linspace(tStart.value, tEnd.value, nDays+1)
    t = pd.to_datetime(t)[:-1]
    h = np.arange(0, 24, 0.5)


    ### Création et remplissage de la matrice du bruit
    noise_matrix = np.zeros((48, nDays))  # Matrice du bruit (1 colonne = 1 journée / 1 ligne = 1/2 heure)
    for i, day in enumerate(t):
        sublist = noise.loc[noise.index.values < day + np.timedelta64(1,'D')]
        sublist = sublist.loc[sublist.index.values >= day]
        
        k = 48 - len(sublist)
        if k > 0:
            try:
                sublist = [sublist[0]]*k + sublist.to_list()  # Ajout de la première valeur dans toute la période considérée
            except:
                # print(day, "\ŧ", k, "\ŧ", sublist)
                sublist = np.zeros(48)
        elif k < 0:
            # sublist = sublist.drop_duplicates(keep='first')
            sublist = np.zeros(48)

            
        noise_matrix[:,i] = np.asarray(sublist)
        
    return t, h, noise_matrix



def UTCToLocal(utc_time=UTCDateTime()):
    """
    utc_time : liste d'objets UTCDateTime que l'on veut convertir en heure locale
    """
    
    try:
        N = len(utc_time)
    except TypeError:
        utc_time = [utc_time]
        N = 1
        
    from_zone = tz.tzutc()  # Zone UTC
    to_zone = tz.tzlocal()  # Zone locale
    # to_zone = pytz.timezone('ZONE')  # Autre méthode cool pour passer en heure locale
    local_time = []         # Liste des heures locales

    for i in range(N):
        # Conversion en datetime
        utc = datetime.datetime(utc_time[i].year,
                       utc_time[i].month,
                       utc_time[i].day,
                       utc_time[i].hour,
                       utc_time[i].minute,
                       utc_time[i].second,
                       utc_time[i].microsecond)

        # On précise que l'objet datetime est en UTC
        utc = utc.replace(tzinfo=from_zone)

        # Conversion du UTC vers un temps local au format str
        local = utc.astimezone(to_zone).strftime("%Y-%m-%dT%H:%M:%S.%fZ")  

        # Conversion en objet UTCDateTime
        local = UTCDateTime(local)
        
        # Remplissage de la liste des heures locales
        local_time.append(local)
    
    if N == 1:
        return local_time[0]
    else:
        return local_time
