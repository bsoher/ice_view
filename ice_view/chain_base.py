#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import abc


class Chain(object, metaclass=abc.ABCMeta):
    """
    This is the (abstract) base class for all chain objects. It can't 
    be instantiated, but all chains inherit from it and implement the interface
    defined below.
    """


    @abc.abstractmethod
    def __init__(self, dataset, block):
        # Subclassers may want to override this
        self._dataset = dataset
        self._block   = block
        self.data = [ ]

        #self.reset_results_arrays()


    def reset_results_arrays(self):
        # Subclassers may want to override this
        pass


    def run(self, voxel, entry='all'):
        # Subclassers may want to override this
        pass


    def update(self):
        # Subclassers may want to override this
        pass
