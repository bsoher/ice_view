#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules
import wx

# Our modules
import ice_view.common.plot_panel_points as plot_panel_points
        

class PlotPanelIceView(plot_panel_points.PlotPanelPoints):
    
    def __init__(self, parent, tab, tab_dataset, **kwargs):
        
        plot_panel_points.PlotPanelPoints.__init__( self, parent, **kwargs )

        # tab is the containing widget for this plot_panel, it is used
        # in resize events, the tab attribute is the AUI Notebook tab
        # that contains this plot_panel

        self.top   = wx.GetApp().GetTopWindow()
        self.tab   = tab  
        self.tab_dataset = tab_dataset
        
        self.set_color( (255,255,255) )


    # EVENT FUNCTIONS -----------------------------------------------
    
    def on_motion(self, xdata, ydata, val, bounds, iaxis):
        
        value = 0.0
        if iaxis in [0,1,2]:
            value = val[0]
            
        self.top.statusbar.SetStatusText( " Time [sec] = %.3f" % (xdata, ), 0)
        self.top.statusbar.SetStatusText(( " Value = "+str(value)), 2)   

    
    def on_scroll(self, button, step, iaxis):
        
        self.set_vertical_scale(step)
        self.tab.FloatScale.SetValue(self.vertical_scale)
            
            
    def on_zoom_select(self, xmin, xmax, val, ymin, ymax, reset=False, iplot=None):
        if reset:
            # we only need to bother with setting the vertical scale in here
            # if we did a reset of the x,y axes.
            self.vertical_scale = self.dataymax
            self.tab.FloatScale.SetValue(self.dataymax)
        

    def on_zoom_motion(self, xmin, xmax, val, ymin, ymax, iplot=None):
        
        tstr  = xmax
        tend  = xmin
        if tstr > tend: tstr, tend = tend, tstr
        tdelta = tstr - tend  # keeps delta positive
        self.top.statusbar.SetStatusText(( " Time Range = %.2f to %.2f" % (tstr, tend)), 0)
        self.top.statusbar.SetStatusText(( " dTime = %.2f" % (tdelta, )), 2)
            
        
    def on_refs_select(self, xmin, xmax, val, reset=False, iplot=None):

        ppm_str = xmax
        ppm_end = xmin

        if ppm_str < ppm_end: ppm_str, ppm_end = ppm_end, ppm_str

        # Calculate area of span
        all_areas, all_rms = self.calculate_area()
        area = all_areas[0]
        rms  = all_rms[0]
        self.top.statusbar.SetStatusText(' Area = %1.5g  RMS = %1.5g' % (area,rms), 3)


    def on_refs_motion(self, xmin, xmax, val, iplot=None):

        ppm_str  = xmin
        ppm_end  = xmax
        if ppm_str > ppm_end: ppm_str, ppm_end = ppm_end, ppm_str
        delta_ppm = -1*(ppm_str - ppm_end)  # keeps delta positive
        self.top.statusbar.SetStatusText(( " PPM Range = %.2f to %.2f" % (ppm_str, ppm_end)), 0)
        self.top.statusbar.SetStatusText(( " dPPM = %.2f " % (delta_ppm, )), 2)

        all_areas, all_rms = self.calculate_area()
        area = all_areas[0]
        rms  = all_rms[0]
        self.top.statusbar.SetStatusText(' Area = %1.5g  RMS = %1.6g' % (area,rms), 3)
        

    def on_middle_select(self, xstr, ystr, xend, yend, iplot):
        pass


    def on_middle_press(self, xloc, yloc, iplot, bounds=None, xdata=None, ydata=None):
        pass

        
    def on_middle_motion(self, xcur, ycur, xprev, yprev, iplot):
        pass
        
    
        
  
    
