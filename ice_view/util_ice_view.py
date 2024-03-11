#!/usr/bin/env python

# Copyright (c) 2023-2024 Brian J Soher - All Rights Reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules
import os

# 3rd party modules
import numpy as np

# Our modules
from ice_view.common.common_dialogs import pickfile, save_as, message, E_OK


def is_dicom(filename):
    """Returns True if the file in question is a DICOM file, else False. """
    # Per the DICOM specs, a DICOM file starts with 128 reserved bytes
    # followed by "DICM".
    # ref: DICOM spec, Part 10: Media Storage and File Format for Media
    # Interchange, 7.1 DICOM FILE META INFORMATION
    if os.path.isfile(filename):
        f = open(filename, "rb")
        s = f.read(132)
        f.close()
        return s.endswith(b"DICM")
    else:
        return False

def transformation_matrix(x_vector, y_vector, translation, spacing):
    """
    Creates a transformation matrix which will convert from a specified
    coordinate system to the scanner frame of reference.

    Parameters:
        x_vector (array): The unit vector along the space X axis in scanner coordinates
        y_vector (array): The unit vector along the space Y axis in scanner coordinates
        translation (array): The origin of the space in scanner coordinates
        spacing (float or array): The size of a space unit in scanner units

    Returns:
        matrix (array)

    """
    matrix = np.zeros((4, 4), dtype=np.float64)
    matrix[:3, 0] = x_vector
    matrix[:3, 1] = y_vector
    z_vector = np.cross(x_vector, y_vector)
    matrix[:3, 2] = z_vector
    matrix[:3, 3] = np.array(translation)
    matrix[3, 3] = 1.0

    # make sure that we can append to spacing
    spacing = list(spacing)
    while len(spacing) < 4:
        spacing.append(1.0)
    for i in range(4):
        for j in range(4):
            matrix[i, j] *= spacing[j]
    return matrix


def get_ice_pair(fname, verbose=False):
    """ returns a hdr/dat filename pair based on ICE output rules"""
    path = os.path.dirname(fname)
    base, ext = fname.split('.')
    num = base[-5:]

    if ext.lower() == 'icehead':
        fname_hdr = fname
        # we have hdr, need binary fname
        if base[-10:-5 ]=='_spe_':
            fname_dat = os.path.join(path ,'WriteToFile_' +num +'.spe')
        elif base[-9:-5 ]=='_sc_':
            fname_dat = os.path.join(path ,'WriteToFile_' +num +'.sc')
        elif base[-10:-5]=='_ima_':
            fname_dat = os.path.join(path ,'WriteToFile_' + num + '.ima')
        else:
            msg = 'File name does not contain "spe", "sc" of "ima", returning! - \n' + fname
            if verbose: message(msg, style=E_OK)
            raise(ValueError(msg))
    elif ext.lower() in ['spe', 'sc', 'ima']:
        # we have binary, need hdr fname
        fname_dat = fname
        fname_hdr = os.path.join(path ,'MiniHead_' +ext.lower( ) +'_' +num +'.IceHead')
    else:
        msg = 'This is not a *.spe, *.sc, *.ima or *.IceHead file, returning! - \n ' +fname
        if verbose: message(msg, style=E_OK)
        raise(ValueError(msg))

    # we have both ICE files
    return fname_hdr, fname_dat


def get_spe_pair(fname, verbose=False):
    """ returns a hdr/dat filename pair based on ICE output rules"""
    path = os.path.dirname(fname)
    base, ext = fname.split('.')
    num = base[-5:]

    if ext.lower() == 'icehead':
        fname_hdr = fname
        # we have hdr, need binary fname
        if base[-10:-5 ]=='_spe_':
            fname_dat = os.path.join(path ,'WriteToFile_' +num +'.spe')
        else:
            msg = 'File name does not contain "_spe_", returning! - \n' + fname
            if verbose: message(msg, style=E_OK)
            raise(ValueError(msg))
    elif ext.lower()=='spe':
        # we have binary, need hdr fname
        fname_dat = fname
        fname_hdr = os.path.join(path ,'MiniHead_' +ext.lower( ) +'_' +num +'.IceHead')
    else:
        msg = 'This is not a *.spe or *.IceHead file, returning! - \n ' +fname
        if verbose: message(msg, style=E_OK)
        raise(ValueError(msg))

    # we have both ICE files
    return fname_hdr, fname_dat