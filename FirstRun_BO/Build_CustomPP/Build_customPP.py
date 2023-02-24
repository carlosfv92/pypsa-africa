# -*- coding: utf-8 -*-
"""

Script to build the custom_powerplant.csv file used in PyPSA-Earth for Bolivia

"""

#%% import libraries 

import pandas as pd
import numpy as np

#%% load file

#format to use
df = pd.read_csv(r'C:/Users/Lenovo/Desktop/pypsa-earth/FirstRun_BO/Build_CustomPP/custom_powerplants.csv', sep=',')
#Name,Fueltype,Technology,Set,Country,Capacity,Efficiency,Duration,Volume_Mm3,DamHeight_m,
#StorageCapacity_MWh,DateIn,DateRetrofit,DateMothball,DateOut,lat,lon,EIC,projectID,bus

#data base to transform
db = pd.read_csv(r'C:/Users/Lenovo/Desktop/pypsa-earth/FirstRun_BO/Build_CustomPP/PowerPlantData_for_custompowerplants_2020.csv', sep=';')

print(df)
print(db)


#%% reshape database

db = db[db.columns[0]].str.split(';', expand=True)

#%% reindexing database

db = db.rename(columns={'Name':'Central','Unit':'Name','Fuel':'Fueltype','Technology':'Technology',
                        'PowerCapacity':'Capacity','STOCapacity':'StorageCapacity_MWh'})

