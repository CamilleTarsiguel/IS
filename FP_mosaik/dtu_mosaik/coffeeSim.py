#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simulator for the coffee machine"""

import mosaik_api
import os
import pandas as pd
from itertools import count
from dtu_mosaik.my_models import coffee_machine

META =  {
    'models': {
        'CoffeeMachine': {
            'public': True,
            'params': [ 'init_bean_level', 'init_time'],
            'attrs': ['broken', 'bean_level', 'working_time', 'on', 'cpt' , 'turn_on'],
        },
    },
}




MY_DIR = os.path.abspath(os.path.dirname(__file__))

class CoffeeMachine(mosaik_api.Simulator):
    def __init__(self, META=META):
        super().__init__(META)

        # Per-entity dicts
        self.eid_counters = {}
        self.simulators = {}
        self.entityparams = {}

    def init(self, sid, eid_prefix="CM", storefilename=None):
        self.eid_prefix = eid_prefix
        if storefilename is None:
            # Load default signal store
            self.storefilename = os.path.join(MY_DIR, 'signals.h5')
        else:
            self.storefilename = storefilename
        self.store = pd.HDFStore(self.storefilename)
        self.store.close()
        return self.meta

    def create(self, num, model, init_time = 5*60, init_bean_level = 100):
        counter = self.eid_counters.setdefault(model, count())
        entities = []

        #self.store.open()
        #series = self.store[series_name]
        #self.store.close()
        #if not phase == 0:
        #    series.values = roll(series.values, phase)
        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = coffee_machine(init_bean_level, init_time)
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
                if attr == 'turn_on':
                    turn_on = sum(incoming.values())
#                    self.entityparams[eid].delta = new_delta
            esim.step()
            if turn_on == True:
                esim.machine_on()
            if esim.is_on() == True:
                esim.prep_coffee()
            if esim.get_count()>=esim.get_time():
                esim.machine_off() 
                esim.use_beans()
                print('Coffee is ready')
                esim.reset_count()
                print(esim.is_on())
        return time + 60
    

    def get_data(self, outputs):
        data = {}
        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr not in self.meta['models']['CoffeeMachine']['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)
                if attr == 'broken':
                    mydata[attr] = esim.is_broken()
                if attr == 'bean_level':
                    mydata[attr] = esim.get_beans()
                if attr == 'working_time':
                    mydata[attr] = esim.get_time()
                if attr == 'on':
                    mydata[attr] = esim.is_on()
                if attr == 'cpt':
                    mydata[attr] = esim.get_count()
            data[eid] = mydata
        return data



if __name__ == '__main__':
    # mosaik_api.start_simulation(PVSim())

    test = CoffeeMachine()