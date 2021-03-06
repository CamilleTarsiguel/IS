#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 16:28:09 2018

@author: CamilleT
"""

import pandas as pd
import mosaik
import mosaik.util
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = [10,5]
data_path = 'temp_files/'

# Dictionary with basic configuration of the simulation
basic_conf = {
    'batt_storage_capacity':20,
    'batt_charge_capacity':5,
    'pv1_scaling':1,
    'controller_change_rate':0.9,
    'climate_conditions':'intermittent',
    'random_weather':False,
    'lower_temp_limit': 18, # Minimum comfortable temperature
    'upper_temp_limit': 22, # Maximum comfortable temperature
    'season':'summer'}

# Scenario name which determines the name of the files we will be saving with the results
scenario_name = 'summer_MINE' # <---- MODIFY FILE NAME HERE


#%% SIMULATION TIME!

SIM_CONFIG = {
    'DemandModel': {
        'python': 'dtu_mosaik.mosaik_demand:DemandModel',
    },
    'SimpleGridModel': {
        'python': 'dtu_mosaik.mosaik_grid:SimpleGridModel',
    },
    'CollectorSim': {
        'python': 'dtu_mosaik.collector:Collector',
    },
    'PVModel': {
        'python': 'dtu_mosaik.mosaik_pv:PVModel'
    },
    'HouseModel': {
        'python': 'dtu_mosaik.mosaik_building:BuildingSim' # Now the house is modeled as house.
    },
    'HeatControl': {
        'python': 'mosaik_pyknow_control_house:Control'
    },
    'BatteryModel': {
        'python': 'dtu_mosaik.mosaik_battery:BatteryModel'
    },
}

# quick check if filepath exists
directory = os.path.dirname(data_path+scenario_name)
if not os.path.exists(directory):
    os.makedirs(directory)

change_rate = basic_conf['controller_change_rate']

seasonscale = {'summer': 1, 'winter': 3, 'autumn': 2, 'spring':2}
demandscale = seasonscale[basic_conf['season']]

ambient_temperatures = {'summer': 16, 'winter': 3, 'autumn': 10, 'spring':10}
ambient_temperature = ambient_temperatures[basic_conf['season']]

pv1_cap = basic_conf['pv1_scaling']
battery_cap = basic_conf['batt_storage_capacity']
battery_rate = basic_conf['batt_charge_capacity']
change_rate = basic_conf['controller_change_rate']
day_type = basic_conf['climate_conditions']
random_weather = basic_conf['random_weather']

seasons = {'summer': 1, 'autumn': 3, 'winter': 5, 'spring': 2}
demand = seasons[basic_conf['season']]

weather_base = {'cloudy': ['/PV715_20180125', '/PV715_20180126', '/PV715_20180127', '/PV715_20180130'],
                'intermittent': ['/PV715_20180423', '/PV715_20180430', '/PV715_20180820', '/PV715_20180722'],
                'sunny': ['/PV715_20180730', '/PV715_20180728', '/PV715_20180729', '/PV715_20180721']}

if random_weather:
    day = weather_base[day_type][np.random.randint(0, 4)]
else:
    day = weather_base[day_type][0]

def init_entities(
        world,
        demandscale=demandscale,
        T_a=ambient_temperature,
        P_maxH=5,
        control_change_rate=basic_conf['controller_change_rate'],
        T_min=basic_conf['lower_temp_limit'],
        T_max=basic_conf['upper_temp_limit'], pv1_rated_capacity=pv1_cap, batt1_rated_cap=battery_cap,
                  batt1_rate=battery_rate, weather=day, 
        filename=data_path+scenario_name):
    sim_dict = {}
    entity_dict = {}
    

    ## Demand
    demand_sim = world.start(
        'DemandModel',
        eid_prefix='demand_',
        step_size=5)
    demand_entity_1 = demand_sim.DemandModel(rated_capacity=demandscale, seriesname='/flexhouse_20180219')
    sim_dict['demand'] = demand_sim
    entity_dict['demand1'] = demand_entity_1

    ## Grid model
    grid_sim = world.start(
        'SimpleGridModel',
        eid_prefix='grid_',
        step_size=5)
    grid_entity_1 = grid_sim.SimpleGridModel(V0=240, droop=0.1)
    
    sim_dict['grid'] = grid_sim
    entity_dict['grid1'] = grid_entity_1

    ##  PV
    pv_sim = world.start(
        'PVModel',
        eid_prefix='pv_',
        step_size=5)
    pv_entity_1 = pv_sim.PVModel(
        rated_capacity=1.0,
        series_name='/PV715_20180730')
    
    sim_dict['pv1'] = pv_sim
    entity_dict['pv1'] = pv_entity_1

    ## House
    house_sim = world.start(
        'HouseModel',
        eid_prefix='house_',
        step_size=5)
    house_entity_1 = house_sim.BuildingSim(
        init_T_amb=T_a,
        init_T_int=20,
        heater_power= P_maxH,
        heat_coeff=30, 
        solar_heat_coeff=1.10,
        insulation_coeff=0.60
        )
        
    sim_dict['house'] = house_sim
    entity_dict['house1'] = house_entity_1
    
    ## Battery
    batt_sim = world.start(
        'BatteryModel',
        eid_prefix='batt_',
        step_size=5)
    batt_entity_1 = batt_sim.BatteryModel(
        rated_capacity=batt1_rated_cap,
        rated_discharge_capacity=batt1_rate,
        rated_charge_capacity=batt1_rate,
        initial_charge_rel=0.5,
        charge_change_rate=0.90)
        
    sim_dict['batt'] = batt_sim
    entity_dict['batt1'] = batt_entity_1
    
    ## Controller
    control_sim = world.start(
        'HeatControl',
        eid_prefix='heatcontrol_',
        step_size=5)
    control_entity_1 = control_sim.Control(
        setpoint_change_rate=control_change_rate,
        T_min=T_min,
        T_max=T_max,
        P_max=P_maxH,
        batt_storage_capacity=batt1_rated_cap,
        rated_discharge_capacity=batt1_rate,
        rated_charge_capacity=batt1_rate,        
        )

    sim_dict['control'] = control_sim
    entity_dict['control1'] = control_entity_1

    ## Collector
    collector_sim = world.start(
        'CollectorSim',
        step_size=60,
        save_h5=True,
        h5_storename='{}_data.h5'.format(filename),
        h5_framename='timeseries/simulation',
        print_results=False)
    
    collector_entity = collector_sim.Collector()
    
    sim_dict['collector'] = collector_sim
    entity_dict['collector'] = collector_entity
    
    return sim_dict, entity_dict


world = mosaik.World(SIM_CONFIG)
sim_dict, entity_dict = init_entities(world)

# Connect units to grid busbar
world.connect(entity_dict['demand1'], entity_dict['grid1'], ('P', 'P'))
world.connect(entity_dict['pv1'], entity_dict['grid1'], ('P', 'P'))
world.connect(entity_dict['batt1'], entity_dict['grid1'], ('P', 'P'))
world.connect(entity_dict['house1'], entity_dict['grid1'], ('P', 'P'))

# Connect PV "sun" to BuildingSim
world.connect(entity_dict['pv1'], entity_dict['house1'], ('zs', 'zs'))

# Connect units to controlller
world.connect(entity_dict['pv1'], entity_dict['control1'], ('zs', 'zs'))
world.connect(entity_dict['grid1'], entity_dict['control1'], ('Pgrid', 'Pgrid'))
world.connect(entity_dict['house1'], entity_dict['control1'], ('T_int', 'T'))
world.connect(entity_dict['control1'], entity_dict['house1'], ('Pset_heat', 'Pset'), time_shifted=True,
                  initial={'Pset_heat': 0.0})
world.connect(entity_dict['control1'], entity_dict['batt1'], ('Pset_batt', 'Pset'), time_shifted=True,
                  initial={'Pset_batt': 0.0})
world.connect(entity_dict['batt1'], entity_dict['control1'], ('relSoC', 'SOC'))


# Connect to Collector
world.connect(entity_dict['demand1'], entity_dict['collector'], ('P', 'DemP[kW]'))
world.connect(entity_dict['grid1'], entity_dict['collector'], ('Pgrid', 'GridP[kW]'))
world.connect(entity_dict['pv1'], entity_dict['collector'], ('P', 'SolarP[kW]'))
world.connect(entity_dict['house1'], entity_dict['collector'], ('P', 'Pheat[kW]'))
world.connect(entity_dict['house1'], entity_dict['collector'], ('T_int', 'HouseTemp[C]'))
world.connect(entity_dict['batt1'], entity_dict['collector'], ('P', 'BattP[kW]'))
world.connect(entity_dict['batt1'], entity_dict['collector'], ('SoC', 'BattSoC[kWh]'))


END = 24*60*60-1 # 24 hours, 1 MosaikTime = 1 second
world.run(END)
## End of simulation

#%% DISPLAY
df = pd.HDFStore('temp_files/summer_MINE_data.h5')['timeseries/simulation']
plt.rcParams['figure.figsize'] = [20,10]
df.plot(legend=False)
df.describe()