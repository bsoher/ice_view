#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# Our modules 


"""
When we need to create an app's INI file, this is the content it
uses. 

This module contains just three objects:
1) the name of the application
2) the name of the configuration file to use
3) a dict called DEFAULT_INI_FILE_CONTENT. The dict has a key 
   for the INI file ("ice_view", etc.) and associated with 
   that key is the default content for that INI file. 
"""

APP_NAME = "IceView"
INI_NAME = "ice_view.ini"

# The dict contents are mostly strings 

DEFAULT_INI_FILE_CONTENT = {

###############################      IceView

    "ice_view" : """
# The IceView config file.

# Colors are described in matplotlib's terms. Matplotlib understands standard
# color names like "red", "black", "blue", etc.
# One can also specify the color using an HTML hex string like #eeefff.
# If you use a string like that, you must put it in quotes, otherwise the
# hash mark will get interpreted as a comment marker. For example, to set
# a background to pale yellow:
#    bgcolor = "#f3f3bb"


[main]
left = 40
top = 40
width = 1200
height = 800

[main_prefs]
bgcolor = "#ffffff"
data_type_imaginary = False
data_type_magnitude = False
data_type_real = True
cmap_autumn = True
cmap_blues = False
cmap_jet = False
cmap_rdbu = False
cmap_gray = False
cmap_rdylbu = False
line_color_baseline = blue
line_color_imaginary = red
line_color_magnitude = purple
line_color_metabolite = blue
line_color_real = black
line_color_svd = green
line_width = 1.0
plot_view_all = True
plot_view_final = False
sash_position = 556
sash_position_main = 556
sash_position_svd = 556
xaxis_time = True
xaxis_points = False
xaxis_show = True
zero_line_plot_bottom = True
zero_line_plot_color = goldenrod
zero_line_plot_middle = False
zero_line_plot_show = False
zero_line_plot_style = solid
zero_line_plot_top = False
zero_line_color = goldenrod
zero_line_style = solid
zero_line_bottom = False
zero_line_middle = True
zero_line_top = False
zero_line_show = True
xaxis_ppm = True
xaxis_hertz = False

""" 

,}

