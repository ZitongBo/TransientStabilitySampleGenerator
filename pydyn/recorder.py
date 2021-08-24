#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Recorder Class
Sets up and manages the recording of signals and variables during the simulation
"""

class recorder:
    def __init__(self, filename, ppc):
        self.recordset = []
        self.results = {}
        self.t_axis = []         
        self.ppc = ppc
        self.parser(filename)
        
        for line in self.recordset:
            self.results[line[0]] = []   
            
    def parser(self, filename):
        """
        Parse a recorder file (*.rcd) and populate recordset list
        """
        f = open(filename, 'r')
        
        for line in f:
            if line[0] != '#' and line.strip() != '':   # Ignore comments and blank lines
                tokens = line.strip().split(',')
                if tokens[1].strip() == 'GEN':
                    for i in range(self.ppc["number_gen"]):
                        self.recordset.append(
                            [tokens[0].strip()+str(i+1), tokens[1].strip(), str(i+1), tokens[2].strip(), tokens[3].strip()])
                elif tokens[1].strip() == "BUS":
                    for i in range(self.ppc["number_bus"]):
                        self.recordset.append(
                            [tokens[0].strip()+str(i), tokens[1].strip(), str(i), tokens[2].strip()])
                elif tokens[1].strip() == "BRAN":
                    for i in range(self.ppc["number_branch"]):
                        self.recordset.append(
                            [tokens[0].strip() + str(i), tokens[1].strip(), str(i), tokens[2].strip()])
                elif tokens[1].strip() == "LOAD":
                    for i in range(self.ppc["number_load"]):
                        self.recordset.append(
                            [tokens[0].strip() + str(i), tokens[1].strip(), str(i), tokens[2].strip()])

        f.close()

    def time_step(self, t):
        """
        Records time step
        """
        self.t_axis.append(t)

    def record_gen(self, elements):
        """
        Records generator variables during a simulation
        """
        for line in self.recordset:
            if line[1] == 'GEN':
                if line[4] == 'SIGNAL':
                    self.results[line[0]].append(elements[line[1]+line[2]].signals[line[3]])
                elif line[4] == 'STATE':
                    self.results[line[0]].append(elements[line[1]+line[2]].states[line[3]])

    def record_bus(self, v):
        """
        Records bus variables during a simulation
        """
        for line in self.recordset:
            if line[1] == 'BUS':
                if line[3] == "U":
                    self.results[line[0]].append(v[int(line[2])][0])
                elif line[3] == "A":
                    self.results[line[0]].append(v[int(line[2])][1])

    def record_bran(self, v):
        """
        Records branch variables during a simulation
        """
        for line in self.recordset:
            if line[1] == 'BRAN':
                if line[3] == "Pf":
                    self.results[line[0]].append(v[int(line[2])][13])
                elif line[3] == "Qf":
                    self.results[line[0]].append(v[int(line[2])][14])
                elif line[3] == "Pt":
                    self.results[line[0]].append(v[int(line[2])][15])
                elif line[3] == "Qt":
                    self.results[line[0]].append(v[int(line[2])][16])

    def record_load(self, v):
        """
        Records load variables during a simulation
        """
        for line in self.recordset:
            if line[1] == 'LOAD':
                if line[3] == "P":
                    self.results[line[0]].append(v[int(line[2])][0])
                elif line[3] == "Q":
                    self.results[line[0]].append(v[int(line[2])][1])

    def write_output(self, filename=None):
        """
        Write recorded variables to file
        (This method could be written in a more pythonic way...)
        """
        if filename != None:
            header = 'time'
            for line in self.recordset:
                header = header + ',' + line[0]
            
            f = open(filename, 'w')
            f.write(header + '\n')
            
            for i in range(len(self.t_axis)):
                newline = str(self.t_axis[i])
                for line in self.recordset:
                    newline = newline + ',' + str(self.results[line[0]][i])
                
                f.write(newline + '\n')
                
            f.close()
        else:
            print('No output file selected...')