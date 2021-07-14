from urllib.request import urlopen
from zipfile import ZipFile
import os
import pandas as pd
import os
os.environ['PROJ_LIB'] = '/home/flavien/anaconda3/envs/SeismicNoise/share/proj'
from mpl_toolkits.basemap import Basemap
import numpy as np

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
    ├  data_type     : Récupérer les données de tout le pays ("global"), ou les données par région ("local")
    
    ├─ OUTPUT ─┤
    ├ data_all       : DataFrame contenant l'ensemble des données
    """

    # Téléchargement des données
    if download_data:

        request = urlopen(data_url)
        zipfile = open(data_path+"/data.zip", "wb")
        zipfile.write(request.read())
        zipfile.close()
        zipfile = ZipFile(data_path+"/data.zip")
        zipfile.extract(path=data_path)
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

        if data_type == "global":
            data = data[data['sub_region_1'].isnull()]
        elif data_type == "local":
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