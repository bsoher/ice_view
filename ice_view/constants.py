#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.

"""A home for constants."""

# Python modules

import math
import collections

# Our modules

DEGREES_TO_RADIANS = math.pi / 180
RADIANS_TO_DEGREES = 180 / math.pi
MINUTES_TO_SECONDS = 60


# PyWavelets is an optional dependency. There's a couple of places in the
# code that need to know whether or not it's installed. Here we make that
# determination so that any code which cares can just check this constant.
# try:
#     import pywt
# except ImportError:
#     PYWAVELETS_AVAILABLE = False
# else:
#     PYWAVELETS_AVAILABLE = True


class Apodization(object):
    """ Apodization constants """
    # MIN =   0
    # MAX = 100
    # INCREMENT = 0.5

    # These constants are arbitrary and may change.
    # However bool(NONE) is guaranteed to be False while
    # bool(X) == True is guaranteed for all other values.
    NONE       = ''
    GAUSSIAN   = 'gaussian'
    LORENTZIAN = 'lorentzian'

    # Items for the spectral processing options dropdown
    choices = collections.OrderedDict(((NONE ,       "None"),
                                       (GAUSSIAN ,   "Gaussian"),
                                       (LORENTZIAN , "Lorentzian"),
                                      ))

class SvdThreshold(object):
    """ PPM threshold constants """
    MIN = -200
    MAX =  200

class SvdThresholdUnit(object):
    """ SVD Threshold Value Unit constants """

    HZ  = 'Hz'
    PPM = 'PPM'

    # Items for the svd processing options dropdown
    choices = collections.OrderedDict(((HZ ,  "Hz"),
                                       (PPM , "PPM"),
                                      ))

class WaterExtrapolation(object):
    """ Water extrapolation constants """
    # These constants are arbitrary and may change.
    # However bool(NONE) is guaranteed to be False while
    # bool(X) == True is guaranteed for all other values.
    NONE = 0
    LINEAR = 1
    AR_MODEL = 2

    MIN_POINTS = 1
    MAX_POINTS = 1000

    # Items for the spectral processing options dropdown
    choices = collections.OrderedDict(((NONE ,     "None"),
                                       (LINEAR ,   "Linear"),
                                       (AR_MODEL , "AR Model"),
                                      ))

class ZeroFillMultiplier(object):
    """
    Zero fill multiplier constants. The zero fill is not only limited
    to a specific range, but it must also be an integral power of 2.
    """
    _EXPONENT = 5
    MIN = 1
    MAX = 2 ** _EXPONENT

    # Items for the spatial processing options
    choices = [ (2 ** i, str(2 ** i)) for i in range(0, _EXPONENT + 1) ]
    choices = collections.OrderedDict(choices)



###################  Dataset Constants

class Dataset(object):
    """ Dataset constants """
    SCALE_INCREMENT = 1.1