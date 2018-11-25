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
        'Control': {
            'public': True,
            'params': [
                'setpoint_change_rate', # Damping factor
                'T_min', # Minimal comfortable temperature [deg C]
                'T_max', # Maximal comfortable temperature [deg C]
                'P_max', # Heater maximal power [kW]        
                'batt_storage_capacity', 
                'rated_discharge_capacity',
                'rated_charge_capacity'                
            ],             
            'attrs': [
                'Pgrid', # Input: Grid exchange [kW]
                'T', # Input: House temperature [deg C]
                'zs', # Input: current sunshine (in kW heat)
                'SOC', # Input: current charge level of battery [0,1]
                'Pset_heat', # Output: Setpoint for heater [kW]  
                'Pset_batt' # Output: Setpoint for battery [kW]
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

class Control(mosaik_api.Simulator):

    
    class ControlEngine(KnowledgeEngine):
        def __init__(self):
            super().__init__()
            self.returnv={}
        
        #### RULES TO MODIFY ####

        ## Input processing rules
        @Rule(Input(T=MATCH.T,
                   T_max=MATCH.Tmax,
                   T_min=MATCH.Tmin,
                   heating=True),
              TEST(lambda T,Tmax, Tmin : T >= Tmin + 0.1), #Tmax - (Tmax-Tmin)/2),
              salience=5)        
        def _high_temp(self):
            self.declare(State(heating = False))

        @Rule(Input(T=MATCH.T,
                   T_min=MATCH.Tmin,
                   T_max = MATCH.Tmax,
                   heating=False,
                   P_max=MATCH.Pmax),
              TEST(lambda T,Tmin, Tmax : T < Tmin+0.1),#Tmin + (Tmax-Tmin)/2),
              salience=5)       
        def _low_temp(self):
            self.declare(State(heating = True))

        @Rule(Input(SOC=MATCH.soc),
              TEST(lambda soc : soc < 0.9 and soc > 0.1),
              salience=5)       
        def _SOCok(self,soc):
            self.declare(State(SOCok= True, SOC=soc))

        @Rule(Input(SOC=MATCH.soc),
              TEST(lambda soc : soc >= 0.9 or soc <= 0.1),
              salience=5)       
        def _SOCbad(self, soc):
            self.declare(State(SOCok= False, SOC=soc))

        ## Decision processing rules
        @Rule(Input(P_max=MATCH.Pmax, Pset_heat = MATCH.Pset),
              State(heating=True),
              salience=3)
        def _heating1(self,Pmax, Pset):
            self.declare(Output(newPset_heat = -0.1*Pmax + (1-0.1)*Pset , heating=True))

        @Rule(State(heating=False),
              salience=3)
        def _heating2(self):
            self.declare(Output(newPset_heat = 0.0, heating=False))

        @Rule(Input(heating=True,
                   P_max=MATCH.Pmax, Pset_heat = MATCH.Pset),
              NOT(State(heating=W())),
              salience=3)
        def _heating3(self,Pmax, Pset):
            self.declare(Output(newPset_heat = -0.7*Pmax + (1-0.7)*Pset,heating=True))

        @Rule(State(SOCok=True), Input(Pgrid = MATCH.P_grid), 
              TEST(lambda P_grid : P_grid <= 0),
              salience=4)
        def _socokout(self):
            self.declare(Output(newPset_batt = -0.5))  # ADAPT this
            #print("charging battery")
        
        @Rule(State(SOCok=True), Input(Pgrid = MATCH.P_grid, P_max = MATCH.Pmax, SOC = MATCH.soc), 
              TEST(lambda P_grid :P_grid > 0), TEST(lambda soc : soc >0.2),
              salience=3)
        def _socokout1(self, Pmax):
            self.declare(Output(newPset_batt = 0.4))  # ADAPT this
           # print("discharging battery")
            

        @Rule(State(SOCok=False),
              salience=3)
        def _socbadout(self):
            self.declare(Output(newPset_batt = -0))  # this is the default

        @Rule(Input(heating=False),
              NOT(State(heating=W())),
              salience=3)
        def _heating4(self):
            self.declare(Output(newPset_heat = 0.0,heating=False))
            
        #@Rule(Input(zs = MATCH.ZS), TEST(lambda ZS: ZS>-0.01 ))
        #def _too_much_sun(self):
        #    self.declare(Output(newPset_heat = 0.0,heating=False))

        # rule to return values last
        @Rule(AS.out << Output(),              
              salience=0) # 
        def _returnoutputs(self,out):
            self.returnv.update(**out.retrieve())
            #print("generated this output: " +str(out.retrieve()))  

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

    def init(self, sid, step_size=5, eid_prefix="ControlE", verbose=False):
        self.step_size = step_size
        self.eid_prefix = eid_prefix
        self.verbose = verbose
        return self.meta

    def create(
            self, num, model,
            setpoint_change_rate=0.80,
            T_min=19,
            T_max=24,
            P_max=5,
            batt_storage_capacity=10, 
            rated_discharge_capacity=5,
            rated_charge_capacity=5):
        counter = self.eid_counters.setdefault(model, count())
        entities = []


        for _ in range(num):
            eid = '%s_%s' % (self.eid_prefix, next(counter))

            esim = {
                    'Pset_heat': 0,
                    'Pset_batt': 0,
                    'newPset_batt': 0,
                    'Pgrid': 0,
                    'rate': setpoint_change_rate, # update rate of controller
                    'T': 22,
                    'T_min': T_min,
                    'T_max': T_max,
                    'P_max': P_max,
                    'heating': False,
                    'SOC' : 0.5,
                    'P_disc_batt': rated_discharge_capacity,
                    'P_char_batt': rated_charge_capacity                
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
                if attr == 'Pgrid':
                    # If multiple sources send a measurement,
                    # use the mean
                    esim['Pgrid'] = mean(incoming.values())
                elif attr == 'T':
                    esim['T'] = mean(incoming.values())
                elif attr == 'SOC':
                    esim['SOC'] = mean(incoming.values())
                elif attr == 'zs':
                    esim['zs'] = mean(incoming.values())
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
            newPset = esim['newPset_heat'] 
            r = esim['rate']
            Pset = esim['Pset_heat']
            Pset = r*newPset + (1-r)*Pset
            esim['Pset_heat'] = Pset
            
            #low-pass filter on setpoint update: then same filter on  battery power
            newPset = esim['newPset_batt'] 
            Pset = esim['Pset_batt']
            Pset = r*newPset + (1-r)*Pset
            esim['Pset_batt'] = Pset

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, esim in self.simulators.items():
            requests = outputs.get(eid, [])
            mydata = {}
            for attr in requests:
                if attr == 'Pgrid':
                    mydata[attr] = esim['Pgrid']
                elif attr == 'Pset_heat':
                    mydata[attr] = esim['Pset_heat']
                elif attr == 'Pset_batt':
                    mydata[attr] = esim['Pset_batt']
                elif attr == 'T':
                    mydata[attr] = esim['T']
                else:
                    raise RuntimeError("Control {0} has no attribute {1}.".format(eid, attr))
            data[eid] = mydata
        return data

if __name__ == '__main__':
    # mosaik_api.start_simulation(ControlSim())
    testengine = Control.ControlEngine()
    testengine.reset()
    
    #### CHANGE '_in' DICTIONARY TO TEST DIFFERENT SCENARIOS ####
    _in = {'Pset_heat': 3.3,
           'Pset_batt': 3.3,
           'newPset_batt': 0,
           'Pgrid': -10,
           'rate': 0.5,
           'T': 22,
           'T_min': 18,
           'T_max': 24,
           'P_max': 5,
           'heating': False,
           'SOC' : 0.5,
           'P_disc_batt': 5,
           'P_char_batt': 5                
          }
    testengine.declare(Input(**_in))
    print_engine(testengine)
    #%%
    testengine.run()
    import json
    print(json.dumps(testengine.returnv, indent=4, sort_keys=False))
    #testengine.get_return('PSet_batt')
    print_engine(testengine)

