#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 22 14:57:53 2018

@author: CamilleT
"""

"""
    An entity which loads a timeseries of relative PV production and outputs it when asked
"""

import mosaik_api
from itertools import count
from statistics import mean
from pyknow import Fact, MATCH, AS, KnowledgeEngine, Rule, TEST, NOT, W
import json

META = {
    'models': {
        'ManageApp': {
            'public': True,
            'params': [
                    'coffee_time'
                #'T_night',
                #'T_day',
                #'setpoint_change_rate', # Damping factor
                #'T_min', # Minimal comfortable temperature [deg C]
                #'T_max', # Maximal comfortable temperature [deg C]
                #'P_max', # Heater maximal power [kW]        
                #'batt_storage_capacity', 
                #'rated_discharge_capacity',
                #'rated_charge_capacity'                
            ],             
            'attrs': [
                #'coffee_time', #Input
                #'alarm_time', #Input
                #'heating_time',#Input
                #'zs',#Input
                #'T',#Input
                'time',#Input
                #'mode',#Input
                #'song',#Input
                'coffee_on',
                #'Pset_heat',
                

            ]
        },
    },
}

# helper function for PyKnow diagnostics

def print_engine(e):
    print("\nEngine: " + str(e))
    print("    facts: " + str(e.facts))
    print("    rules: " + str(e.get_rules()))
    if len(e.agenda.activations)>0 :
        print("    activations: ("+str(len(e.agenda.activations))+") "+ str([a.__repr__() for a in e.agenda.activations]))
    else : 
        print("    activations: " + "NO_ACTIVATIONS")

class Input(Fact):
    '''accepts any dict of input variables'''
    def retrieve(self):
        return self.as_dict()

class Output(Fact):
    '''accepts any dict of output variables'''
    def retrieve(self):
        return self.as_dict()
    
class State(Fact):
    '''placeholder for internal state - needs to be retained with container class'''
    def retrieve(self):
        return self.as_dict()

class ManageApp(mosaik_api.Simulator):

    
    class ControlEngine(KnowledgeEngine):
        def __init__(self):
            super().__init__()
            self.returnv={}
        
        #### RULES TO MODIFY ####
        
        @Rule(Input(coffee_time=MATCH.coffee_time, time = MATCH.time), NOT(Output(coffee_on = True)),
              TEST(lambda coffee_time, time : coffee_time == time),
              salience=5)        
        def _time_for_coffee(self, time):
            
            self.declare(Output(coffee_on = True))
            print('something happened at %d' %time)

        

        #### RULES FOR COFFEE MACHINE ####
        
        
         # rule to return values last
        @Rule(AS.out << Output(),              
              salience=0) # 
        def _returnoutputs(self,out):
            self.returnv.update(**out.retrieve())
    

        #### END OF RULES ####

        def get_return(self,key):
            return self.returnv.get(key)

        def set_return(self,returnvaluedict):
            self.returnv = returnvaluedict

 
    
    def __init__(self, META=META):
        super().__init__(META)

        # Per-entity dicts
        self.eid_counters = {}
        self.simulators = {}
        self.entityparams = {}
        # for engine:
        self.engine = self.ControlEngine()

    def init(self, sid, step_size=5, eid_prefix="Rules", verbose=False):
        self.step_size = step_size
        self.eid_prefix = eid_prefix
        self.verbose = verbose
        return self.meta

    def create(
            self, num, model, coffee_time):#,
            #setpoint_change_rate=0.80,
            #T_min=19,
            #T_max=24,
            #P_max=5,
            #batt_storage_capacity=10, 
            #rated_discharge_capacity=5,
            #rated_charge_capacity=5):
        counter = self.eid_counters.setdefault(model, count())
        entities = []


        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = {
                    #'Pset_heat': 0,
                    #'Pset_batt': 0,
                    #'newPset_batt': 0,
                    #'Pgrid': 0,
                    #'rate': setpoint_change_rate, # update rate of controller
                    #'T': 22,
                    #'T_min': T_min,
                    #'T_max': T_max,
                    #'P_max': P_max,
                    #'heating': False,
                    #'SOC' : 0.5,
                    #'P_disc_batt': rated_discharge_capacity,
                    #'P_char_batt': rated_charge_capacity 
                    'time' : -1,
                    'coffee_time' : coffee_time,
                    'coffee_on' : False
            }
            self.simulators[eid] = esim
            #self.engine.set_return({})
            entities.append({'eid': eid, 'type': model})

        return entities

    ###
    #  Functions used online
    ###

    def step(self, time, inputs):
        for eid, esim in self.simulators.items():
            # first collect updated inputs
            data = inputs.get(eid, {})
            for attr, incoming in data.items():
                if self.verbose: print("Incoming data:{0}".format(incoming))
                if attr == 'coffee_time':
                    # If multiple sources send a measurement,
                    # use the mean
                    esim['coffee_time'] = mean(incoming.values())
                elif attr == 'coffee_on':
                    esim['coffee_on'] = mean(incoming.values())
                elif attr == 'time':
                    esim['time'] = mean(incoming.values())
                #elif attr == 'zs':
                #    esim['zs'] = mean(incoming.values())
                else:
                    raise RuntimeError("Controller {0} has no input {1}.".format(eid, attr))
                    

            # Calculate new setpoint & heating 
            # --> pass input & state variables (esim) to ControlEngine
            ce = self.engine
            ce.reset()
            ce.declare(Input(**esim))
            ce.returnv={}
            
            ###############################################################
            # Here the decision "if-statements" were moved to PyKnow Engine #         
            ###############################################################
            
            # run the engine with new inputs
            ce.run()

            # update (all results from engine delivered in returnvaluedict)
            esim.update([(key, ce.returnv[key]) for key in ce.returnv.keys()])
            
            #low-pass filter on setpoint update: first on heat
            #newPset = esim['newPset_heat'] 
            #r = esim['rate']
            #Pset = esim['Pset_heat']
            #Pset = r*newPset + (1-r)*Pset
            #esim['Pset_heat'] = Pset
            
            #low-pass filter on setpoint update: then same filter on  battery power
            #newPset = esim['newPset_batt'] 
            #Pset = esim['Pset_batt']
            #Pset = r*newPset + (1-r)*Pset
            #esim['Pset_batt'] = Pset

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr == 'coffee_time':
                    mydata[attr] = esim['coffee_time']
                elif attr == 'coffee_on':
                    mydata[attr] = esim['coffee_on']
                #elif attr == 'Pset_batt':
                #    mydata[attr] = esim['Pset_batt']
                #elif attr == 'T':
                #    mydata[attr] = esim['T']
                else:
                    raise RuntimeError("Control {0} has no attribute {1}.".format(eid, attr))
            data[eid] = mydata
        return data

if __name__ == '__main__':
    # mosaik_api.start_simulation(ControlSim())
    testengine = ManageApp.ControlEngine()
    testengine.reset()
    
    #### CHANGE '_in' DICTIONARY TO TEST DIFFERENT SCENARIOS ####
    _in = {#'Pset_heat': 3.3,
           #'Pset_batt': 3.3,
           #'newPset_batt': 0,
           #'Pgrid': -10,
           #'rate': 0.5,
           #'T': 22,
           #'T_min': 18,
           #'T_max': 24,
           #'P_max': 5,
           #'heating': False,
           #'SOC' : 0.5,
           #'P_disc_batt': 5,
           #'P_char_batt': 5 
            'coffee_time' : 10 ,
            'time': 10              
          }
    testengine.declare(Input(**_in))
    print_engine(testengine)
    #%%
    testengine.run()
    import json
    print(json.dumps(testengine.returnv, indent=4, sort_keys=False))
    #testengine.get_return('PSet_batt')
    print_engine(testengine)

