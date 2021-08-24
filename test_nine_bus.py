#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Nine-Bus Network Stability Test

"""
# Dynamic model classes
from pydyn.controller import controller
from pydyn.sym_order4 import sym_order4
from pydyn.sym_order4 import sym_order4
from pydyn.sym_order4 import sym_order4
from pydyn.ext_grid import ext_grid

# Simulation modules
from pydyn.events import events
from pydyn.recorder import recorder
from pydyn.run_sim import run_sim

# External modules
from pypower.loadcase import loadcase
import matplotlib.pyplot as plt
import numpy as np
    
if __name__ == '__main__':
    
    #########
    # SETUP #
    #########
    
    print('---------------------------------------')
    print('PYPOWER-Dynamics - 9 Bus Stability Test')
    print('---------------------------------------')

    # Load PYPOWER case
    ppc = loadcase('case39.py')
    
    # Program options
    dynopt = {}
    dynopt['h'] = 1e-2               # step length (s)
    dynopt['t_sim'] = 5.0             # simulation time (s)
    dynopt['max_err'] = 1e-4       # Maximum error in network iteration (voltage mismatches)
    dynopt['max_iter'] = 100         # Maximum number of network iterations
    dynopt['verbose'] = False       # option for verbose messages
    dynopt['fn'] = 60                 # Nominal system frequency (Hz)
    dynopt['speed_volt'] = True    # Speed-voltage term option (for current injection calculation)
    
    # Integrator option
    dynopt['iopt'] = 'mod_euler'
    dynopt['iopt'] = 'runge_kutta'
          
    # Create dynamic model objects
    G1 = sym_order4('generator/G1.mach', dynopt)
    G2 = sym_order4('generator/G2.mach', dynopt)
    G3 = sym_order4('generator/G3.mach', dynopt)
    G4 = sym_order4('generator/G4.mach', dynopt)
    G5 = sym_order4('generator/G5.mach', dynopt)
    G6 = sym_order4('generator/G6.mach', dynopt)
    G7 = sym_order4('generator/G7.mach', dynopt)
    G8 = sym_order4('generator/G8.mach', dynopt)
    G9 = sym_order4('generator/G9.mach', dynopt)
    G10 = sym_order4('generator/G10.mach', dynopt)
    # G1 = ext_grid('GEN1', 0, 0.0608, 23.64, dynopt)
    # G2 = ext_grid('GEN2', 1, 0.1198, 6.01, dynopt)
    # G3 = ext_grid('GEN3', 2, 0.1813, 3.01, dynopt)

    # Create dictionary of elements
    elements = {}
    elements[G1.id] = G1
    elements[G2.id] = G2
    elements[G3.id] = G3
    elements[G4.id] = G4
    elements[G5.id] = G5
    elements[G6.id] = G6
    elements[G7.id] = G7
    elements[G8.id] = G8
    elements[G9.id] = G9
    elements[G10.id] = G10

    #elements[oCtrl.id] = oCtrl
    
    # Create event stack
    oEvents = events('events.evnt')
    
    # Create recorder object
    oRecord = recorder('recorder.rcd', ppc)
    
    # Run simulation
    oRecord = run_sim(ppc,elements,dynopt,oEvents,oRecord)
    
    # Plot variables
    baseline = np.array(oRecord.results["GEN:delta"+str(1)])*180/np.pi
    for i in range(len(elements)-1):
        plt.plot(oRecord.t_axis, np.array(oRecord.results["GEN:delta"+str(i+2)])*180/np.pi-baseline)
    # plt.plot(oRecord.t_axis,rel_delta1 * 180 / np.pi, 'r-', oRecord.t_axis, rel_delta2 *180 / np.pi, 'b-')
    # plt.plot(oRecord.t_axis, oRecord.results['GEN1:omega'])
    plt.xlabel('Time (s)')
    # plt.ylim((30,80))
    plt.ylabel('Rotor Angles ')
    plt.show()
    
    # Write recorded variables to output file
    # oRecord.write_output('output.csv')