# -*- coding: utf-8 -*-
"""
# Plotting PyPSA results (adapted for a First Run of Bolivia - config.yaml file)

### Adele will check for additional results that can be used

"""
#%% 1

#importing libraries

import logging
import os
import pypsa
import yaml
import pandas as pd
import geopandas as gpd
#import geoviews as gv
#import hvplot.pandas 
import numpy as np
import scipy as sp
import networkx as nx

# plotting stuff
import matplotlib.pyplot as plt
plt.style.use("bmh")
import seaborn as sns  ###
import cartopy.crs as ccrs
sns.set(style="darkgrid")
from scipy.sparse import csgraph
from itertools import product
from shapely.geometry import Point, LineString
import shapely, shapely.prepared, shapely.wkt
logger = logging.getLogger(__name__)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 70)
import sys
sys.path.append("../")  # to import helpers
#from scripts._helpers import sets_path_to_root


#sets_path_to_root("pypsa-earth")
max_node_size = 1.0  # maximum size of a node for plotting purposes [used in plots]

# utility function for nice plotting
def normalize_node_size(values, max_node_size=max_node_size):
    return values / values.max() * max_node_size

#%% 2

#loading solved networks/results and plot results

#os.getcwd()  gets the path to where the library is selected and the rest is link to the simulation's result

solved_network = os.getcwd() + "/results/networks/elec_s_10_ec_lcopt_Co2L-6H.nc"

n_solve = pypsa.Network(solved_network)

n = n_solve

n.plot()

#%% 3

#check general characteristics of the solved file

#checks the amount of timesteps in the model
len(n.snapshots)

#prints the list of componentes in the file
for c in n.iterate_components(list(n.components.keys())[2:]):
    print("Component '{}' has {} entries".format(c.name, len(c.df)))

#%% 4

#check which global_constraints are being used in the config.yaml file

n.global_constraints


#%% 5

#check generators for the model

n.generators

#print(type(n.generators))
#print(n.generators.columns)

#check generations for only 
idx = ['BO' in x for x in n.generators.index]
n.generators.loc[idx,:]

#check installed capacity by type
gen_cap = n.generators.groupby(["carrier"]).sum()

#check installed capacity by bus and carrier
n.generators.iloc[:, :].groupby(["bus", "carrier"]).p_nom.sum()



#%%

#check demand in the model for a specific period

n.loads_t.p_set.loc["2013-01-01":"2013-01-07","BO 1"].plot()

print(n.loads_t.p_set.sum())

#%%

#check line expansion optimized - nominal

(n.lines.s_nom_opt - n.lines.s_nom)

#%%

#check general statistics

n.statistics()




