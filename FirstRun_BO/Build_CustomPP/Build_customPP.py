# -*- coding: utf-8 -*-
"""

Script to build the custom_powerplant.csv file used in PyPSA-Earth for Bolivia

"""

#%% import libraries 

import pandas as pd
import numpy as np

#%% load file

#format to use when using commas "," as separators
df = pd.read_csv(r'C:/Users/Lenovo/Desktop/pypsa-earth/FirstRun_BO/Build_CustomPP/Format_custom_powerplants.csv', sep=',')
#Name,Fueltype,Technology,Set,Country,Capacity,Efficiency,Duration,Volume_Mm3,DamHeight_m,
#StorageCapacity_MWh,DateIn,DateRetrofit,DateMothball,DateOut,lat,lon,EIC,projectID,bus

#data base to transform and loading file that uses ";" as separators
db = pd.read_csv(r'C:/Users/Lenovo/Desktop/pypsa-earth/FirstRun_BO/Build_CustomPP/New_custompowerplants_2020_2.csv', sep=';')

print(df)
print(db)


#%% save as new csv file

db.to_csv('custom_powerplants.csv',index=False)


#%% Check infor on created powerplants file

df_pp = pd.read_csv(r'C:/Users/Lenovo/Desktop/pypsa-earth/resources/powerplants.csv')

print(df_pp.iloc[:,[6]].sum(axis=0))
#print(df_pp['Capacity'])

#%% check base network data on buses
import pypsa

base_network = "C:/Users/Lenovo/Desktop/pypsa-earth/networks/base.nc"

bn = pypsa.Network(base_network)

