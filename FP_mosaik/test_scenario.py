#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 15:52:32 2018

@author: CamilleT
"""

import pandas as pd
import mosaik
import mosaik.util
import numpy as np
import os
import matplotlib.pyplot as plt

plt.rcParams['figure.figsize'] = [10,5]
data_path = 'temp_files/'

# Dictionary with basic configuration of the simulation
basic_conf = {
    'pv1_scaling':1,
    'controller_change_rate':0.9,
    'climate_conditions':'intermittent',
    'random_weather':False,
    'lower_temp_limit': 18, # Minimum comfortable temperature
    'upper_temp_limit': 22, # Maximum comfortable temperature
    'season':'summer'}

# Scenario name which determines the name of the files we will be saving with the results
scenario_name = 'test_with_clock' # <---- MODIFY FILE NAME HERE

#%% SIMULATION

SIM_CONFIG = {
    'ClockModel': {
        'python': 'dtu_mosaik.clockSim:ClockModel',
    },
    
    'CollectorSim': {
        'python': 'dtu_mosaik.collector:Collector',
    },
    'luminosity': {
        'python': 'dtu_mosaik.lightSim:luminosity'
    },
    'HouseModel': {
        'python': 'dtu_mosaik.mosaik_building:BuildingSim' # Now the house is modeled as house.
    },
    'HeatControl': {
        'python': 'mosaik_pyknow_control_house:Control'
    },
    'CoffeeMachine': {
        'python': 'dtu_mosaik.coffeeSim:CoffeeMachine'
    },
    
    'LampControl': {
        'python': 'dtu_mosaik.LampSim:LampControl'
    },
}

# quick check if filepath exists
directory = os.path.dirname(data_path+scenario_name)
if not os.path.exists(directory):
    os.makedirs(directory)

change_rate = basic_conf['controller_change_rate']

seasonscale = {'summer': 1, 'winter': 3, 'autumn': 2, 'spring':2}


ambient_temperatures = {'summer': 16, 'winter': 3, 'autumn': 10, 'spring':10}
ambient_temperature = ambient_temperatures[basic_conf['season']]

pv1_cap = basic_conf['pv1_scaling']
change_rate = basic_conf['controller_change_rate']
day_type = basic_conf['climate_conditions']
random_weather = basic_conf['random_weather']

seasons = {'summer': 1, 'autumn': 3, 'winter': 5, 'spring': 2}


weather_base = {'cloudy': ['/PV715_20180125', '/PV715_20180126', '/PV715_20180127', '/PV715_20180130'],
                'intermittent': ['/PV715_20180423', '/PV715_20180430', '/PV715_20180820', '/PV715_20180722'],
                'sunny': ['/PV715_20180730', '/PV715_20180728', '/PV715_20180729', '/PV715_20180721']}

if random_weather:
    day = weather_base[day_type][np.random.randint(0, 4)]
else:
    day = weather_base[day_type][0]

def init_entities(
        world,
        T_a=ambient_temperature,
        P_maxH=5,
        control_change_rate=basic_conf['controller_change_rate'],
        T_min=basic_conf['lower_temp_limit'],
        T_max=basic_conf['upper_temp_limit'], pv1_rated_capacity=pv1_cap, init_val = 0, weather=day, 
        filename=data_path+scenario_name):
    sim_dict = {}
    entity_dict = {}
    
    ## Clock
    
    cl_sim = world.start(
            'ClockModel',
            eid_prefix = 'clock_')
    cl_entity_1 = cl_sim.ClockModel(init_val=0)
    
    sim_dict['cl1'] = cl_sim
    entity_dict['cl1'] = cl_entity_1

    ##  Light simulation
    lumin_sim = world.start(
        'luminosity',
        eid_prefix='lumin_',
        step_size=5)
    lumin_entity_1 = lumin_sim.luminosity(
        rated_capacity=1.0,
        series_name='/PV715_20180730')
    
    sim_dict['lumin1'] = lumin_sim
    entity_dict['lumin1'] = lumin_entity_1

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
        )

    sim_dict['control'] = control_sim
    entity_dict['control1'] = control_entity_1
    
    ## Coffee Machine
    cm_sim = world.start(
            'CoffeeMachine',
            eid_prefix = 'cm')
    cm_entity_1 = cm_sim.CoffeeMachine()
    
    sim_dict['cm1'] = cm_sim
    entity_dict['cm1'] = cm_entity_1
    
    ## Lamp Control
    lc_sim = world.start(
            'LampControl',
            eid_prefix = 'lc')
    lc_entity_1 = lc_sim.LampControl()
    
    sim_dict['lc1'] = lc_sim
    entity_dict['lc1'] = lc_entity_1
   
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

# Connect PV "sun" to BuildingSim
world.connect(entity_dict['lumin1'], entity_dict['house1'], ('zs', 'zs'))

# Connect units to controlller
world.connect(entity_dict['lumin1'], entity_dict['control1'], ('zs', 'zs'))
world.connect(entity_dict['house1'], entity_dict['control1'], ('T_int', 'T'))
world.connect(entity_dict['control1'], entity_dict['house1'], ('Pset_heat', 'Pset'), time_shifted=True,
                  initial={'Pset_heat': 0.0})


# Connect to Collector
#world.connect(entity_dict['cl1'], entity_dict['collector'], ('val', 'time[m]'))
world.connect(entity_dict['lumin1'], entity_dict['collector'], ('zs', 'Light power [kwh]'))
world.connect(entity_dict['house1'], entity_dict['collector'], ('P', 'Pheat[kW]'))
world.connect(entity_dict['house1'], entity_dict['collector'], ('T_int', 'HouseTemp[C]'))
#world.connect(entity_dict['cm1'], entity_dict['collector'], ('on', 'State Of Machine'))
#world.connect(entity_dict['cm1'], entity_dict['collector'], ('bean_level', 'Beans level'))
world.connect(entity_dict['lc1'], entity_dict['collector'], ('on', 'State Of Machine'))
world.connect(entity_dict['lc1'], entity_dict['collector'], ('Pmax', 'Pmax'))
world.connect(entity_dict['lc1'], entity_dict['collector'], ('progressive', 'Progressive'))



END = 24*60*60-1 # 24 hours, 1 MosaikTime = 1 second
world.run(END)
## End of simulation

#%% LAST MINUTE CHECK

df = pd.HDFStore('temp_files/test_with_clock_data.h5')['timeseries/simulation']
plt.rcParams['figure.figsize'] = [20,10]
df.plot()
df.describe()