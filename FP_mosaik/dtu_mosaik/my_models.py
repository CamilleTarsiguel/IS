#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 15 16:54:30 2018

@author: CamilleT
"""

""" This is where we implement our own models"""
import numpy as np

class clock:
    def __init__(self, init_val = 0):
        self.val = init_val
        self.delta = 1
    
    def step(self):
        self.val = self.val + self.delta
        
    def get_val(self):
        return self.val
    
    def get_delta(self):
        return self.delta


        
class coffee_machine:
    def __init__(self, init_bean_level = 100, init_time = 5*60):
        #self.state = 'on'
        self.broken = False
        self.bean_level = init_bean_level # percentage
        self.working_time = init_time # time to prepare coffee. default :  5 minutes
        self.on = False
        self.cpt = 0
    
    def step(self):
        r = np.random.randint(0,1000, 1)
        self.broken = r>999
    
    def machine_on(self):
        self.on = True
        
    def machine_off(self):
        self.on = False
    
    def prep_coffee(self):
        self.on = True
        self.cpt += 1
          
    def use_beans(self):
        self.bean_level -= 10
    
    def get_beans(self):
        return self.bean_level
    
    def is_broken(self):
        return self.broken
    
    def get_time(self):
        return self.working_time
    
    def get_count(self):
        return self.cpt
    
    def is_on(self):
        return(self.on)
        

class sound_machine:
    pass

class lamp:
    
    def __init__(self, Pmax = 0): # change value for default Pmax
        self.broken = False
        self.state = 0 # percentage
        self.Pmax = Pmax
        self.on = False
        self.progressive = False
        
        
    def step(self):    
        r = np.random.randint(0,1000, 1)
        self.broken = r<999
        
    def light_on(self):
        if self.state != 100:
            self.state = 100
        
    def light_off(self):
        if self.state != 0:
            self.state = 0
            
    def progressive_light(self, rate=1):
        self.state = self.state + rate*10
    
    def get_state(self):
        return self.state
    
    def is_broken(self):
        return self.broken
    
    def get_light_power(self):
        return self.state*self.Pmax

    def get_Pmax(self):
        return self.Pmax
    
    def is_on(self):
        return(self.on)
    
    def is_progressive(self):
        return(self.progressive)
        

class curtain: 
    pass