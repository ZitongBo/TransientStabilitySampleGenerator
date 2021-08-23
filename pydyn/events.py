#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Events Class
Sets up and handles events in the simulation
"""

import numpy as np
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF

class events:
    def __init__(self, filename):
        self.event_stack = []
        self.parser(filename) 
            
    def parser(self, filename):
        """
        Parse an event file (*.evnt) and populate event stack
        """
        f = open(filename, 'r')
        
        for line in f:
            if line[0] != '#' and line.strip() != '':   # Ignore comments and blank lines
                tokens = line.strip().split(',')
                
                # Parse signal events
                if tokens[1].strip() in ['SIGNAL', 'BUS_FAULT', 'LOAD', 'STATE']:
                    self.event_stack.append([float(tokens[0].strip()), tokens[1].strip(), tokens[2].strip(), tokens[3].strip(), tokens[4].strip()])

                elif tokens[1].strip() in ['BRANCH_FAULT']:
                    self.event_stack.append([float(tokens[0].strip(),),tokens[1].strip(), tokens[2].strip(), tokens[3].strip(), tokens[4].strip(),tokens[5].strip()])

                elif tokens[1].strip() in ['CLEAR_BUS_FAULT', 'CLEAR_BRANCH_FAULT', 'TRIP_BRANCH']:
                    self.event_stack.append([float(tokens[0].strip()), tokens[1].strip(), tokens[2].strip()])
                    
        f.close()
        
    def handle_events(self, t, elements, ppc, baseMVA, flag):
        """
        Checks and handles the event stack during a simulation time step
        """
        refactorise = False
        
        if self.event_stack:
            if self.event_stack[0][0] < t:
                print('Event missed at t=' + str(self.event_stack[0][0]) + 's... Check simulation time step!')
                del self.event_stack[0]
            
            # Event exists at time step
            while self.event_stack and self.event_stack[0][0] == t:
                event_type = self.event_stack[0][1]
                
                # Handle signal events
                if event_type == 'SIGNAL':
                    obj_id = self.event_stack[0][2]
                    sig_id = self.event_stack[0][3]
                    value = float(self.event_stack[0][4])
                    elements[obj_id].signals[sig_id] = value
                    
                    print('SIGNAL event at t=' + str(t) + 's on element "' + obj_id + '". ' + sig_id + ' = ' + str(value) + '.')
                
                if event_type == 'STATE':
                    obj_id = self.event_stack[0][2]
                    sig_id = self.event_stack[0][3]
                    value = float(self.event_stack[0][4])
                    elements[obj_id].states[sig_id] = value
                    
                    print('STATE event at t=' + str(t) + 's on element "' + obj_id + '". ' + sig_id + ' = ' + str(value) + '.')

                if event_type == 'BRANCH_FAULT':
                    branch_id = int(self.event_stack[0][2])
                    Rf = float(self.event_stack[0][3])
                    Xf = float(self.event_stack[0][4])
                    location = float(self.event_stack[0][5])
                    # print(ppc["branch"])
                    # print(len(ppc["bus"]))
                    branch = ppc["branch"][branch_id]

                    ppc["branch"] = np.delete(ppc["branch"], branch_id, 0)
                    # fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
                    new_bus_id = int(len(ppc["bus"])+1)
                    separated_branch1 = [branch[0], new_bus_id, branch[2]*location, branch[3]*location, branch[4]*location, branch[5], branch[6], branch[7], branch[8], branch[9], branch[10], branch[11], branch[12]]
                    separated_branch2 = [new_bus_id, branch[1], branch[2] * (1-location), branch[3] * (1-location),
                                         branch[4]*(1-location), branch[5], branch[6], branch[7], branch[8], branch[9], branch[10], branch[11], branch[12]]
                    from_bus = ppc["bus"][int(branch[0]-1)]
                    to_bus = ppc["bus"][int(branch[1]-1)]
                    voltage_difference = complex(from_bus[VM], from_bus[VA]) - complex(to_bus[VM], to_bus[VA])
                    voltage = voltage_difference * location + complex(to_bus[VM], to_bus[VA])

                    intermediate_bus = [new_bus_id, 1, 0, 0, 0, 0, 1, 1, 0, 345, 1, 1.06, 0.94]
                    intermediate_bus[7] = np.sqrt(voltage.real ** 2 + voltage.imag ** 2)
                    intermediate_bus[8] = np.arctan(voltage.imag/voltage.real) * 180 / np.pi

                    if Rf == 0:
                        intermediate_bus[GS] = 1e6
                    elif Rf < 0:
                        intermediate_bus[GS] = 0
                        Rf = 'Inf'
                    else:
                        intermediate_bus[GS] = 1 / Rf * baseMVA

                    if Xf == 0:
                        intermediate_bus[BS] = -1e6
                    elif Xf < 0:
                        intermediate_bus[BS] = 0
                        Xf = 'Inf'
                    else:
                        intermediate_bus[BS] = -1 / Xf * baseMVA
                    ppc["fault"].append([branch_id, len(ppc["branch"]), len(ppc["bus"])])
                    ppc["branch"] = np.insert(ppc["branch"], branch_id, [separated_branch1], axis=0)
                    ppc["branch"] = np.append(ppc["branch"], [separated_branch2], axis=0)

                    ppc["bus"] = np.append(ppc["bus"], [intermediate_bus], axis=0)
                    refactorise = True
                    print('FAULT event at t=' + str(t) + 's on branch at row "' + str(
                        branch_id) + '" with fault impedance Zf = ' + str(Rf) + ' + j' + str(Xf) + ' pu.')

                if event_type == 'BUS_FAULT':
                    bus_id = int(self.event_stack[0][2])
                    Rf = float(self.event_stack[0][3])
                    Xf = float(self.event_stack[0][4])
                    
                    if Rf == 0:
                        ppc["bus"][bus_id, GS] = 1e6
                    elif Rf < 0:
                        ppc["bus"][bus_id, GS] = 0
                        Rf = 'Inf'
                    else:
                        ppc["bus"][bus_id, GS] = 1 / Rf * baseMVA
                    
                    if Xf == 0:
                        ppc["bus"][bus_id, BS] = -1e6
                    elif Xf < 0:
                        ppc["bus"][bus_id, BS] = 0
                        Xf = 'Inf'
                    else:
                        ppc["bus"][bus_id, BS] = -1 / Xf * baseMVA

                    refactorise = True

                    print('FAULT event at t=' + str(t) + 's on bus at row "' + str(bus_id) + '" with fault impedance Zf = ' + str(Rf) + ' + j' + str(Xf) + ' pu.')
                
                if event_type == 'CLEAR_BUS_FAULT':
                    bus_id = int(self.event_stack[0][2])
                    ppc["bus"][bus_id, BS] = 0
                    ppc["bus"][bus_id, GS] = 0

                    refactorise = True
                    
                    print('CLEAR_FAULT event at t=' + str(t) + 's on bus at row "' + str(int(self.event_stack[0][2])) + '".')

                if event_type == 'CLEAR_BRANCH_FAULT':
                    if flag:
                        ppc["branch"] = np.insert(ppc["branch"], flag[1], flag[0],axis=0)
                        flag=None
                    else:
                        for f in ppc["fault"]:
                            if int(self.event_stack[0][2]) == f[0]:
                                ppc["bus"][f[2], BS] = 0
                                ppc["bus"][f[2], GS] = 0
                                print('CLEAR_FAULT event at t=' + str(t) + 's on branch at row "' + str(
                                    int(self.event_stack[0][2])) + '".')
                    refactorise = True

                if event_type == 'TRIP_BRANCH':
                    branch_id = int(self.event_stack[0][2])
                    if len(ppc["branch"]) != ppc["number_branch"]:
                        ppc["branch"] = np.delete(ppc["branch"], -1, 0)
                        ppc["branch"] = np.delete(ppc["branch"], -1, 0)
                        ppc["bus"] = np.delete(ppc["bus"],-1, 0)

                    else:
                        ppc["branch"] = np.delete(ppc["branch"],branch_id, 0)
                    refactorise = True
                    flag = [ppc["branch"][branch_id], branch_id]
                    
                    print('TRIP_BRANCH event at t=' + str(t) + 's on branch "' + str(branch_id) + '".')
                
                if event_type == 'LOAD':
                    bus_id = int(self.event_stack[0][2])
                    Pl = float(self.event_stack[0][3])
                    Ql = float(self.event_stack[0][4])
                    
                    ppc["bus"][bus_id, PD] = Pl
                    ppc["bus"][bus_id, QD] = Ql
                    
                    refactorise = True
                    
                    print('LOAD event at t=' + str(t) + 's on bus at row "' + str(bus_id) + '" with S = ' + str(Pl) + ' MW + j' + str(Ql) + ' MVAr.')
                    
                del self.event_stack[0]
                
        return ppc, refactorise, flag

def complex(VM, VA):
    return VM*np.cos(VA/180*np.pi) + 1j *VM * np.sin(VA/180*np.pi)

