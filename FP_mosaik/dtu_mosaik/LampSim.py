# -*- coding: utf-8 -*-
"""
Created on Mon Nov 19 11:41:09 2018

@author: Sylvain
"""

"""Simulator for the Lamps"""

import mosaik_api
import os
import pandas as pd
from itertools import count
from dtu_mosaik.my_models import lamp
#from my_models import lamp
META =  {
    'models': {
        'LampControl': {
            'public': True,
            'params': [ 'Pmax'],
            'attrs': ['broken', 'state', 'Pmax', 'on', 'progressive'],
        },
    },
}
        

MY_DIR = os.path.abspath(os.path.dirname(__file__))

class LampControl(mosaik_api.Simulator):
    def __init__(self, META=META):
        super().__init__(META)

        # Per-entity dicts
        self.eid_counters = {}
        self.simulators = {}
        self.entityparams = {}
        
    def init(self, sid, eid_prefix="LC", storefilename=None):
        self.eid_prefix = eid_prefix
        if storefilename is None:
            # Load default signal store
            self.storefilename = os.path.join(MY_DIR, 'signals.h5')
        else:
            self.storefilename = storefilename
            self.store = pd.HDFStore(self.storefilename)
            self.store.close()
        return self.meta
    
    def create(self, num, model, Pmax=0):
        counter = self.eid_counters.setdefault(model, count())
        entities = []

        #self.store.open()
        #series = self.store[series_name]
        #self.store.close()
        #if not phase == 0:
        #    series.values = roll(series.values, phase)
        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = lamp(Pmax)
            self.simulators[eid] = esim

            entities.append({'eid': eid, 'type': model})

        return entities
    
    def step(self, time, inputs):
        for eid, esim in self.simulators.items():
#            data = inputs.get(eid, {})
#            for attr, incoming in data.items():
#                if attr == 'delta':
#                    new_delta = sum(incoming.values())
#                    self.entityparams[eid].delta = new_delta
            esim.step()
        if esim.is_on() == True:
            if esim.is_progressive() == True:
                while esim.get_state()!=100:
                    esim.progressive_light()
            else:
                esim.light_on()
        else:
            esim.light_off()
            
        return time + 1
    
    def get_data(self, outputs):
        data = {}
        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr not in self.meta['models']['LampControl']['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                if attr == 'broken':
                    mydata[attr] = esim.is_broken()
                if attr == 'state':
                    mydata[attr] = esim.state()
                if attr == 'Pmax':
                    mydata[attr] = esim.get_Pmax()
                if attr == 'on':
                    mydata[attr] = esim.is_on()
                if attr == 'progressive':
                    mydata[attr] = esim.is_progressive()
            data[eid] = mydata
        return data



if __name__ == '__main__':
    # mosaik_api.start_simulation(PVSim())

    test = LampControl()
    
    
    
    
    
    
    
    
    