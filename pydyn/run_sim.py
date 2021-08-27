#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Time-domain simulation engine

"""

from pydyn.interface import init_interfaces
from numpy import flatnonzero as find
from pydyn.mod_Ybus import mod_Ybus
from pydyn.version import pydyn_ver
import matplotlib.pyplot as plt
from scipy.sparse.linalg import splu
import numpy as np
from pypower.pfsoln import pfsoln
from pypower.runpf import runpf
from pypower.ext2int import ext2int
from pypower.makeYbus import makeYbus
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF
from pypower.idx_brch import F_BUS, T_BUS, BR_STATUS, PF, PT, QF, QT
from numpy import asarray, angle, pi, conj, zeros, ones, finfo, c_, ix_

def run_sim(ppc, gens, dynopt = None, events = None, recorder = None):
    """
    Run a time-domain simulation
    
    Inputs:
        ppc         PYPOWER load flow case
        gens    Dictionary of dynamic model objects (machines, controllers, etc) with Object ID as key
        events      Events object
        recorder    Recorder object (empty)
    
    Outputs:
        recorder    Recorder object (with data)
    """
    
    #########
    # SETUP #
    #########
    
    # Get version information
    ver = pydyn_ver()
    # print('PYPOWER-Dynamics ' + ver['Version'] + ', ' + ver['Date'])
    
    # Program options
    if dynopt:
        h = dynopt['h']             
        t_sim = dynopt['t_sim']           
        max_err = dynopt['max_err']        
        max_iter = dynopt['max_iter']
        verbose = dynopt['verbose']
    else:
        # Default program options
        h = 0.01                # step length (s)
        t_sim = 5               # simulation time (s)
        max_err = 0.0001        # Maximum error in network iteration (voltage mismatches)
        max_iter = 25           # Maximum number of network iterations
        verbose = False
        
    # Make lists of current injection sources (generators, external grids, etc) and controllers
    sources = []
    controllers = []
    for element in gens.values():
        if element.__module__ in ['pydyn.sym_order6a', 'pydyn.sym_order6b', 'pydyn.sym_order4', 'pydyn.ext_grid', 'pydyn.vsc_average', 'pydyn.asym_1cage', 'pydyn.asym_2cage']:
            sources.append(element)
            
        if element.__module__ == 'pydyn.controller':
            controllers.append(element)
    
    # Set up interfaces
    interfaces = init_interfaces(gens)
    
    ##################
    # INITIALISATION #
    ##################
    # print('Initialising models...')
    
    # Run power flow and update bus voltages and angles in PYPOWER case object
    results, success = runpf(ppc) 
    ppc["bus"][:, VM] = results["bus"][:, VM]
    ppc["bus"][:, VA] = results["bus"][:, VA]

    # Build Ybus matrix
    ppc_int = ext2int(ppc)
    baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]

    Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)
    
    # Build modified Ybus matrix
    Ybus = mod_Ybus(Ybus, gens, bus, ppc_int['gen'], baseMVA)
    
    # Calculate initial voltage phasors
    v0 = bus[:, VM] * (np.cos(np.radians(bus[:, VA])) + 1j * np.sin(np.radians(bus[:, VA])))
    
    # Initialise sources from load flow
    for source in sources:
        if source.__module__ in ['pydyn.asym_1cage', 'pydyn.asym_2cage']:
            # Asynchronous machine
            source_bus = int(ppc_int['bus'][source.bus_no,0])
            v_source = v0[source_bus]
            source.initialise(v_source,0)
        else:
            # Generator or VSC
            source_bus = int(ppc_int['gen'][source.gen_no,0])
            S_source = np.complex(results["gen"][source.gen_no, 1] / baseMVA, results["gen"][source.gen_no, 2] / baseMVA)
            v_source = v0[source_bus]
            source.initialise(v_source,S_source)
    
    # Interface controllers and machines (for initialisation)
    for intf in interfaces:
        int_type = intf[0]
        var_name = intf[1]
        if int_type == 'OUTPUT':
            # If an output, interface in the reverse direction for initialisation
            intf[2].signals[var_name] = intf[3].signals[var_name]
        else:
            # Inputs are interfaced in normal direction during initialisation
            intf[3].signals[var_name] = intf[2].signals[var_name]
    
    # Initialise controllers
    for controller in controllers:
        controller.initialise()
    
    #############
    # MAIN LOOP #
    #############
    t_bus_V = np.zeros((int(t_sim / h) + 1, len(bus), 2))
    if events == None:
        print('Warning: no events!')
    
    # Factorise Ybus matrix
    Ybus_inv = splu(Ybus)
    flag=None
    y1 = []
    v_prev = v0
    print('Simulating...')
    for t in range(int(t_sim / h) + 1):
        # Record state
        elements = {"gen": {}, "bus": {}, "bran": {}, "load": {}}

        if np.mod(t,1/h) == 0:
            print('t=' + str(t*h) + 's')
            
        # Interface controllers and machines
        for intf in interfaces:
            var_name = intf[1]
            intf[3].signals[var_name] = intf[2].signals[var_name]
        
        # Solve differential equations
        for j in range(4):
            # Solve step of differential equations
            for element in gens.values():
                element.solve_step(h,j) 
            v0 = bus[:, VM] * (np.cos(np.radians(bus[:, VA])) + 1j * np.sin(np.radians(bus[:, VA])))
            
            v_prev = solve_network(sources, v_prev, Ybus_inv, ppc_int, len(bus), max_err, max_iter)
        bus_V = np.zeros((len(bus), 2))
        for v in range(len(v_prev)):
            Va = np.arctan(v_prev[v].imag / v_prev[v].real)
            Vm = v_prev[v].real / np.cos(Va)
            bus_V[v][0] = Vm
            bus_V[v][1] = Va
            # t_bus_V[t][v][0] = Vm
            # t_bus_V[t][v][1] = Va
        # results, _ = runpf(ppc)
        # ppc["bus"][:, VM] = results["bus"][:, VM]
        # ppc["bus"][:, VA] = results["bus"][:, VA]
        # Interface with network equations
        # print('Time',t)
        # for i in range(len(bus)):
        #     print('Bus No.',i,' voltage magnitude:',bus_V[i][0],' voltage angle :',bus_V[i][1])
        br = find(branch[:, BR_STATUS]).astype(int)  ## in-service branches
        V = v_prev
        if branch.shape[1] < QT:
            branch = c_[branch,
                               zeros((branch.shape[0],
                                      QT - branch.shape[1] + 1))]

        # complex power at "from" bus
        Sf = V[branch[br, F_BUS].astype(int)] \
             * conj(Yf[br, :] * V) * baseMVA
        # complex power injected at "to" bus
        St = V[branch[br, T_BUS].astype(int)] \
             * conj(Yt[br, :] * V) * baseMVA
        branch[ix_(br, [PF, QF, PT, QT])] = c_[Sf.real, Sf.imag, St.real, St.imag]

        # 故障线路的两部分合二为一
        for f in ppc["fault"]:
            branch[f[0], QT] = branch[-1, QT]
            branch[f[0], QF] = branch[-1, QF]

        if recorder is not None:
            # Record signals or states
            recorder.time_step(t)
            recorder.record_bus(bus_V)
            recorder.record_gen(gens)
            recorder.record_bran(branch)
            recorder.record_load(ppc_int["load"])
        
        if events is not None:
            # Check event stack
            ppc, refactorise, flag = events.handle_events(np.round(t*h,5), gens, ppc, baseMVA,flag)
            
            if refactorise is True:
                # Rebuild Ybus from new ppc_int
                ppc_int = ext2int(ppc)
                baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]
                Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)
                
                # Rebuild modified Ybus
                Ybus = mod_Ybus(Ybus, gens, bus, ppc_int['gen'], baseMVA)

                # Refactorise Ybus
                Ybus_inv = splu(Ybus)

                # Solve network equations
                v_prev = solve_network(sources, v_prev, Ybus_inv, ppc_int, len(bus), max_err, max_iter)

    for i in range(ppc["number_branch"]):
        plt.plot(recorder.t_axis, np.array(recorder.results["BRAN:Qf" + str(i)]))
    plt.xlabel('Time (s)')
    # plt.ylim((30,80))
    plt.ylabel('Qf')
    plt.show()
    # x = np.arange(int(t_sim / h) + 1)
    #
    # for i in range(39):
    #     #    plt.plot(x/100, abs(t_bus_V[:, i, 0]), label='bus '+ str(i))
    #     plt.plot(x / 100, abs(t_bus_V[:, i, 0]),)
    # plt.xlabel("time/s")
    # plt.ylabel("")
    # #plt.legend()
    # plt.show()

    return recorder


def solve_network(sources, v_prev, Ybus_inv, ppc_int, no_buses, max_err, max_iter):
    """
    Solve network equations
    """
    verr = 1
    i = 1
    # Iterate until network voltages in successive iterations are within tolerance
    while verr > max_err and i < max_iter:        
        # Update current injections for sources
        I = np.zeros(no_buses, dtype='complex')
        for source in sources:
            if source.__module__ in ['pydyn.asym_1cage', 'pydyn.asym_2cage']:
                # Asynchronous machine
                source_bus = int(ppc_int['bus'][source.bus_no,0])
            else:
                # Generators or VSC
                source_bus = int(ppc_int['gen'][source.gen_no,0])
                
            I[source_bus] = source.calc_currents(v_prev[source_bus])

        # Solve for network voltages
        vtmp = Ybus_inv.solve(I)
        verr = np.abs(np.dot((vtmp[:39]-v_prev[:39]), np.transpose(vtmp[:39]-v_prev[:39])))
        v_prev = vtmp
        i = i + 1
    
    if i >= max_iter:
        print('Network voltages and current injections did not converge in time step...')
    
    return v_prev