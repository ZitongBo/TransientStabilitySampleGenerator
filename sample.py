import numpy as np
from pydyn.sym_order4 import sym_order4
from pydyn.ext_grid import ext_grid

# Simulation modules
from pydyn.events import events
from pydyn.recorder import recorder
from pydyn.run_sim import run_sim
import copy
# External modules
from pypower.loadcase import loadcase
import matplotlib.pyplot as plt


# generate critical sample
def criticalSample(case, elements, dynopt, fault):
    min_time = 1                                  # min clear time
    max_time = dynopt['t_sim'] / dynopt['h'] / 8  # max clear time
    ppc = copy.deepcopy(case)

    # whether the critical sample exists
    fault['clear_time'] = min_time * dynopt["h"]
    writeEventFile(fault)
    recorder = simulation(ppc, elements, dynopt)
    if TransientStability(recorder) is False:
        print('Can not generate critical sample sample, please adjust the parameters')
        return None

    # dichotomy
    curr_time = round((min_time + max_time) / 2)
    while min_time < max_time - 1:
        fault['clear_time'] = round(curr_time * dynopt["h"], 2)
        writeEventFile(fault)
        dynopt['t_sim'] = round(5+curr_time*dynopt["h"], 2)
        ppc = copy.deepcopy(case)
        recorder = simulation(ppc, elements, dynopt)
        stability = TransientStability(recorder)
        print('切除故障时间:', curr_time, '是否稳定:', stability)
        if stability:
            min_time = curr_time
        else:
            max_time = curr_time
        curr_time = round((min_time + max_time) / 2)
    recorder.write_to_excel('critical sample\\' + fault['type'] + str(fault['object']) + '.xlsx')


# generate transient sample
def transientSample(case, elements, dynopt, fault):
    ppc = case
    writeEventFile(fault)
    recorder = simulation(ppc, elements, dynopt)
    stability = TransientStability(recorder)
    print('切除故障时间', fault['clear_time'] * dynopt['h'], '是否稳定', stability)
    recorder.write_to_excel('transient sample\\'+fault['type'] +str(fault['object'])+'.xlsx')


def simulation(case, elements, dynopt):
    # Create event stack
    oEvents = events('events.evnt')

    # Create recorder object
    oRecord = recorder('recorder.rcd', case)

    # Run simulation
    oRecord = run_sim(case, elements, dynopt, oEvents, oRecord)

    return oRecord


# 暂态稳定判断
def TransientStability(oRecord):
    result = True
    oRecord.plot_relative_angle()
    baseline = np.array(oRecord.results["GEN:delta" + str(1)]) * 180 / np.pi
    for i in range(len(elements) - 1):
        # 相对功角大于180
        if max(abs(np.array(oRecord.results["GEN:delta"+ str(i + 2)]) * 180 / np.pi - baseline)) > 180:
            result = False
    oRecord.stability = result
    return result


def writeEventFile(fault):
    event_file = open('events.evnt', 'w')
    event_file.write('# Event Stack for SMIB test case\n')
    event_file.write('# Event time (s), Event type, Object ID, [Parameters]\n\n')
    fault_str = '0.0, ' + fault['type'] + ', ' + fault['object']
    for i in fault['parameters']:
        fault_str += ', ' + str(i)
    event_file.write(fault_str + '\n')
    clear = str(fault['clear_time']) + ', '
    if fault['type'] == 'BRANCH_FAULT':
        clear += 'CLEAR_BRANCH_FAULT, '
    clear += fault['object']
    event_file.write(clear + '\n')
    event_file.close()


if __name__ == "__main__":
    # Load PYPOWER case

    # Program options
    dynopt = {}
    dynopt['h'] = 1e-2  # step length (s)
    dynopt['t_sim'] = 5.0  # simulation time (s)
    dynopt['max_err'] = 1e-4  # Maximum error in network iteration (voltage mismatches)
    dynopt['max_iter'] = 100  # Maximum number of network iterations
    dynopt['verbose'] = False  # option for verbose messages
    dynopt['fn'] = 60  # Nominal system frequency (Hz)
    dynopt['speed_volt'] = True  # Speed-voltage term option (for current injection calculation)

    # Integrator option
    # dynopt['iopt'] = 'mod_euler'
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

    fault = {}
    fault['type'] = 'BRANCH_FAULT'
    fault['object'] = '1'
    fault['parameters'] = [0, 0, 0.5]
    fault['clear_time'] = 0.3

    case = loadcase('case39.py')
    # transientSample(case, elements, dynopt, fault)
    criticalSample(case, elements, dynopt, fault)