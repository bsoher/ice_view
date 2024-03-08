#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import abc

# 3rd party modules

# Our modules
import ice_view.util_menu as util_menu
import ice_view.util_ice_view_config as util_ice_view_config
import ice_view.common.prefs_base as prefs_base


"""See common/prefs_base.py for info on the classes below."""

class IceViewPrefs(prefs_base.Prefs, metaclass=abc.ABCMeta):
    def __init__(self, id_class):
        prefs_base.Prefs.__init__(self, util_menu.bar, id_class)

    @property
    def _ConfigClass(self):
        """Returns the appropriate ConfigObj class for this app."""
        return util_ice_view_config.Config


class PrefsMain(IceViewPrefs):
    def __init__(self):
        IceViewPrefs.__init__(self, util_menu.ViewIds)


    @property
    def _ini_section_name(self):
        return "main_prefs"


    def deflate(self):
        # Call my base class deflate
        d = IceViewPrefs.deflate(self)

        # Add my custom stuff
        for name in ("sash_position",
                     "sash_position_main",
                     "sash_position_svd",
                     "line_color_baseline",
                     "line_color_imaginary",
                     "line_color_magnitude",
                     "line_color_metabolite", 
                     "line_color_real",
                     "line_color_svd",
                     "zero_line_plot_color", 
                     "zero_line_plot_style", 
                     "zero_line_color",
                     "zero_line_style",
                     "zero_line_bottom",
                     "zero_line_middle",
                     "zero_line_top",
                     "zero_line_show",
                     "line_width",
                     "xaxis_ppm",
                     "xaxis_hertz"
                    ):
            d[name] = getattr(self, name)

        return d


    def inflate(self, source):
        # Call my base class inflate
        IceViewPrefs.inflate(self, source)

        # Add my custom stuff
        for name in ("sash_position",
                     "sash_position_main",
                     "sash_position_svd",
                     ):
            setattr(self, name, int(source[name]))

        for name in ("line_color_baseline",
                     "line_color_imaginary", 
                     "line_color_magnitude",
                     "line_color_metabolite", 
                     "line_color_real",
                     "line_color_svd",
                     "zero_line_plot_color", 
                     "zero_line_plot_style",
                     "zero_line_color",
                     "zero_line_style",
                     ):
            setattr(self, name, source[name])

        for name in ("line_width", ):
            setattr(self, name, float(source[name]))

        for name in (
                    "zero_line_bottom",
                    "zero_line_middle",
                    "zero_line_top",
                    "zero_line_show",
                    "xaxis_ppm",
                    "xaxis_hertz"
                    ):
            if source[name].lower() in ['true','1','yes']:
                setattr(self, name, True)
            else:
                setattr(self, name, False)

