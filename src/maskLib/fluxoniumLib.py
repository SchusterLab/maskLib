# -*- coding: utf-8 -*-
"""
Created on Thu Aug 8 15:11:27 2024

@author: chuyao and paul 
"""
import sys
import os
current_dir = os.getcwd()
file_dir = os.path.dirname(__file__)

import maskLib
from dxfwrite.vector2d import vadd,midpoint,vmul_scalar,vsub
import math
import sys, subprocess, os, time
import numpy as np
from dxfwrite import DXFEngine as dxf
from dxfwrite import const
from dxfwrite.entities import Polyline
import ezdxf

import maskLib.MaskLib as m
import maskLib.microwaveLib as mw
from maskLib.utilities import curveAB
from maskLib.markerLib import AlphaNumStr

from maskLib.markerLib import MarkerSquare, MarkerCross
from maskLib.utilities import doMirrored

def round_sf(value, n):
    """
    Round a value to n significant figures
    
    Args:
        value (float): value to round
        n (int): number of significant figures
    """
    rounded_val = round(value, -int(np.floor(np.log10(abs(value)))) + (n - 1))
    # if rounded_val has >= n digits to the left of the decimal point, return int
    if len(str(rounded_val).split('.')[0]) >= n:
        rounded_val = int(rounded_val)
    return rounded_val

def grid_from_row(row, no_row):
    return [row for _ in range(no_row)]

def grid_from_column(column, no_column, no_row):
    return [[column[i] for _ in range(no_column)] for i in range(no_row)]

def grid_from_entry(entry, no_row, no_column):
    return [entry * np.ones(no_column) for _ in range(no_row)]

def junction_chain(chip, structure, n_junc_array=None, w=None, s=None, gap=None,
                   bgcolor=None, CW=True, finalpiece=True, Jlayer=None,
                   Ulayer=None, **kwargs):
    def struct():
        if isinstance(structure, m.Structure):
            return structure
        elif isinstance(structure, tuple):
            return m.Structure(chip, structure)
        else:
            return chip.structure(structure)

    if w is None:
        try:
            w = struct().defaults['w']
        except KeyError:
            print('\x1b[33mw not defined in ', chip.chipID)
    if s is None:
        try:
            s = struct().defaults['s']
        except KeyError:
            print('\x1b[33ms not defined in ', chip.chipID)
    if bgcolor is None:
        bgcolor = chip.wafer.bg()

    struct().translatePos((0, -s/2))

    # undercut amount = 0.3 approximate
    UNDERCUT = 0.3

    for count, n in enumerate(n_junc_array):
        undercut = struct().clone()
        # undercut on outside of JJ array
        undercut.translatePos((0, s/2), angle=0)

        mw.CPW_straight(chip, undercut, w = s, s = UNDERCUT, length = n*gap + (n-1)*w, 
                        layer = Ulayer, rotation = struct().direction)

        chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        for i in range(n-1):
            chip.add(dxf.rectangle(struct().getPos((0, 0)), w, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Jlayer),
                                   structure=structure, length= w)

            chip.add(dxf.rectangle(struct().getPos((0, 0)), gap, s,
                                   rotation=struct().direction, bgcolor=bgcolor, layer=Ulayer),
                                   structure=structure, length= gap)
        if len(n_junc_array) >= 1:

            if CW:
                if count % 2 == 0:
                    factor = -2
                    direction = -1
                else:
                    factor = 0
                    direction = 3
            else:
                if count % 2 == 0:
                    factor = 0
                    direction = 3
                else:
                    factor = -2
                    direction = -1

            if count + 1 < len(n_junc_array):
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, abs(direction)*s)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((0, factor*s-UNDERCUT)), w + gap + UNDERCUT, UNDERCUT, rotation=struct().direction,
                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s+UNDERCUT)), UNDERCUT, s-2*UNDERCUT, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)

                # undercut.translatePos((0, s/2))
                # chip.add(dxf.rectangle(undercut.getPos((0, 0)), w+gap+UNDERCUT, UNDERCUT,
                #                    rotation=undercut.direction, bgcolor=bgcolor, layer=Ulayer),
                #                    structure=structure, length= gap)

            elif finalpiece:
                chip.add(dxf.rectangle(struct().getPos((0, factor*s)), w + gap, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Jlayer))
                chip.add(dxf.rectangle(struct().getPos((w + gap, factor*s)), UNDERCUT, 3 * s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                chip.add(dxf.rectangle(struct().getPos((-UNDERCUT, (factor+1)*s)), UNDERCUT, s, rotation=struct().direction,
                                        bgcolor=bgcolor, layer=Ulayer))
                struct().translatePos((0, direction * s), angle=180)
    

    struct().translatePos((0, +s/2))

def smallJ(chip, structure, start, j_length, Jlayer, Ulayer, gap=0.14, lead = 1, ubridge_width=0.3, **kwargs):

    x, y = start

    tmp = round(200 * (lead - j_length) / 2) / 200 # rounding to make sure it falls in 5nm grid

    j_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Jlayer)
    j_quad.close()
    chip.add(j_quad)

    # u_quad = dxf.polyline(points=[[x, y], [x+0.5, y-tmp], [x+0.5, y-tmp-j_length], [x, y-lead], [x, y]], bgcolor=chip.wafer.bg(), layer=Ulayer)
    # u_quad.close()
    # chip.add(u_quad)

    structure.translatePos((0.5, - j_length/2), angle=0)

    undercut = structure.clone()
    
    finger_length = 1.36 # specified by LL 
    chip.add(dxf.rectangle(structure.getPos((0, 0)), finger_length, j_length,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Jlayer))
    chip.add(dxf.rectangle(structure.getPos((finger_length, -ubridge_width-lead/2 +j_length/2)), gap, 2*ubridge_width + lead,
                        rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=Ulayer))
    structure.translatePos((finger_length + gap, j_length/2), angle=0)

    # do undercut for U layer 
    undercut.translatePos((-0.5, j_length/2), angle=0)
    mw.CPW_taper(chip, undercut, length=0.5, w1 = j_length, w0 = lead, s0 = ubridge_width, s1 = ubridge_width, layer = Ulayer)
    mw.CPW_straight(chip, undercut, w = j_length, s = ubridge_width, length = finger_length, layer = Ulayer)

# checker_board for resolution tests
def checker_board(chip, structure, start, num, square_size, layer=None):
    x, y = start
    for i in range(num):
        for j in range(num):
            if (i+j) % 2 == 0:
                chip.add(dxf.rectangle(structure.getPos((x + i * square_size, y + j * square_size)), square_size, square_size,
                                       rotation=structure.direction, bgcolor=chip.wafer.bg(), layer=layer))

# clover_leaf for 4-pt_probe measurement
def clover_leaf(chip, structure, start, diameter, layer=None, ptDensity=64, sf=1.05, ground_plane=True):
    x, y = start
    # init polyline
    size = diameter/2

    if ground_plane:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)

        ## first quadrant
        # big circle
        poly.add_vertices(curveAB((x+size/10, y+size), (x+size, y+size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/4, y+size/10), (x+size/4, y-size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB((x+size, y-size/10), (x+size/10, y-size), ptDensity=ptDensity))

        # finish 1st poly object
        poly.add_vertices([(x+size/10, y-sf*size), (x+sf*size, y-sf*size), (x+sf*size, y+sf*size), (x+size/10, y+sf*size)])

        poly.close()

        chip.add(poly)

        # second poly object
        poly = dxf.polyline(points=[(x+size/10, y-size)], bgcolor=chip.wafer.bg(), layer=layer)

        # small circle
        poly.add_vertices(curveAB((x+size/10, y-size/4), (x-size/10, y-size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB((x-size/10, y-size), (x-size, y-size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/4, y-size/10), (x-size/4, y+size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB((x-size, y+size/10), (x-size/10, y+size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/10, y+size/4), (x+size/10, y+size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        # finish 2nd poly object
        poly.add_vertices([(x+size/10, y+sf*size), (x-sf*size, y+sf*size), (x-sf*size, y-sf*size), (x+size/10, y-sf*size)])

        poly.close() 

        chip.add(poly)
    else:
        poly = dxf.polyline(points=[], bgcolor=chip.wafer.bg(), layer=layer)        
        
        ## first quadrant
        # big circle
        poly.add_vertices(curveAB((x+size/10, y+size), (x+size, y+size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/4, y+size/10), (x+size/4, y-size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## second quadrant
        # big circle
        poly.add_vertices(curveAB((x+size, y-size/10), (x+size/10, y-size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x+size/10, y-size/4), (x-size/10, y-size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## third quadrant
        # big circle
        poly.add_vertices(curveAB((x-size/10, y-size), (x-size, y-size/10), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/4, y-size/10), (x-size/4, y+size/10), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        ## fourth quadrant
        # big circle
        poly.add_vertices(curveAB((x-size, y+size/10), (x-size/10, y+size), ptDensity=ptDensity))
        # small circle
        poly.add_vertices(curveAB((x-size/10, y+size/4), (x+size/10, y+size/4), ptDensity=ptDensity, clockwise=False, angleDeg=180))

        poly.close() 

        chip.add(poly)

# create chip which has 10 clover leafs for each metal layer
# also has checkerboard pattern from 0.5um to 50um as [0.5, 1, 2, 4, 8, 16, 32, 50] um, with label on '5_M1' layer
# checkerboard from 0.004 to 2um as [0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2] um, with label on '???' layer

def create_clover_leaf_checkerboard(chip, loc, jlayer='20_SE1', M1_layer="5_M1",
                                    clover_leaf_size=250, spacing=20, 
                                    M1_checkerboard=None, JLayer_checkerboard=None,
                                    do_JClover=False,
                                    JLayer_ch_offset=50, text_size=(40,40),
                                    num_checkers=10):
    # clover leaf
    for i in range(3):
        structure = m.Structure(chip, start = vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, clover_leaf_size/2)))
        clover_leaf(chip, structure, vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, clover_leaf_size/2)), 
                    clover_leaf_size, layer=M1_layer)
    label_struct = m.Structure(chip, start = vadd(loc, (0, (clover_leaf_size + spacing))))
    AlphaNumStr(chip, label_struct, f'{M1_layer}', size=text_size)

    if M1_checkerboard is None:
        M1_checkerboard = [0.5, 1, 2, 4, 8, 16]
    # checkerboard Metal
    for i, size in enumerate(M1_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in M1_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1])))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=M1_layer)
    
    if JLayer_checkerboard is None:
        JLayer_checkerboard = [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.5, 1, 2]
    # checkerboard Junction
    for i, size in enumerate(JLayer_checkerboard):
        structure = m.Structure(chip, start = vadd(loc, (np.sum([(num_checkers+2)*size_sq for size_sq in JLayer_checkerboard[:i]]), clover_leaf_size+2*spacing+text_size[1]+JLayer_ch_offset)))  
        checker_board(chip, structure, (0,0), num_checkers, size, layer=jlayer)

    if do_JClover:
        for i in range(3):
            structure = m.Structure(chip, start = vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)))
            clover_leaf(chip, structure, vadd(loc, ((clover_leaf_size + spacing) * i + clover_leaf_size/2, 1.5*clover_leaf_size+4*spacing+2*text_size[1]+np.max(M1_checkerboard)*num_checkers)), 
                        clover_leaf_size, layer=jlayer, ground_plane=False)
        label_struct = m.Structure(chip, start = vadd(loc, (0, 1*clover_leaf_size+3*spacing+text_size[1]+np.max(M1_checkerboard)*num_checkers)))
        AlphaNumStr(chip, label_struct, f'{jlayer}', size=text_size)

def create_test_grid(chip, grid, x_var, y_var, x_key, y_key, ja_length, j_length,
                     gap_width, window_width, ubridge_width, no_gap, start_grid_x,
                     start_grid_y, M1_pads, ulayer_edge, test_JA, test_smallJ,
                     dose_Jlayer_row, dose_Ulayer_column, no_column, pad_w, pad_s,
                     ptDensity, pad_l, lead_length, cpw_s, jgrid_skip=1, ugrid_skip=1,
                     do_e_beam_label= True, **kwargs):

    if M1_pads:
        row_sep = 490
        column_sep = 1000

    elif not M1_pads:
        row_sep = 150
        column_sep = 200

    if dose_Jlayer_row:
        jlayer = []

        for i in range(grid[0]):
            jlayer.append('2'+str(f"{i*jgrid_skip:02}")+'_SE1_dose_'+str(f"{i*jgrid_skip:02}"))
            chip.wafer.addLayer(jlayer[i],221)
    else:
        jlayer = ['20_SE1'] * no_column
    
    if dose_Ulayer_column:
        ulayer = []

        for i in range(len(grid)):
            ulayer.append('6'+str(f"{i*ugrid_skip:02}")+'_SE1_JJ_dose_'+str(f"{i*ugrid_skip:02}"))
            chip.wafer.addLayer(ulayer[i],150)
    else:
        ulayer = ['60_SE1_JJ'] * len(grid)

    for row, column in enumerate (grid):

        row_label = m.Structure(chip, start = (start_grid_x-250, start_grid_y + row * row_sep),)

        AlphaNumStr(chip, row_label, y_key, size=(40,40), centered=False)
        row_label.translatePos((-120, -60))
        AlphaNumStr(chip, row_label, str(round_sf(y_var[row][0],3)), size=(40,40), centered=False)

        if row == 0:
            for i in range(column):
                column_label = m.Structure(chip, start = (start_grid_x + i * column_sep-40, start_grid_y - 300),)
                AlphaNumStr(chip, column_label, x_key, size=(40,40), centered=False)
                column_label.translatePos((-120, 60))
                AlphaNumStr(chip, column_label, str(round_sf(x_var[0][i],3)), size=(40,40), centered=False)

        for i in range(column):

            s_test = m.Structure(chip, start = (start_grid_x + i * column_sep, start_grid_y + row * row_sep))
            
            s_test_gnd = s_test.clone()
            
            if test_JA:
                lead = ja_length[row][i]
            elif test_smallJ:
                lead = j_length[row][i]+1

            # Left pad
            if M1_pads:
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = True)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
                
                mw.CPW_taper(chip, s_test, length=lead_length, w0 = pad_w, s0=pad_s, w1 = lead + 3, s1=pad_s)

                s_test_gnd = s_test.clone()
                s_test.translatePos((-lead_length, 0))
                s_test_ubridge = s_test.clone()

                mw.Strip_taper(chip, s_test, length=lead_length, w0 = pad_w/4, w1 = lead, layer = jlayer[i])
                mw.Strip_straight(chip, s_test, length=lead_length, w = lead, layer = jlayer[i])
                
                if ulayer_edge:
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length, w0 = pad_w/4, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[row])
            else:
                s_test_ubridge = s_test.clone()

                mw.Strip_taper(chip, s_test, length=lead_length/5, w0 = pad_w/10, w1 = lead, layer = jlayer[i])
                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, layer = jlayer[i])

                if ulayer_edge:
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w0 = pad_w/10, w1 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[row])

            if do_e_beam_label:
                e_beam_label = s_test.clone()
                e_beam_label.translatePos((-13, 10))
                AlphaNumStr(chip, e_beam_label, y_key, size=(4,4), centered=False, layer='20_SE1')
                e_beam_label.translatePos((4, 0))
                AlphaNumStr(chip, e_beam_label, str(round_sf(y_var[row][0],3)), size=(4,4), centered=False, layer='20_SE1')

                e_beam_label.translatePos((-24, 8))
                AlphaNumStr(chip, e_beam_label, x_key, size=(4,4), centered=False, layer='20_SE1')
                e_beam_label.translatePos((4, 0))
                AlphaNumStr(chip, e_beam_label, str(round_sf(x_var[0][i],3)), size=(4,4), centered=False, layer='20_SE1')


            if test_JA:
                junction_chain(chip, s_test, n_junc_array=no_gap, w=window_width[row][i], s=lead, gap=gap_width[row][i], CW = True, finalpiece = False, Jlayer = jlayer[i], Ulayer=ulayer[row])

            elif test_smallJ:
                x, y = s_test.getPos((0, +lead/2))
                smallJ(chip, s_test, (x, y), j_length[row][i], Jlayer = jlayer[i], Ulayer = ulayer[row], lead = lead, gap=gap_width[row][i])
            
            s_test_ubridge = s_test.clone()

            # Right pad
            if M1_pads:
                if ulayer_edge:
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length, layer = ulayer[row])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length, w1 = pad_w/4, w0 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])

                mw.Strip_straight(chip, s_test, length=lead_length, w = lead, s = cpw_s, layer = jlayer[i])
                mw.Strip_taper(chip, s_test, length=lead_length, w1 = pad_w/4, w0 = lead, layer = jlayer[i])

                s_test.translatePos((-lead_length, 0))
                
                mw.CPW_taper(chip, s_test, length=lead_length, w1 = pad_w, w0 = lead, s0 = pad_s, s1 = pad_s)
                mw.CPW_straight(chip, s_test, w = pad_w, s = pad_s, length = pad_l, ptDensity = ptDensity)
            
                mw.CPW_stub_round(chip, s_test, w = pad_w, s = pad_s, ptDensity = ptDensity, flipped = False)
    
            else:
                if ulayer_edge:
                    s_test_ubridge = s_test.clone()
                    mw.CPW_straight(chip, s_test_ubridge, w = lead, s = ubridge_width[row][i], length = lead_length/5, layer = ulayer[row])
                    mw.CPW_taper(chip, s_test_ubridge, length=lead_length/5, w1 = pad_w/10, w0 = lead, s0 = ubridge_width[row][i], s1 = ubridge_width[row][i], layer = ulayer[row])

                mw.Strip_straight(chip, s_test, length=lead_length/5, w = lead, s = cpw_s, layer = jlayer[i])
                mw.Strip_taper(chip, s_test, length=lead_length/5, w1 = pad_w/10, w0 = lead, layer = jlayer[i])
                
            # Ground window for structure 
            if test_JA:

                if len(no_gap) <= 1:
                    gnd_width = lead_length*2 + (gap_width[row][i] + window_width[row][i]) * no_gap[0] - window_width[row][i]

                elif len(no_gap) >= 2:
                    arraylength = 0
                    for j in range(len(no_gap)):
                        arraylength += (-1)**j*no_gap[j]

                    gnd_width = lead_length*2 + (gap_width[row][i] + window_width[row][i]) * arraylength - window_width[row][i]

            elif test_smallJ:
                gnd_width = lead_length*2 + 0.5 + 1.36 + 0.14

            if not M1_pads:
                position = (-(lead_length)*(2-4/5)/2, -40)
            elif M1_pads:
                position = (0, -40)

            chip.add(dxf.rectangle(s_test_gnd.getPos(position), gnd_width, 80,
                        bgcolor=chip.wafer.bg(), layer="5_M1"))
            
class TestChip(m.ChipHelin):
    def __init__(self, wafer, chipID, layer, params, test=True, do_clv_and_cb=True,
                 chipWidth=6800, chipHeight=6800, lab_logo=True, motivational_dxf_path=None,
                 do_chip_title=True):
        super().__init__(wafer, chipID, layer)

        # # Top left no metal strip
        # s = m.Structure(self, start=(0, chipHeight - 50), direction=0)
        # mw.Strip_straight(self, s, length=300, w=100)

        # Chip ID
        if do_chip_title:
            s = m.Structure(self, start=(chipWidth/2, chipHeight-520))
            AlphaNumStr(self, s, chipID, size=(500, 500), centered=True)

        # add standard clover leaf and checkerboard
        if do_clv_and_cb:
            create_clover_leaf_checkerboard(self, loc=(chipWidth-1300, chipHeight-490))

        # add lab logo
        if lab_logo:
            add_imported_polyLine(self, start=(1000, chipHeight-280),
                                file_name=os.path.join(file_dir, 'slab_logo.dxf'),
                                layer=layer, scale=0.6)
        
        # add motivational dxf
        if motivational_dxf_path:
            # add dxf that will cause the chip/wafer to be blessed
            # should be approximately 500x500um for scale to work
            add_imported_polyLine(self, start=(1800, chipHeight-280),
                                    file_name=motivational_dxf_path,
                                    layer=layer, scale=0.6)

        if test:
            for i in range(len(params)):
               create_test_grid(self, **params[i])
            #    print(i)

class Fluxonium4inWafer(m.Wafer):
    def __init__(self, waferID='SIH_Fluxonium_4in', directory=os.path.join(current_dir, 'masks_DXF\\SIH_Tests\\')):
        w = m.Wafer(waferID, directory, chipWidth=6800, chipHeight=6800, 
                waferDiameter=m.waferDiameters['4in'], sawWidth=200, frame=True, markers=True, solid=False)

        w.SetupLayers([  # [layernumber_name, color (autocad index colors)] https://gohtx.com/acadcolors.php
            ['5_M1', 2], #Al base metal
            #['10_M2', 2], #TiN base metal
            ['20_SE1', 221], #Fine shadow-evaporated features
            ['55_SEB1', 221], #Coarse shadow-evaporated features
            ['60_SE1_JJ', 150], #Auxiliary layer for SE1_JJ DRC checks
        ])

        w.setupJunctionLayers(JLAYER='20_SE1', ULAYER='60_SE1_JJ')
        #w.setupAirbridgeLayers(BRLAYER='31_BR', RRLAYER='30_RR', IBRLAYER='131_IBR', IRRLAYER='130_IRR', brcolor=41, rrcolor=32) #CHECK why only on interposer layer

        w.init(FRAME_LAYER=['703_ChipEdge', 7])
        w.DicingBorder(thin=20, long=10, dash=500)

        markerpts = [(-41800,-20800),(-34800,-27800),(-27800,-34800),(-20800,-41800)]
        for pt in markerpts:
            #(note: mirrorX and mirrorY are true by default)
            doMirrored(MarkerSquare, w, pt, 80,layer='EBEAM_MARK')
            doMirrored(MarkerSquare, w, pt, 80,layer='5_M1')

class ImportedChip(m.ChipHelin):
    def __init__(self,wafer,chipID,layer,file_name,rename_dict=None,
                 chipWidth=6800, chipHeight=6800, surpress_warnings=False,
                 do_chip_title=True):
        super().__init__(wafer,chipID,layer)

        doc = ezdxf.readfile(file_name)
        doc.header['$INSUNITS'] = 13 
        msp = doc.modelspace()

        defaultChipWidth = 6800
        defaultChipHeight = 6800

        # Chip ID
        if do_chip_title:
            s = m.Structure(self, start=(defaultChipWidth/2, defaultChipHeight-200))
            AlphaNumStr(self, s, chipID, size=(100, 100), centered=True)

        # if chipWidth and chipHeight are not default, shift all points by the difference/2
        offset = (defaultChipWidth/2, defaultChipHeight/2)

        for entity in msp:
            if entity.dxf.layer in rename_dict:
                layer_updated = rename_dict[entity.dxf.layer]
            else:
                layer_updated = entity.dxf.layer
            
            if entity.dxftype() == 'LINE':
                self.add(dxf.line(
                    start=vadd(entity.dxf.start, offset),
                    end=vadd(entity.dxf.end, offset),
                    color=entity.dxf.color,
                    layer=layer_updated
                ))
            elif entity.dxftype() == 'CIRCLE':
                self.add(dxf.circle(
                    center=vadd(entity.dxf.center, offset),
                    radius=entity.dxf.radius,
                    color=entity.dxf.color,
                    layer=layer_updated
                ))
            elif entity.dxftype() == 'POLYLINE':
                pts = list(entity.points())
                pts.append(pts[0])
                pts = [vadd(pt, offset) for pt in pts]
                poly = dxf.polyline(
                    points=pts,
                    color=entity.dxf.color,
                    layer=layer_updated,
                    bgcolor=self.wafer.bg(layer)
                )
                poly.POLYLINE_CLOSED = True
                poly.close()

                self.add(poly)
            elif entity.dxftype() == 'INSERT':
                raise NotImplementedError('INSERT not supported. Please explode the INSERT block before importing')
            else:
                print(f'Unsupported entity type: {entity.dxftype()}, skipping')
                continue

def add_imported_polyLine(chip, start, file_name, scale=1.0, layer=None):
    doc = ezdxf.readfile(file_name)
    doc.header['$INSUNITS'] = 13 
    msp = doc.modelspace()

    # check that there is only one layer
    for entity in msp:
        if entity.dxftype() != 'POLYLINE':
            print(f'Unsupported entity type: {entity.dxftype()}, skipping')
            continue
        
        pts = list(entity.points())
        pts = [vmul_scalar(pt, scale) for pt in pts]
        # shift points to start
        pts = [vadd(start, pt) for pt in pts]
        pts.append(pts[0])
        poly = dxf.polyline(
            points=pts,
            color=entity.dxf.color,
            layer=layer,
            bgcolor=chip.wafer.bg(layer)
        )
        poly.POLYLINE_CLOSED = True
        poly.close()

        chip.add(poly)

# class StandardTestChip(TestChip):
#     def __init__(wafer, test_index, chipWidth=6800, chipHeight=6800):

#         params = std_params[test_index]
#         chipID = params[0]['chipID']
#         super().__init__(wafer, chipID, layer="5_M1", params=params, test=True, do_clv_and_cb=True,
#                  chipWidth=chipWidth, chipHeight=chipHeight, lab_logo=True, do_chip_title=True)