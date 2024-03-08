#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python imports


# 3rd party imports

# Our imports
import ice_view.common.misc as util_misc


class Functor(object):
    """An abstract base class for functors. It describes the interface to 
    functors. It also ensures that functors share a common base class so that
    we can differentiate them from plugins (should we ever implement plugins).

    Subclasses may want to override update() and the attribs attribute, and 
    must override algorithm().
    """
    def __init__(self):
        self.attribs = [ ]
        

    def update(self, source):
        """Copies the attributes in self.attribs from the source object to
        this object. The attributes must exist on both objects or an
        AttributeError is raised.

        When self.attribs is empty (as it is by default), this method is
        a no-op.
        """
        for attr in self.attribs:
            util_misc.safe_attribute_set(source, self, attr)
    
    
    def algorithm(self, chain):
        raise NotImplementedError

