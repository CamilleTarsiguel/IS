#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 16:58:23 2018

@author: CamilleT
"""

"""Simulator for the clock"""

import mosaik_api
import os
import pandas as pd
from itertools import count
from dtu_mosaik.my_models import clock

META =  {
    'models': {
        'ClockModel': {
            'public': True,
            'params': ['init_val'],
            'attrs': ['delta', 'val'],
        },
    },
}




MY_DIR = os.path.abspath(os.path.dirname(__file__))

class ClockModel(mosaik_api.Simulator):
    def __init__(self, META=META):
        super().__init__(META)

        # Per-entity dicts
        self.eid_counters = {}
        self.simulators = {}
        self.entityparams = {}

    def init(self, sid, eid_prefix="Cl", storefilename=None):
        self.eid_prefix = eid_prefix
        if storefilename is None:
            # Load default signal store
            self.storefilename = os.path.join(MY_DIR, 'signals.h5')
        else:
            self.storefilename = storefilename
        self.store = pd.HDFStore(self.storefilename)
        self.store.close()
        return self.meta

    def create(self, num, model, init_val=0):
        counter = self.eid_counters.setdefault(model, count())
        entities = []

        #self.store.open()
        #series = self.store[series_name]
        #self.store.close()
        #if not phase == 0:
        #    series.values = roll(series.values, phase)
        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = clock(init_val)
            self.simulators[eid] = esim

            entities.append({'eid': eid, 'type': model})

        return entities

    ###
    #  Functions used online
    ###

    def step(self, time, inputs):
        for eid, esim in self.simulators.items():
            data = inputs.get(eid, {})
            for attr, incoming in data.items():
                if attr == 'delta':
                    new_delta = sum(incoming.values())
                    self.entityparams[eid].delta = new_delta
            esim.step()

        return time + 60
    

    def get_data(self, outputs):
        data = {}
        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr not in self.meta['models']['ClockModel']['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                if attr == 'val':
                    mydata[attr] = esim.get_val()
                if attr == 'delta':
                    mydata[attr] = esim.get_delta()
            data[eid] = mydata
        return data



if __name__ == '__main__':
    # mosaik_api.start_simulation(PVSim())

    test = ClockModel()