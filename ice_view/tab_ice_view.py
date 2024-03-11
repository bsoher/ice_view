#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os
import warnings
import datetime
import time
import sys
import importlib
import xml.etree.cElementTree as ElementTree
from xml.etree.cElementTree import Element

# 3rd party modules
import wx
import wx.grid as gridlib
import wx.lib.agw.aui as aui
import numpy as np
from scipy.fft import fft, fftshift
from wx.lib.mixins.listctrl import CheckListCtrlMixin, ColumnSorterMixin
import matplotlib.cm as cm

# Our modules
import ice_view.tab_base as tab_base
import ice_view.constants as constants
import ice_view.util_menu as util_menu
import ice_view.prefs as prefs
from ice_view.plot_panel_spectral import PlotPanelSpectral
from ice_view.plot_panel_svd_filter import PlotPanelSvdFilter
import ice_view.common.funct_water_filter as funct_watfilt

import ice_view.auto_gui.ice_view as ice_view_ui

import ice_view.common.wx_util as wx_util
from ice_view.common.dist import dist


#------------------------------------------------------------------------------
HLSVD_MAX_SINGULAR_VALUES = 256
HLSVD_MIN_DATA_POINTS = 128
_HLSVD_RESULTS_DISPLAY_SIZE = 6

#------------------------------------------------------------------------------

class CheckListCtrl(wx.ListCtrl, ColumnSorterMixin):
    def __init__(self, _inner_notebook, tab):
        style = wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES
        wx.ListCtrl.__init__(self, _inner_notebook, -1, style=style)
        ColumnSorterMixin.__init__(self, _HLSVD_RESULTS_DISPLAY_SIZE)
        self.itemDataMap = {}
        self._tab_dataset = _inner_notebook
        self.tab = tab
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.Bind(wx.EVT_LIST_ITEM_CHECKED , self.OnCheckItem)
        self.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.OnCheckItem)


    def GetListCtrl(self):
        return self

    def OnItemActivated(self, evt):
        flag = evt.GetEventObject().IsItemChecked(evt.Index)
        self.CheckItem(evt.Index, check=(not flag))

    # this is called by the base class when an item is checked/unchecked
    def OnCheckItem(self, event):
        """
        Note. This event is called everytime self.svd_checklist_update() calls
          CheckItem() for the lines it includes while updating the SVD table.
          This was creating a race condition that crashed Analysis. That method
          is only called when _update_svd_gui is True, so we check for False
          here and know that it is a manual click on a CheckBox and that we
          need to call the on_check_item() method.
        """
        flag = event.GetEventObject().IsItemChecked(event.Index)
#        print('in OnCheckItem index/flag = '+str(event.Index)+'/'+str(flag))
        if self.tab._update_svd_gui == False:
            self.tab.on_check_item(self, event.Index, flag)


#------------------------------------------------------------------------------

class CustomDataTable(gridlib.GridTableBase):

    def __init__(self):
        gridlib.GridTableBase.__init__(self)

        self.colLabels = ['','Rank', 'PPM', 'Freq', 'Damping', 'Phase', 'Area']

        self.dataTypes = [gridlib.GRID_VALUE_BOOL,
                          gridlib.GRID_VALUE_NUMBER,
                          gridlib.GRID_VALUE_FLOAT + ':6,2',
                          gridlib.GRID_VALUE_FLOAT + ':6,2',
                          gridlib.GRID_VALUE_FLOAT + ':6,2',
                          gridlib.GRID_VALUE_FLOAT + ':6,2',
                          gridlib.GRID_VALUE_FLOAT + ':6,2', ]

        # self.colWidths = [60,60,80,80,80,80,80]
        #
        # self.list_svd_results.SetColumnWidth(0, 60)
        # self.list_svd_results.SetColumnWidth(1, 60)
        # self.list_svd_results.SetColumnWidth(2, 80)
        # self.list_svd_results.SetColumnWidth(3, 80)
        # self.list_svd_results.SetColumnWidth(4, 80)
        # self.list_svd_results.SetColumnWidth(5, 80)
        # self.list_svd_results.SetColumnWidth(6, 80)

        self.data = [
            [0, 1, 1.11, 1.12, 1.13, 1.14, 1.15],
            [0, 2, 1.21, 1.22, 1.23, 1.24, 1.25],
            [0, 3, 1.31, 1.32, 1.33, 1.34, 1.35]

            ]


    #--------------------------------------------------
    # required methods for the wxPyGridTableBase interface

    def GetNumberRows(self):
        return len(self.data) + 1

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except IndexError:
            return True

    # Get/Set values in the table.  The Python version of these
    # methods can handle any data-type, (as long as the Editor and
    # Renderer understands the type too,) not just strings as in the
    # C++ version.
    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return ''

    def SetValue(self, row, col, value):
        def innerSetValue(row, col, value):
            try:
                self.data[row][col] = value
            except IndexError:
                # add a new row
                self.data.append([''] * self.GetNumberCols())
                innerSetValue(row, col, value)

                # tell the grid we've added a row
                msg = gridlib.GridTableMessage(self,            # The table
                        gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED, # what we did to it
                        1   )                                   # how many

                self.GetView().ProcessTableMessage(msg)
        innerSetValue(row, col, value)

    #--------------------------------------------------
    # Some optional methods

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.colLabels[col]

    # Called to determine the kind of editor/renderer to use by
    # default, doesn't necessarily have to be the same type used
    # natively by the editor/renderer if they know how to convert.
    def GetTypeName(self, row, col):
        return self.dataTypes[col]

    # Called to determine how the data can be fetched and stored by the
    # editor and renderer.  This allows you to enforce some type-safety
    # in the grid.
    def CanGetValueAs(self, row, col, typeName):
        colType = self.dataTypes[col].split(':')[0]
        if typeName == colType:
            return True
        else:
            return False

    def CanSetValueAs(self, row, col, typeName):
        return self.CanGetValueAs(row, col, typeName)


#---------------------------------------------------------------------------

class CustTableGrid(gridlib.Grid):

    def __init__(self, parent):

        gridlib.Grid.__init__(self, parent, -1)
        table = CustomDataTable()

        # The second parameter means that the grid is to take ownership of the
        # table and will destroy it when done.  Otherwise you would need to keep
        # a reference to it and call it's Destroy method later.
        self.SetTable(table, True)
        self.SetRowLabelSize(0)
        self.SetMargins(0,0)
        self.AutoSizeColumns(False)

        self.Bind(gridlib.EVT_GRID_CELL_LEFT_DCLICK, self.OnLeftDClick)


    # I do this because I don't like the default behaviour of not starting the
    # cell editor on double clicks, but only a second click.
    def OnLeftDClick(self, evt):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

#------------------------------------------------------------------------------

def _configure_combo(control, choices, selection=''):
        lines = list(choices.values())
        control.SetItems(lines)
        if selection in lines:
            control.SetStringSelection(selection)
        else:
            control.SetStringSelection(lines[0])

def _paired_event(obj_min, obj_max):
        val_min = obj_min.GetValue()
        val_max = obj_max.GetValue()
        pmin = min(val_min, val_max)
        pmax = max(val_min, val_max)
        obj_min.SetValue(pmin)
        obj_max.SetValue(pmax)
        return pmin, pmax



#------------------------------------------------------------------------------
#
#  Tab IceView
#
#------------------------------------------------------------------------------


class TabIceView(tab_base.Tab, ice_view_ui.IceViewUI):
    
    def __init__(self, tab_dataset, top, dataset):

        ice_view_ui.IceViewUI.__init__(self, top.notebook_ice_view)
        tab_base.Tab.__init__(self, tab_dataset, top, prefs.PrefsMain)

        # global attributes

        self.top                = top
        self.block              = dataset.blocks['spectral']
        self.dataset            = dataset

        self.cursor_span_picks_lines = False

        # the button at bottom of tab can be set to a number of user defined
        # purposes, namely:
        #
        # 1. Automatic Phasing of data
        #
        # 2. Output of current area value to a text file
        #    - each time it is hit a file select dialog comes up
        #    - default file is last filename selected
        #    - if file exists, value is appended, else file created
        #    - both the dataset name, x,y,z voxel numbers, and area values
        #      are saved in a tab delineated text line

        self.user_button_area_fname = ''

        # _svd_scale_initialized performs the same role as
        # tab_base.Tab._scale_initialized (q.v.)
        self._svd_scale_initialized = False
        self._update_svd_gui = False

        # Plot parameters
        self.dataymax       = 1.0       # used for zoom out
        self.voxel          = [0,0,0]   # x,y only, z in islice

        # values used in plot and export routines, filled in process()
        self.last_export_filename  = ''
        
        # Plotting is disabled during some of init. That's because the plot
        # isn't ready to plot, but the population of some controls
        # (e.g. spin controls on the water filter panel) fires their
        # respective change event which triggers a call to plot(). This
        # is a Windows-specific bug.
        # See http://trac.wxwidgets.org/ticket/14583
        # In any case, skipping some calls to plot() will speed things up. =)
        self._plotting_enabled = False
        self.plot_results = None

        # self.plot_C_function refers to either None or a callable object
        # (i.e. a function) that takes two params which are typically the
        # data from plots A & B.
        # The plot_C_map relates the various options to the
        # appropriate function. The functions currently used are so simple
        # that I implement them with anonymous lambda functions
        self.plot_C_map =   {
            util_menu.ViewIds.PLOT_C_FUNCTION_NONE      : (lambda a, b: (a+b)*0.0),
            util_menu.ViewIds.PLOT_C_FUNCTION_A_MINUS_B : (lambda a, b: a - b),
            util_menu.ViewIds.PLOT_C_FUNCTION_B_MINUS_A : (lambda a, b: b - a),
            util_menu.ViewIds.PLOT_C_FUNCTION_A_PLUS_B  : (lambda a, b: a + b),
                            }
        # The default plot 3 function is set here
        self.plot_C_function = self.plot_C_map[util_menu.ViewIds.PLOT_C_FUNCTION_A_MINUS_B]
        self.plot_C_final = None

        self.initialize_controls()        
        self.populate_controls()

        self._plotting_enabled = True

        self.process_and_plot(init=True)

        #------------------------------------------------------------
        # Set window events
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed, self.NotebookSpectral)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy, self)

        # bjs hack - for now process all data into 'spectral' block here
        dat = self.dataset.blocks['raw'].data
        self.dataset.blocks['spectral'].data = fftshift(fft(dat, axis=-1), axes=-1)

        # If the sash position isn't recorded in the INI file, we use the
        # arbitrary-ish value of 400.
        if not self._prefs.sash_position_main:
            self._prefs.sash_position_main = 400
        if not self._prefs.sash_position_svd:
            self._prefs.sash_position_svd = 400

        # Under OS X, wx sets the sash position to 10 (why 10?) *after*
        # this method is done. So setting the sash position here does no
        # good. We use wx.CallAfter() to (a) set the sash position and
        # (b) fake an EVT_SPLITTER_SASH_POS_CHANGED.
        wx.CallAfter(self.SplitterWindow.SetSashPosition, self._prefs.sash_position_main, True)
        wx.CallAfter(self.SplitterWindowSvd.SetSashPosition, self._prefs.sash_position_svd, True)
        wx.CallAfter(self.on_splitter)


    @property
    def svd_tab_active(self):
        """Returns True if HLSVD is the active tab on the spectral notebook,
        False otherwise."""
        tab = self.NotebookSpectral.GetPage(self.NotebookSpectral.GetSelection())
        return (tab.Id == self.PanelSvdFilter.Id)

    # @property
    # def view_mode(self):
    #     return (3 if self._prefs.plot_view_all else 1)


    #=======================================================
    #
    #           GUI Setup Handlers
    #
    #=======================================================

    def initialize_controls(self):
        """ 
        This method goes through the widgets and sets up certain sizes
        and constraints for those widgets. This method does not set the 
        value of any widget except insofar that it is outside a min/max
        range as those are being set up. 
        
        Use populate_controls() to set the values of the widgets from
        a data object.

        """

        # calculate a few useful values
        
        ds  = self.dataset
        dim0, dim1, dim2, dim3, _, _ = ds.spectral_dims
        sw = ds.sw
        maxppm = ds.pts2ppm(0)
        minppm = ds.pts2ppm(dim0 - 1)
        ppmlim = (minppm, maxppm)

        wx_util.configure_spin(self.SpinX, 60)
        wx_util.configure_spin(self.SpinY, 60)
        wx_util.configure_spin(self.SpinZ, 60)

        wx_util.configure_spin(self.FloatScale, 110, 8, 0.5, (0.0, 100000000.0))

        # The many controls on various tabs need configuration of
        # their size, # of digits displayed, increment and min/max. 

        wx_util.configure_spin(self.FloatWidth,       70, 3, 0.5, (0.0, 100.0))
        wx_util.configure_spin(self.FloatFrequency,   70, 3, 0.5, (-1e4, 1e4))
        wx_util.configure_spin(self.FloatAmplitude,   70, 3, None, (0,1e12))
        self.FloatAmplitude.multiplier = 1.1
        wx_util.configure_spin(self.FloatPhase0,      70, 3, 1.0, (-360.0, 360.0))
        wx_util.configure_spin(self.FloatPhase1,      70, 3, 10.0, (-1e5, 1e5))
        wx_util.configure_spin(self.FloatPhase1Pivot, 70, 3, 0.5, (-1000.0, 1000.0))
        wx_util.configure_spin(self.FloatDcOffset,    70, 3, 0.25, (-1e5, 1e5))
        wx_util.configure_spin(self.SpinLeftShift,    70)

        # set up combo selections
        _configure_combo(self.ComboApodization,      constants.Apodization.choices)

        # set up the user function button initial setting
        if self._prefs.user_button_phasing:
            self.ButtonUserFunction.SetLabel('Do Automatic Phasing')
        elif self._prefs.user_button_area:
            self.ButtonUserFunction.SetLabel('Output Area Value')

        # Water Filter widget constraints
        #
        # - note. by setting the default value first, we avoid having an event
        #     sent that sets the block attribute to the min value because the
        #     widget's original value was outside min/max range when they're set

        self.SpinFirLength.SetValue(funct_watfilt.FIR_LENGTH_DEFAULT)
        wx_util.configure_spin(self.SpinFirLength, 60, None, None,
                               (funct_watfilt.FIR_LENGTH_MIN,
                                funct_watfilt.FIR_LENGTH_MAX))

        self.FloatFirWidth.SetValue(funct_watfilt.FIR_HALF_WIDTH_DEFAULT)
        wx_util.configure_spin(self.FloatFirWidth, 60, None,
                                funct_watfilt.FIR_HALF_WIDTH_STEP,
                               (funct_watfilt.FIR_HALF_WIDTH_MIN,
                                funct_watfilt.FIR_HALF_WIDTH_MAX))

        self.FloatFirRipple.SetValue(funct_watfilt.FIR_RIPPLE_DEFAULT)
        wx_util.configure_spin(self.FloatFirRipple, 60, None,
                                funct_watfilt.FIR_RIPPLE_STEP,
                               (funct_watfilt.FIR_RIPPLE_MIN,
                                funct_watfilt.FIR_RIPPLE_MAX))

        self.SpinFirExtrapValue.SetValue(funct_watfilt.FIR_EXTRAPOLATION_POINTS_DEFAULT)
        wx_util.configure_spin(self.SpinFirExtrapValue, 60, None, None,
                               (funct_watfilt.FIR_EXTRAPOLATION_POINTS_MIN,
                                funct_watfilt.FIR_EXTRAPOLATION_POINTS_MAX))

        self.SpinHamLength.SetValue(funct_watfilt.HAM_LENGTH_DEFAULT)
        wx_util.configure_spin(self.SpinHamLength, 60, None, None,
                               (funct_watfilt.HAM_LENGTH_MIN,
                                funct_watfilt.HAM_LENGTH_MAX))

        self.SpinHamExtrapValue.SetValue(funct_watfilt.HAM_EXTRAPOLATION_POINTS_DEFAULT)
        wx_util.configure_spin(self.SpinHamExtrapValue, 60, None, None,
                               (funct_watfilt.HAM_EXTRAPOLATION_POINTS_MIN,
                                funct_watfilt.HAM_EXTRAPOLATION_POINTS_MAX))

        #-------------------------------------------------------------
        # Set up the view tabs
        #-------------------------------------------------------------

        self.view = PlotPanelSpectral(self.PanelViewSpectral,
                                      self,
                                      self._tab_dataset,
                                      naxes=3,
                                      reversex=True,
                                      zoom='span',
                                      reference=True,
                                      middle=True,
                                      zoom_button=1,
                                      middle_button=3,
                                      refs_button=2,
                                      do_zoom_select_event=True,
                                      do_zoom_motion_event=True,
                                      do_refs_select_event=True,
                                      do_refs_motion_event=True,
                                      do_middle_select_event=True,
                                      do_middle_motion_event=True,
                                      do_scroll_event=True,
                                      props_zoom=dict(alpha=0.2, facecolor='yellow'),
                                      props_cursor=dict(alpha=0.2, facecolor='gray'),
                                      xscale_bump=0.0,
                                      yscale_bump=0.05,
                                      data = [],
                                      prefs=self._prefs,
                                      dataset=self.dataset,
                                      )

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelViewSpectral.SetSizer(sizer)
        self.view.Fit()
        self.view.change_naxes(1)

        #------------------------------------------------------------
        # SVD tab settings
        #------------------------------------------------------------

        self.view_svd = PlotPanelSvdFilter( self.PanelViewSvd,
                                            self,
                                            self._tab_dataset,
                                            naxes=3,
                                            reversex=True,
                                            zoom='span',
                                            reference=True,
                                            middle=True,
                                            zoom_button=1,
                                            middle_button=3,
                                            refs_button=2,
                                            do_zoom_select_event=True,
                                            do_zoom_motion_event=True,
                                            do_refs_select_event=True,
                                            do_refs_motion_event=True,
                                            do_middle_select_event=True,
                                            do_middle_motion_event=True,
                                            do_scroll_event=True,
                                            props_zoom=dict(alpha=0.2, facecolor='yellow'),
                                            props_cursor=dict(alpha=0.2, facecolor='gray'),
                                            xscale_bump=0.0,
                                            yscale_bump=0.05,
                                            data = [],
                                            prefs=self._prefs,
                                            dataset=self.dataset,
                                            )

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.view_svd, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.PanelViewSvd.SetSizer(sizer)
        self.view_svd.Fit()

        #------------------------------------------------------------
        # Results Control

        self.list_svd_results = CheckListCtrl(self.PanelResults, self)
        self.list_svd_results.EnableCheckBoxes(enable=True)
        sizer = wx.BoxSizer()
        sizer.Add(self.list_svd_results, 1, wx.EXPAND)
        self.PanelResults.SetSizer(sizer)
        self.Fit()

        self.list_svd_results.InsertColumn(0, "Rank", wx.LIST_FORMAT_CENTER)
        self.list_svd_results.InsertColumn(1, "PPM", wx.LIST_FORMAT_CENTER)
        self.list_svd_results.InsertColumn(2, "Freq", wx.LIST_FORMAT_CENTER)
        self.list_svd_results.InsertColumn(3, "Damping", wx.LIST_FORMAT_CENTER)
        self.list_svd_results.InsertColumn(4, "Phase", wx.LIST_FORMAT_CENTER)
        self.list_svd_results.InsertColumn(5, "Area", wx.LIST_FORMAT_CENTER)

        self.list_svd_results.SetColumnWidth(0, 60)
        self.list_svd_results.SetColumnWidth(1, 60)
        self.list_svd_results.SetColumnWidth(2, 80)
        self.list_svd_results.SetColumnWidth(3, 80)
        self.list_svd_results.SetColumnWidth(4, 80)
        self.list_svd_results.SetColumnWidth(5, 80)

        # Manual selection is the default
        self.RadioSvdManual.SetValue(True)

        #------------------------------------------------------------
        # Algorithm Controls

        # Here's our safe hard limit for # of data points.
        min_data_points = HLSVD_MIN_DATA_POINTS + 1

        # min_data_points is now in safe territory. Since everything in this
        # code is expressed in powers of 2, we'll keep the same style with
        # min_data_points. Plus it gives us a little margin of error.
        i = 1
        while 2**i < min_data_points:
            i += 1
        min_data_points = 2**i

        # Max # of data points can't be more than the # of points in the data.
        max_data_points = ds.spectral_dims[0]
        self.SliderDataPoints.SetRange(min_data_points, max_data_points)

        # Range is set; now set value.
        n_data_points = min(funct_watfilt.SVD_N_DATA_POINTS, max_data_points)
        self.SliderDataPoints.SetValue(n_data_points)

        # Singular values
        self.SliderSingularValues.SetRange(1, int(HLSVD_MAX_SINGULAR_VALUES))
        self.SliderSingularValues.SetValue(funct_watfilt.SVD_N_SINGULAR_VALUES)

        # There's a lot of ways to change sliders -- dragging the thumb,
        # clicking on either side of the thumb, using the arrow keys to
        # move one tick at a time, and hitting home/end. Fortunately all
        # platforms cook these down into a simple "the value changed" event.
        # Unfortunately it has different names depending on the platform.
        if "__WXMAC__" in wx.PlatformInfo:
            event = wx.EVT_SCROLL_THUMBRELEASE
        else:
            event = wx.EVT_SCROLL_CHANGED

        for slider in (self.SliderDataPoints, self.SliderSingularValues):
                self.Bind(event, self.on_slider_changed, slider)

        wx_util.configure_spin(self.FloatSvdThreshold, 70, 2, 0.1,
                               (constants.SvdThreshold.MIN, constants.SvdThreshold.MAX))

        _configure_combo(self.ComboSvdThresholdUnit, constants.SvdThresholdUnit.choices)

        wx_util.configure_spin(self.FloatSvdExcludeLipidStart, 50, 2, 0.5, ppmlim)
        wx_util.configure_spin(self.FloatSvdExcludeLipidEnd,   50, 2, 0.5, ppmlim)


    def populate_controls(self):
        """ 
        Populates the widgets with relevant values from the data object. 
        It's meant to be called when a new data object is loaded.
        
        This function trusts that the data object it is given doesn't violate
        any rules. Whatever is in the data object gets slapped into the 
        controls, no questions asked. 
        
        """
        ds = self.dataset
        dim0, dim1, dim2, dim3, _, _ = ds.spectral_dims
        voxel = self.voxel
        maxppm = ds.pts2ppm(0)
        minppm = ds.pts2ppm(dim0 - 1)
        voxel = self.voxel

        #-------------------------------------------------------------
        # View Controls

        self.SpinX.SetRange(1, dim1)
        self.SpinY.SetRange(1, dim2)
        self.SpinZ.SetRange(1, dim3)
        self.SpinX.SetValue(voxel[0]+1)
        self.SpinY.SetValue(voxel[1]+1)
        self.SpinZ.SetValue(voxel[2]+1)

        self.FloatScale.SetRange(0.0, 1000000000.0)
        self.FloatScale.multiplier = 1.1

        #------------------------------------------------------------
        # Water Filter settings

        # (Re)populate the Water Filter list

        self.ComboWater.Clear()
        for item in funct_watfilt.WATFILT_MENU_ITEMS:
            self.ComboWater.Append(item, "")
        if self.block.set.water_filter_method == '':
            self.block.set.water_filter_method = 'None'
        self.ComboWater.SetStringSelection(self.block.set.water_filter_method)

        # set all the other filter panel widgets to attribute settings
        self.SpinFirLength.SetValue(self.block.set.fir_length)
        self.FloatFirWidth.SetValue(self.block.set.fir_half_width)
        self.FloatFirRipple.SetValue(self.block.set.fir_ripple)
        self.SpinFirExtrapValue.SetValue(self.block.set.fir_extrapolation_point_count)
        self.ComboFirExtrapMethod.Clear()
        for label in funct_watfilt.FIR_EXTRAPOLATION_ALL:
            self.ComboFirExtrapMethod.Append(label, "")
            if self.block.set.fir_extrapolation_method == label:
                # This is the active filter, so I select it in the list
                self.ComboFirExtrapMethod.SetSelection(self.ComboFirExtrapMethod.GetCount() - 1)
        self.SpinFirExtrapValue.Enable(self.block.set.fir_extrapolation_method == 'AR Model')

        self.SpinHamLength.SetValue(self.block.set.ham_length)
        self.SpinHamExtrapValue.SetValue(self.block.set.ham_extrapolation_point_count)
        self.ComboHamExtrapMethod.Clear()
        for label in funct_watfilt.HAM_EXTRAPOLATION_ALL:
            self.ComboHamExtrapMethod.Append(label, "")
            if self.block.set.ham_extrapolation_method == label:
                # This is the active filter, so I select it in the list
                self.ComboHamExtrapMethod.SetSelection(self.ComboHamExtrapMethod.GetCount() - 1)
        self.SpinHamExtrapValue.Enable(self.block.set.ham_extrapolation_method == 'AR Model')

        choice = self.ComboWater.GetStringSelection()
        if choice == 'None' or choice == 'SVD - water filter':
            self.PanelWaterFir.Hide()
            self.PanelWaterHamming.Hide()
        elif choice == 'FIR - water filter':
            self.PanelWaterFir.Show()
            self.PanelWaterHamming.Hide()
        elif choice == 'Hamming - water filter':
            self.PanelWaterFir.Hide()
            self.PanelWaterHamming.Show()

        # ------------------------------------------------------------
        # Spectral Control setup

        #self.ComboDataB.SetStringSelection(str(self._tab_dataset.indexAB[1]))
        #self.CheckSync.Disable()

        self.CheckFlip.SetValue(self.block.set.flip)
        self.CheckFFT.SetValue(self.block.set.fft)
        self.CheckChop.SetValue(self.block.set.chop)

        # Apodization width is disabled if there's no method chosen
        apodize = constants.Apodization.choices[self.block.set.apodization]
        self.ComboApodization.SetStringSelection(apodize)
        self.FloatWidth.SetValue(self.block.set.apodization_width)
        self.FloatWidth.Enable(bool(self.block.set.apodization))
        self.ComboZeroFill.SetStringSelection(str(int(self.block.set.zero_fill_multiplier)))
        self.FloatFrequency.SetValue(ds.get_frequency_shift(voxel))
        self.CheckFreqLock.SetValue(self.block.frequency_shift_lock)
        self.FloatAmplitude.SetValue(self.block.set.amplitude)
        self.FloatPhase0.SetValue(ds.get_phase_0(voxel))
        self.CheckPhaseLock.SetValue(self.block.phase_lock)
        self.FloatPhase1.SetValue(ds.get_phase_1(voxel))
        self.CheckZeroPhase1.SetValue(self.block.phase_1_lock_at_zero)
        self.FloatPhase1Pivot.SetValue(self.block.set.phase_1_pivot)
        self.FloatDcOffset.SetValue(self.block.set.dc_offset)
        self.SpinLeftShift.SetValue(self.block.set.left_shift_value)
        self.SpinLeftShift.SetRange(0, ds.raw_dims[0])
        self.CheckCorrectPhase1.SetValue(self.block.set.left_shift_correct)

        # ------------------------------------------------------------
        # SVD tab settings
        # ------------------------------------------------------------

        # SVD Algorithm Controls
        self.SliderDataPoints.SetValue(int(self.block.get_data_point_count(voxel)))
        self.SliderSingularValues.SetValue(int(self.block.get_signal_singular_value_count(voxel)))

        # SVD Results Controls
        self.svd_checklist_update()

        self.RadioSvdApplyThreshold.SetValue(self.block.set.svd_apply_threshold)
        self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)
        if self.block.set.svd_apply_threshold:
            self.FloatSvdThreshold.Enable()
        else:
            self.FloatSvdThreshold.Disable()

        item = constants.SvdThresholdUnit.choices[self.block.set.svd_threshold_unit]
        self.ComboSvdThresholdUnit.SetStringSelection(item)
        if item == 'PPM':
            # threshold value used to be in Hz and allowed to range +/- 200
            #  units can now be PPM, so check if we are outside min/max ppm
            val = self.block.set.svd_threshold
            if val < minppm:
                self.block.set.svd_threshold = minppm
            elif val > maxppm:
                self.block.set.svd_threshold = maxppm
                self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)

        self.CheckSvdExcludeLipid.SetValue(self.block.set.svd_exclude_lipid)
        self.FloatSvdExcludeLipidStart.SetValue(self.block.set.svd_exclude_lipid_start)
        self.FloatSvdExcludeLipidEnd.SetValue(self.block.set.svd_exclude_lipid_end)
        if self.block.set.svd_exclude_lipid:
            self.FloatSvdExcludeLipidStart.Enable()
            self.FloatSvdExcludeLipidEnd.Enable()
        else:
            self.FloatSvdExcludeLipidStart.Disable()
            self.FloatSvdExcludeLipidEnd.Disable()

        # ------------------------------------------------------------
        # Global controls
        # ------------------------------------------------------------

        self.TextSource.SetValue(ds.data_sources[0])

        self.view.dataymax = 150.0
        self.view.set_vertical_scale(150.0)
        self.FloatScale.SetValue(self.view.vertical_scale)


    #=======================================================
    #
    #           Global and Menu Event Handlers
    #
    #=======================================================

    def on_destroy(self, event):
        tab_base.Tab.on_destroy(self, event)

    def on_activation(self):
        tab_base.Tab.on_activation(self)

        # these BlockSpectral object values may be changed by other tabs, so
        # update their widget values on activation of this tab
        voxel      = self.voxel
        freq_shift = self.dataset.get_frequency_shift(voxel)
        phase_0    = self.dataset.get_phase_0(voxel)
        phase_1    = self.dataset.get_phase_1(voxel)
        self.FloatFrequency.SetValue(freq_shift)
        self.FloatPhase0.SetValue(phase_0)
        self.FloatPhase1.SetValue(phase_1)

        # This is a faux event handler. wx doesn't call it directly. It's 
        # a notification from my parent (the dataset notebook) to let
        # me know that this tab has become the current one.
        
        # Force the View menu to match the current plot options.
        util_menu.bar.set_menu_from_state(self._prefs.menu_state)

    def on_menu_view_option(self, event):
        event_id = event.GetId()

        if self._prefs.handle_event(event_id):
            if event_id in (util_menu.ViewIds.ZERO_LINE_SHOW,
                            util_menu.ViewIds.ZERO_LINE_TOP,
                            util_menu.ViewIds.ZERO_LINE_MIDDLE,
                            util_menu.ViewIds.ZERO_LINE_BOTTOM,
                            util_menu.ViewIds.XAXIS_SHOW,
                           ):
                self.view.update_axes()
                self.view.canvas.draw()



            elif event_id in (util_menu.ViewIds.DATA_TYPE_REAL,
                              util_menu.ViewIds.DATA_TYPE_IMAGINARY,
                              util_menu.ViewIds.DATA_TYPE_MAGNITUDE,
                             ):
                if event_id == util_menu.ViewIds.DATA_TYPE_REAL:
                    self.view.set_data_type_real()
                elif event_id == util_menu.ViewIds.DATA_TYPE_IMAGINARY:
                    self.view.set_data_type_imaginary()
                elif event_id == util_menu.ViewIds.DATA_TYPE_MAGNITUDE:
                    self.view.set_data_type_magnitude()

                self.view.update(no_draw=True)
                self.view.set_phase_0(0.0, no_draw=True)
                self.view.canvas.draw()

            elif event_id in (util_menu.ViewIdsSpectral.AREA_CALC_PLOT_A,
                              util_menu.ViewIdsSpectral.AREA_CALC_PLOT_B,
                              util_menu.ViewIdsSpectral.AREA_CALC_PLOT_C,
                             ):
                area, rms = self.view.calculate_area()
                if self._prefs.area_calc_plot_a:
                    index = 0
                    labl = 'A'
                elif self._prefs.area_calc_plot_b:
                    index = 1
                    labl = 'B'
                elif self._prefs.area_calc_plot_c:
                    index = 2
                    labl = 'C'
                self.top.statusbar.SetStatusText(self.build_area_text(area[index], rms[index], plot_label=labl), 3)

            elif event_id in (util_menu.ViewIdsSpectral.PLOT_C_FUNCTION_NONE,
                              util_menu.ViewIdsSpectral.PLOT_C_FUNCTION_A_MINUS_B,
                              util_menu.ViewIdsSpectral.PLOT_C_FUNCTION_B_MINUS_A,
                              util_menu.ViewIdsSpectral.PLOT_C_FUNCTION_A_PLUS_B,
                             ):
                if event_id == util_menu.ViewIdsSpectral.PLOT_C_FUNCTION_NONE:
                    if len(self.view.axes) == 3:
                        if self.datasetB:
                            self.view.change_naxes(2)
                        else:
                            self.view.change_naxes(1)
                else:
                    if len(self.view.axes) != 3:
                        self.view.change_naxes(3)

                self.plot_C_function = self.plot_C_map[event_id]

                self.set_plot_c()
                self.view.canvas.draw_idle()

            elif event_id in (util_menu.ViewIdsSpectral.USER_BUTTON_PHASING,
                              util_menu.ViewIdsSpectral.USER_BUTTON_AREA,
                             ):
                if event_id == util_menu.ViewIdsSpectral.USER_BUTTON_PHASING:
                    label = 'Do Automatic Phasing'
                elif event_id == util_menu.ViewIdsSpectral.USER_BUTTON_AREA:
                    label = 'Output Area Value'
                self.ButtonUserFunction.SetLabel(label)



    #=======================================================
    #
    #           Widget Event Handlers
    #
    #=======================================================

    def on_tab_changed(self, event):
        voxel = self.voxel
        ph0 = self.dataset.get_phase_0(voxel)
        ph1 = self.dataset.get_phase_1(voxel)
        # refresh the plot in the current sub-tab
        if self.svd_tab_active:
            view = self.view_svd
            view.set_phase_0(ph0, absolute=True)
            view.set_phase_1(ph1, absolute=True)
        else:
            view = self.view
            view.set_phase_0(ph0, index=[0], absolute=True)
            view.set_phase_1(ph1, index=[0], absolute=True)
            # if self.tabB_spectral:
            #     ph0b = self.datasetB.get_phase_0(voxel)
            #     ph1b = self.datasetB.get_phase_1(voxel)
            #     view.set_phase_0(ph0b, index=[1], absolute=True)
            #     view.set_phase_1(ph1b, index=[1], absolute=True)

        self.FloatScale.SetValue(view.vertical_scale)

    def on_splitter(self, event=None):
        # This is sometimes called programmatically, in which case event is None
        self._prefs.sash_position_main = self.SplitterWindow.GetSashPosition()
        self._prefs.sash_position_svd = self.SplitterWindowSvd.GetSashPosition()

    def on_voxel(self, event):
        self.set_voxel()

    def set_voxel(self):
        tmpx = self.SpinX.GetValue()-1
        tmpy = self.SpinY.GetValue()-1
        tmpz = self.SpinZ.GetValue()-1
        dim0, dim1, dim2, dim3, _, _ = self.dataset.spectral_dims
        tmpx = max(0, min(dim1-1, tmpx))  # clip to range
        tmpy = max(0, min(dim2-1, tmpy))
        tmpz = max(0, min(dim3-1, tmpz))
        self.SpinX.SetValue(tmpx+1)
        self.SpinY.SetValue(tmpy+1)
        self.SpinZ.SetValue(tmpz+1)
        self.voxel = [tmpx, tmpy, tmpz]
        self.process()
        self.plot()

    def on_scale(self, event):
        view = self.view
        scale = self.FloatScale.GetValue()
        if scale > view.vertical_scale:
            view.set_vertical_scale(1.0, scale_mult=1.1)
        else:
            view.set_vertical_scale(-1.0, scale_mult=1.1)
        self.FloatScale.SetValue(view.vertical_scale)


    # Spectral Control events ---------------------------------------

    def on_combo_dataB(self, event):
        pass

    def on_flip(self, event):
        # flip respects the sync A/B setting
        value = event.GetEventObject().GetValue()
    #     nb = self.top.notebook_datasets
    #     poll_labels = [self._tab_dataset.indexAB[0]]
    #     if self.do_sync:
    #         poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
    #     nb.global_poll_sync_event(poll_labels, value, event='flip')
    #
    # def set_flip(self, value):
        self.block.set.flip = value
        self.CheckFlip.SetValue(value)
        self.process_and_plot()

    def on_fft(self, event):
        # FFT is always the same across datasets regardless of sync A/B
        value = event.GetEventObject().GetValue()
        self.block.set.fft = value
        # if self.do_sync:
        #     self.datasetB.blocks["spectral"].set.fft = value
        #     self.tabB_spectral.CheckFFT.SetValue(value)
        #     self.tabB_spectral.process_and_plot()
        self.process_and_plot()

    def on_chop(self, event):
        # chop respects the sync A/B setting
        value = event.GetEventObject().GetValue()
    #     nb = self.top.notebook_datasets
    #     poll_labels = [self._tab_dataset.indexAB[0]]
    #     if self.do_sync:
    #         poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
    #     nb.global_poll_sync_event(poll_labels, value, event='chop')
    #
    # def set_chop(self, value):
        self.block.set.chop = value
        self.CheckChop.SetValue(value)
        self.process_and_plot()

    def on_sync(self, event):
        """
        This check should only be turned on if there is a dataset selected for
        plot B. Otherwise this is always turned off.

        """
        pass
        # value = event.GetEventObject().GetValue()
        # self._tab_dataset.sync = value

    def on_ecc_method(self, event=None):
        # ecc method ignores the sync A/B setting
        # This event handler is sometimes called programmatically, in which
        # case event is None. Don't rely on its existence!
        pass
        # label = event.GetEventObject().GetStringSelection()
        # self.block.set.ecc_method = label
        #
        # self.top.Freeze()
        # if label == 'None':
        #     self.PanelEccBrowse.Hide()
        # else:
        #     self.PanelEccBrowse.Show()
        #
        # self.top.Layout()
        # self.PanelSpectral.Layout()
        # self.top.Thaw()
        #
        # self.process_and_plot()

    def on_ecc_browse(self, event):
        # Allows the user to select an ECC dataset.
        pass
        # dialog = dialog_dataset_browser.DialogDatasetBrowser(self.top.datasets)
        # dialog.ShowModal()
        # ecc_dataset = dialog.dataset
        # dialog.Destroy()
        #
        # if ecc_dataset:
        #     self.dataset.set_associated_dataset_ecc(ecc_dataset)
        #     self.TextEccFilename.SetValue(ecc_dataset.blocks["raw"].data_source)
        #     self.process_and_plot()

    def on_water_method(self, event=None):
        # water filter type ignores the sync A/B setting
        # This event handler is sometimes called programmatically, in which
        # case event is None. Don't rely on its existence!
        label = event.GetEventObject().GetStringSelection()
        self.block.set.water_filter_method = label

        self.top.Freeze()
        if label == 'None' or label == 'SVD - water filter':
            self.PanelWaterFir.Hide()
            self.PanelWaterHamming.Hide()
        elif label == 'FIR - water filter':
            self.PanelWaterFir.Show()
            self.PanelWaterHamming.Hide()
        elif label == 'Hamming - water filter':
            self.PanelWaterFir.Hide()
            self.PanelWaterHamming.Show()

        self.top.Layout()
        self.PanelSpectral.Layout()
        self.top.Thaw()
        self.process_and_plot()
    def on_fir_length(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.fir_length = value
        self.process_and_plot()

    def on_fir_width(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.fir_half_width = value
        self.process_and_plot()

    def on_fir_ripple(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.fir_ripple = value
        self.process_and_plot()

    def on_fir_extrap_method(self, event):
        value = event.GetEventObject().GetStringSelection()
        self.block.set.fir_extrapolation_method = value
        flag = self.block.set.fir_extrapolation_method == 'AR Model'
        self.SpinFirExtrapValue.Enable(flag)
        self.process_and_plot()

    def on_fir_extrap_value(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.fir_extrapolation_point_count = value
        self.process_and_plot()

    def on_ham_length(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.ham_length = value
        self.process_and_plot()

    def on_ham_extrap_method(self, event):
        value = event.GetEventObject().GetStringSelection()
        self.block.set.ham_extrapolation_method = value
        flag = self.block.set.ham_extrapolation_method == 'AR Model'
        self.SpinHamExtrapValue.Enable(flag)
        self.process_and_plot()

    def on_ham_extrap_value(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.ham_extrapolation_point_count = value
        self.process_and_plot()

    def on_frequency_shift_lock(self, event):
        # frequency shift lock respects the sync A/B setting
        pass
    #     value = event.GetEventObject().GetValue()
    #     nb = self.top.notebook_datasets
    #     poll_labels = [self._tab_dataset.indexAB[0]]
    #     if self.do_sync:
    #         poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
    #     nb.global_poll_sync_event(poll_labels, value, event='frequency_shift_lock')
    #
    # def set_frequency_shift_lock(self, value):
    #     self.block.frequency_shift_lock = value
    #     self.CheckFreqLock.SetValue(value)

    def on_phase_lock(self, event):
        # phase 0 lock respects the sync A/B setting
        pass
    #     value = event.GetEventObject().GetValue()
    #     nb = self.top.notebook_datasets
    #     poll_labels = [self._tab_dataset.indexAB[0]]
    #     if self.do_sync:
    #         poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
    #     nb.global_poll_sync_event(poll_labels, value, event='phase_lock')
    #
    # def set_phase_lock(self, value):
    #     self.block.phase_lock = value
    #     self.CheckPhaseLock.SetValue(value)

    def on_phase1_zero(self, event):
        # phase 1 zero respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.block.phase_1_lock_at_zero = value
        if value:
            self.dataset.set_phase_1(0.0, self.voxel)    # value is NULL here since method checks the 'lock' flag
            self.FloatPhase1.SetValue(0.0)
        self.CheckZeroPhase1.SetValue(value)
        self.view.set_phase_1(self.block.get_phase_1(self.voxel), index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()

    def on_left_shift_correction(self, event):
        # left shift correction respects the sync A/B setting
        pass
    #     value = event.GetEventObject().GetValue()
    #     nb = self.top.notebook_datasets
    #     poll_labels = [self._tab_dataset.indexAB[0]]
    #     if self.do_sync:
    #         poll_labels = [self._tab_dataset.indexAB[0],self._tab_dataset.indexAB[1]]
    #     nb.global_poll_sync_event(poll_labels, value, event='left_shift_correction')
    #
    # def set_left_shift_correction(self, value):
    #     self.block.set.left_shift_correct = value
    #     self.CheckCorrectPhase1.SetValue(value)
    #     self.process_and_plot()

    def on_zero_fill(self, event):
        # zero fill multiplier is always synched across spectra
        zf_value = int(event.GetEventObject().GetStringSelection())

        # reset ALL dataset then ALL gui stuff as needed
        self._tab_dataset._outer_notebook.global_block_zerofill_update(zf_value)
        #self._tab_dataset._outer_notebook.global_tab_zerofill_update(zf_value)

        self.process_and_plot()

    def on_apodization_method(self, event):
        # apodization type ignores the synch A/B setting
        index = event.GetEventObject().GetSelection()
        apodization = list(constants.Apodization.choices.keys())[index]
        self.block.set.apodization = apodization

        # Enable the value textbox if a method is selected
        self.FloatWidth.Enable(bool(apodization))
        self.process_and_plot()

    def on_apodization_value(self, event):
        # apodization width ignores the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.block.set.apodization_width = value
        self.process_and_plot()

    def on_b0_shift(self, event):
        value = event.GetEventObject().GetValue()
        self.dataset.set_frequency_shift(value, self.voxel)     # set absolute shift
        self.process_and_plot()

    def on_amplitude(self, event):
        # amplitude multiplier ignores the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.block.set.amplitude = value
        self.process_and_plot()

    def on_phase0(self, event):
        # phase 0 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        orig = self.dataset.get_phase_0(self.voxel)
        self.set_phase_0(value-orig, self.voxel)         # sets delta change
        self.view.set_phase_0(self.block.get_phase_0(self.voxel), index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()

    def on_phase1(self, event):
        # phase 1 respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        orig = self.dataset.get_phase_1(self.voxel)
        self.set_phase_1(value-orig, self.voxel)         # sets delta change
        self.view.set_phase_1(self.block.get_phase_1(self.voxel), index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()

    def on_phase1_pivot(self, event):
        # phase 1 pivot respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.set_phase1_pivot(value)

    def set_phase1_pivot(self, value):
        self.block.set.phase_1_pivot = value
        self.FloatPhase1Pivot.SetValue(value)
        self.process_and_plot()

    def on_dc_offset(self, event):
        # DC offset respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.block.set.dc_offset = value
        self.process_and_plot()

    def on_left_shift_value(self, event):
        # left shift points respects the sync A/B setting
        value = event.GetEventObject().GetValue()
        self.block.set.left_shift_value = value
        self.process_and_plot()

    def on_user_function(self, event):
        label = event.GetEventObject().GetLabel()

        if label == 'Do Automatic Phasing':

            freq = self.plot_results['freq']
            phase = self.dataset.automatic_phasing_max_real_freq(freq)
            voxel = self.voxel
            self.dataset.set_phase_0(phase, voxel)
            self.FloatPhase0.SetValue(phase)
            self.process_and_plot()

    def on_process_all(self, event):
        pass
        # self.process(init=True, dataset_to_process=[0,], dynamic=False)
        # self.update_image_integral(set_ceil=True, set_floor=True)
        # self.plot()

    # SVD Tab Control events ---------------------------------------

    def on_reset_all(self, event):

        msg = "This will set parameters to default values and erase \nall results. Are you sure you want to continue?"
        if wx.MessageBox(msg, "Reset All Voxels", wx.YES_NO, self) == wx.YES:
            # set all results to 0, turn off all lines. Note. when we replot
            # the current voxel, this will calculate a result for that voxel
            self.block.set_dims(self.dataset)
            self.on_voxel_change(self.voxel)
            self.process_and_plot()

    def on_slider_changed(self, event):
        # One of the sliders was changed. Each change requires re-applying
        # the HLSVD algorithm.
        # We allow the control to update itself before performing the HLSVD.
        # If we don't, then there can be a noticeable & confusing pause
        # between interacting with the control and seeing it actually change.
        wx.CallAfter(self._apply_hlsvd)

    def on_check_item(self, listctrl, index, flag):
        # Clicking on a check box in the table causes both the Threshold and
        # Exclude Lipid automatic calculations to be turned off. If you are
        # clicking you obviously want a 'manual' mode. No other boxes are set
        # or unset when the Threshold or Exclude Lipid boxes are unchecked,
        # but those algorithms don't run when their flag are off.

        voxel = self.voxel
        # because the user can sort the list using any column, we need to
        # get the rank value for the item at index that is causing the event,
        # this is the actual index of the line in the block
        block_index = int(self.list_svd_results.GetItemText(index))-1

        svd_output = self.block.get_svd_output(voxel)
        svd_output.in_model[block_index] = flag

        self.block.set.svd_apply_threshold = False
        if self.RadioSvdApplyThreshold.GetValue():
            self.RadioSvdManual.SetValue(True)
        self.FloatSvdThreshold.Disable()
        self.ComboSvdThresholdUnit.Disable()

        self.block.set.svd_exclude_lipid = False
        self.CheckSvdExcludeLipid.SetValue(False)
        self.FloatSvdExcludeLipidStart.Disable()
        self.FloatSvdExcludeLipidEnd.Disable()
        self.process_and_plot()

    def on_svd_manual(self, event):
        self.cursor_span_picks_lines = False
        self.block.set.svd_apply_threshold = False
        self.FloatSvdThreshold.Disable()
        self.ComboSvdThresholdUnit.Disable()
        self.process_and_plot()

    def on_svd_cursor_span_picks_lines(self, event):
        self.cursor_span_picks_lines = True
        self.block.set.svd_apply_threshold = False
        self.FloatSvdThreshold.Disable()
        self.ComboSvdThresholdUnit.Disable()
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_svd_apply_threshold(self, event):
        self.cursor_span_picks_lines = False
        self.block.set.svd_apply_threshold = True
        self.FloatSvdThreshold.Enable()
        self.ComboSvdThresholdUnit.Enable()
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_svd_threshold(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.svd_threshold = value
        self._update_svd_gui = True
        if self.block.set.svd_threshold_unit == 'PPM':
            dataset = self.dataset
            dim0, dim1, dim2, dim3, _, _ = dataset.spectral_dims
            maxppm  = dataset.pts2ppm(0)
            minppm  = dataset.pts2ppm(dim0-1)
            # threshold value used to be in Hz and allowed to range +/- 200
            #  units can now be PPM, so check if we are outside min/max ppm
            val = self.block.set.svd_threshold
            if val < minppm:
                self.block.set.svd_threshold = minppm
                self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)
            elif val > maxppm:
                self.block.set.svd_threshold = maxppm
                self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)
        self.process_and_plot()
        self._update_svd_gui = False

    def on_svd_threshold_unit(self, event):
        index = event.GetEventObject().GetSelection()
        item = list(constants.SvdThresholdUnit.choices.keys())[index]
        self.block.set.svd_threshold_unit = item

        if self.block.set.svd_threshold_unit == 'PPM':
            dataset = self.dataset
            dim0, dim1, dim2, dim3, _, _ = dataset.spectral_dims
            maxppm  = dataset.pts2ppm(0)
            minppm  = dataset.pts2ppm(dim0-1)
            # threshold value used to be in Hz and allowed to range +/- 200
            #  units can now be PPM, so check if we are outside min/max ppm
            if self.block.set.svd_threshold < minppm:
                self.block.set.svd_threshold = minppm
                self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)
            elif self.block.set.svd_threshold > maxppm:
                self.block.set.svd_threshold = maxppm
                self.FloatSvdThreshold.SetValue(self.block.set.svd_threshold)
        self.process_and_plot()

    def on_svd_exclude_lipid(self, event):
        value = event.GetEventObject().GetValue()
        self.block.set.svd_exclude_lipid = value
        if value:
            self.FloatSvdExcludeLipidStart.Enable()
            self.FloatSvdExcludeLipidEnd.Enable()
        else:
            self.FloatSvdExcludeLipidStart.Disable()
            self.FloatSvdExcludeLipidEnd.Disable()
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_svd_exclude_lipid_start(self, event):
        # Note. min=End and max=Start because dealing with PPM range
        min, max = _paired_event(self.FloatSvdExcludeLipidEnd,
                                 self.FloatSvdExcludeLipidStart)
        self.block.set.svd_exclude_lipid_start = max
        self.block.set.svd_exclude_lipid_end   = min
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_svd_exclude_lipid_end(self, event):
        # Note. min=End and max=Start because dealing with PPM range
        min, max = _paired_event(self.FloatSvdExcludeLipidEnd,
                                 self.FloatSvdExcludeLipidStart)
        self.block.set.svd_exclude_lipid_start = max
        self.block.set.svd_exclude_lipid_end   = min
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_all_on(self, event):
        # Spectral water filter HLSVD threshold value will take precedence
        # over this setting if it is on. The change in the in_model array takes
        # place in the process() call to run the chain.
        voxel = self.voxel
        svd_output = self.block.get_svd_output(voxel)
        svd_output.in_model.fill(True)
        self.block.set.svd_apply_threshold = False
        self.FloatSvdThreshold.Disable()
        if self.RadioSvdApplyThreshold.GetValue():
            self.RadioSvdManual.SetValue(True)

        self.block.set.svd_exclude_lipid = False
        self.CheckSvdExcludeLipid.SetValue(False)
        self.FloatSvdExcludeLipidStart.Disable()
        self.FloatSvdExcludeLipidEnd.Disable()
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False

    def on_all_off(self, event):
        # Spectral water filter HLSVD threshold value will take precedence
        # over this setting if it is on. The change in the in_model array takes
        # place in the process() call to run the chain.
        voxel = self.voxel
        svd_output = self.block.get_svd_output(voxel)
        svd_output.in_model.fill(False)
        self.block.set.svd_apply_threshold = False
        self.FloatSvdThreshold.Disable()
        if self.RadioSvdApplyThreshold.GetValue():
            self.RadioSvdManual.SetValue(True)

        self.block.set.svd_exclude_lipid = False
        self.CheckSvdExcludeLipid.SetValue(False)
        self.FloatSvdExcludeLipidStart.Disable()
        self.FloatSvdExcludeLipidEnd.Disable()
        self._update_svd_gui = True
        self.process_and_plot()
        self._update_svd_gui = False


    #=======================================================
    #
    #           Public Methods
    #
    #=======================================================

    def set_frequency_shift(self, delta, voxel, auto_calc=False, entry='one'):
        '''
        Phase0, phase 1 and frequency shift are all parameters that affect the
        data in the spectral tab, however, they can also be changed in other
        places using either widgets or mouse canvas events. In the end, these
        GUI interactions are all changing the same variables located in the
        block_spectral object.

        Because these can be changed by "between tabs" actions, I've located
        these methods at this level so that one datasest does not ever talk
        directly to another tab, but just to a parent (or grandparent).

        '''
        b0shift = self.block.get_frequency_shift(voxel)
        b0shift = b0shift + delta
        self.block.set_frequency_shift(b0shift, voxel)
        self.FloatFrequency.SetValue(b0shift)
        self.plot_results = self.block.chain.run([voxel]) #, entry=entry)
        self.plot()


    def set_phase_0(self, delta, voxel, auto_calc=False):
        '''
        This method only updates block values and widget settings, not view
        display. That is done in the set_xxx_x_view() method.

        '''
        phase_0 = self.block.get_phase_0(voxel)
        phase_0 = (phase_0 + delta) 
        phase_0 = (phase_0+180)%360-180
        
        self.block.set_phase_0(phase_0,voxel)
        self.FloatPhase0.SetValue(phase_0)


    def set_phase_0_view(self, voxel):
        phase0 = self.block.get_phase_0(voxel)
        self.view.set_phase_0(phase0, index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()


    def set_phase_1(self, delta, voxel, auto_calc=False):
        '''
        Phase0, phase 1 and frequency shift are all parameters that affect the
        data in the spectral tab, however, they can also be changed in other
        places using either widgets or mouse canvas events. In the end, these
        GUI interactions are all changing the same variables located in the
        block_spectral object.

        Because these can be changed by "between tabs" actions, I've located
        these methods at this level so that one tab does not ever talk directly
        to another tab, but just to a parent (or grandparent).

        '''
        # check if phase1 is locked at zero
        if not self.block.phase_1_lock_at_zero:
            phase_1 = self.block.get_phase_1(voxel)
            phase_1 = phase_1  + delta
        else:
            phase_1 = 0.0

        self.block.set_phase_1(phase_1,voxel)
        self.FloatPhase1.SetValue(phase_1)

    def set_phase_1_view(self, voxel):
        phase1 = self.block.get_phase_1(voxel)
        self.view.set_phase_1(phase1, index=[0], absolute=True, no_draw=True)
        self.view.canvas.draw()

    def chain_status(self, msg, slot=1):
        self.top.statusbar.SetStatusText((msg), slot)


    def process_and_plot(self, entry='one',
                         init=False,
                         no_draw=False,
                         dynamic=False):
        """
        The process(), plot() and process_and_plot() methods are standard in
        all processing tabs. They are called to update the data in the plot
        results dictionary, the plot_panel in the View side of the tab or both.

        """
        tab_base.Tab.process_and_plot(self, entry)

        if self._plotting_enabled:
            self.process(entry, init, dynamic=dynamic)
            self.plot(no_draw=no_draw)
            if not dynamic:
                self.plot_svd(no_draw=no_draw)

    def process(self, entry='one', init=False, dynamic=False):
        """
        Data processing results are stored into the Block inside the Chain,
        but the View results are returned as a dictionary from the Chain.run()
        method. The plot routine takes its inputs from this dictionary.

        The dataset_to_process param can be a single integer or a tuple/list
        in the range (0, 1). It defaults to (0, 1). Since the Spectral tab has
        the option to compare a "datasetB" to the "dataset" in the tab, and
        datasetB can also be synched to the tab's dataset, we may need to
        process both dataset and datasetB for each call to process(). The
        parameter "dataset_to_process" can be set to process either dataset or
        datasetB or both by setting it to a tuple of (0,) or (1,) or (0,1)
        respectively
        """
        tab_base.Tab.process(self, entry)

        if self._plotting_enabled:

            # update plot results arrays if required
            voxel = [self.voxel, ]

            if dynamic:
                entry = 'dynamic'

            block = self.block
            do_fit = block.get_do_fit(voxel[0])
            self.plot_results = block.chain.run(voxel, entry=entry)

            if not dynamic:
                # refresh the hlsvd sub-tab on the active dataset tab
                if do_fit or init or self._update_svd_gui:
                    # we changed results, now need to update results widget
                    self.svd_checklist_update()
                else:
                    # same results, but check boxes may have changed
                    self.set_check_boxes()

            # if self.fit_mode == 'all':
            #     voxel = self.dataset.get_all_voxels()  # list of tuples, with mask != 0
            #     entry = 'all'
            #     self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)

    def plot_svd(self, no_draw=False, dynamic=False):
        """
        The set_data() method sets data into the plot_panel_spectrum object
        in the plot in the right panel.

        """
        if dynamic: return

        if self._plotting_enabled:

            voxel = self.voxel
            results = self.plot_results

            data1 = {'data': results['svd_data'],
                     'line_color_real': self._prefs.line_color_real,
                     'line_color_imaginary': self._prefs.line_color_imaginary,
                     'line_color_magnitude': self._prefs.line_color_magnitude}

            data2 = {'data': results['svd_peaks_checked'],
                     'line_color_real': self._prefs.line_color_svd,
                     'line_color_imaginary': self._prefs.line_color_svd,
                     'line_color_magnitude': self._prefs.line_color_svd}

            data3 = {'data': results['svd_data'] - results['svd_peaks_checked_sum'],
                     'line_color_real': self._prefs.line_color_real,
                     'line_color_imaginary': self._prefs.line_color_imaginary,
                     'line_color_magnitude': self._prefs.line_color_magnitude}

            data = [[data1], [data2], [data3]]
            self.view_svd.set_data(data)

            if self._svd_scale_initialized:
                self.view_svd.update(no_draw=True)
            else:
                ymax = np.max(np.abs(fft(self.dataset.get_source_data('spectral'))) / self.dataset.spectral_dims[0])
                self.view_svd.update(no_draw=True, set_scale=True)  # TODO bjs, get from siview  , force_ymax=ymax)
                self._svd_scale_initialized = True

            ph0 = self.dataset.get_phase_0(voxel)
            ph1 = self.dataset.get_phase_1(voxel)
            self.view_svd.set_phase_0(ph0, absolute=True, no_draw=True)
            self.view_svd.set_phase_1(ph1, absolute=True)

    def plot(self, no_draw=False):
        """
        The set_data() method sets data into the plot_panel_spectrum object
        in the plot in the right panel.

        """
        tab_base.Tab.plot(self)

        if self._plotting_enabled:

            voxel = self.voxel
            results = self.plot_results
            data1 = results['freq']
            ph0_1 = self.dataset.get_phase_0(voxel)
            ph1_1 = self.dataset.get_phase_1(voxel)

            data2 = np.zeros_like(data1)
            ph0_2 = 0.0
            ph1_2 = 0.0

            data3 = np.zeros_like(data1)

            # these data will use default line colors in view  data1 == data2
            data = [[data1], [data2], [data3]]
            self.view.set_data(data)

            if self._scale_initialized:
                self.view.update(no_draw=True)
            else:
                ymax = np.max(np.abs(fft(self.dataset.get_source_data('spectral'))) / self.dataset.spectral_dims[0])
                self.view.update(no_draw=True, set_scale=True) # TODO bjs, get from siview , force_ymax=ymax)
                self._scale_initialized = True

            # we take this opportunity to ensure that our phase values reflect
            # the values in the block.
            self.view.set_phase_0(ph0_1, absolute=True, no_draw=True, index=[0])
            self.view.set_phase_1(ph1_1, absolute=True, no_draw=True, index=[0])
            self.view.set_phase_0(ph0_2, absolute=True, no_draw=True, index=[1])
            self.view.set_phase_1(ph1_2, absolute=True, no_draw=True, index=[1])

            self.set_plot_c()

            self.view.canvas.draw_idle()

            # Calculate the new area after phasing
            area, rms = self.view.calculate_area()
            if self._prefs.area_calc_plot_a:
                index = 0
                labl = 'A'
            elif self._prefs.area_calc_plot_b:
                index = 1
                labl = 'B'
            elif self._prefs.area_calc_plot_c:
                index = 2
                labl = 'C'
            else:
                index = 0
                labl = 'A'
            self.top.statusbar.SetStatusText(self.build_area_text(area[index], rms[index], plot_label=labl), 3)






    # def process_and_plot(self, initialize=False):
    #
    #     self.process()
    #     self.plot(initialize=initialize)
    #
    #
    # def process(self):
    #     """
    #     Currently this is just an FFT and FFTSHIFT.  May add more in future.
    #
    #     """
    #     voxel = [self.voxel]
    #     entry = 'one'
    #     self.plot_results = self.block.chain.run(voxel, entry=entry)
    #
    #     # if self.fit_mode == 'all':
    #     #     voxel = self.dataset.get_all_voxels()  # list of tuples, with mask != 0
    #     #     entry = 'all'
    #     #     self.plot_results = self.dataset.chain.run(voxel, entry=entry, status=self.chain_status)
    #
    #
    # def plot(self, is_replot=False, initialize=False):
    #
    #     if self.dataset == None:
    #         return
    #
    #     if self._plotting_enabled:
    #
    #         voxel = self.voxel
    #         data1 = self.plot_results['freq']
    #         ph0_1 = self.dataset.get_phase_0(voxel)
    #         ph1_1 = self.dataset.get_phase_1(voxel)
    #
    #         data = [[data1], ]
    #         self.view.set_data(data)
    #         self.view.update(no_draw=True, set_scale=not self._scale_initialized)
    #
    #         if not self._scale_initialized:
    #             self._scale_initialized = True
    #
    #         # we take this opportunity to ensure that our phase values reflect
    #         # the values in the block.
    #         self.view.set_phase_0(ph0_1, absolute=True, no_draw=True, index=[0])
    #         self.view.set_phase_1(ph1_1, absolute=True, no_draw=True, index=[0])
    #
    #         self.view.canvas.draw()
    #
    #         # Calculate the new area after phasing
    #         area, rms = self.view.calculate_area()
    #         self.top.statusbar.SetStatusText(self.build_area_text(area[0], rms[0], plot_label='A'), 3)

    #=======================================================
    #
    #           Internal Helper Functions
    #
    #=======================================================

    def set_check_boxes(self):
        """
        This method only refreshes the checkboxes in the current checklist
        widget.

        """
        voxel   = self.voxel
        num     = self.list_svd_results.GetItemCount()
        svd_output = self.block.get_svd_output(voxel)
        for i in range(num):
            if i < self.list_svd_results.GetItemCount():
                index = int(self.list_svd_results.GetItemText(i))-1
                self.list_svd_results.SetItemImage(i, svd_output.in_model[index])


    def set_plot_c(self):
        data1 = self.view.all_axes[0].lines[0].get_ydata()
        data2 = self.view.all_axes[1].lines[0].get_ydata()
        data3 = self.plot_C_function(data1, data2)
        self.view.all_axes[2].lines[0].set_ydata(data3)

        view_data1 = self.view.get_data(0)
        view_data2 = self.view.get_data(1)
        view_data3 = self.plot_C_function(view_data1, view_data2)
        self.view.set_data_direct(view_data3, 2)

    def svd_checklist_update(self, dynamic=False):
        """
        This method totally rebuilds the result set in the checklist widget.

        Take the hlsvd results for the current voxel and set them into the
        checklist widget. If the spectral tab hlsvd water filter is on and
        has checked the "Apply Threshold" box, then we modify (and save) the
        index values according to the threshold.

        """
        if dynamic: return

        voxel = self.voxel[0:3]

        svd_output = self.block.get_svd_output(voxel)

        amp = svd_output.amplitudes
        dam = svd_output.damping_factors
        fre = svd_output.frequencies
        pha = svd_output.phases
        in_model = svd_output.in_model
        nsvd = len(svd_output)

        ppm = self.dataset.resppm - (fre*1000.0/self.dataset.frequency)

        # Update the list_svd_results widget
        if sum(amp) == 0:
            in_model.fill(False)

        res = {}
        self.list_svd_results.DeleteAllItems()
        for i in range(nsvd):
            res[i] = (i + 1, float(ppm[i]), float(fre[i]*1000), float(dam[i]), float(pha[i]), float(amp[i]))
            index = self.list_svd_results.InsertItem(i,' '+str(res[i][0])+' ')
            self.list_svd_results.SetItem(index, 1, '%.2f'%(res[i][1])) # bjs_ccx
            self.list_svd_results.SetItem(index, 2, '%.1f'%(res[i][2])) # bjs_ccx
            self.list_svd_results.SetItem(index, 3, '%.1f'%(res[i][3])) # bjs_ccx
            self.list_svd_results.SetItem(index, 4, '%.1f'%(res[i][4])) # bjs_ccx
            self.list_svd_results.SetItem(index, 5, '%.1f'%(res[i][5])) # bjs_ccx
            self.list_svd_results.CheckItem(index, check=in_model[i])
            self.list_svd_results.SetItemData(index, i)

        self.list_svd_results.itemDataMap = res


    def on_voxel_change(self, voxel, dynamic=False):
        # this just updates widgets that vary based on the voxel number
        # selection. We do not update plot here because that is only done
        # for the active tab in the inner notebook.
        freq_shift = self.dataset.get_frequency_shift(voxel)
        phase_0    = self.dataset.get_phase_0(voxel)
        phase_1    = self.dataset.get_phase_1(voxel)
        self.FloatFrequency.SetValue(freq_shift)
        self.FloatPhase0.SetValue(phase_0)
        self.FloatPhase1.SetValue(phase_1)

        self.SliderDataPoints.SetValue(int(self.block.get_data_point_count(voxel)))
        self.SliderSingularValues.SetValue(int(self.block.get_signal_singular_value_count(voxel)))

        self.svd_checklist_update(dynamic=dynamic)

    def _apply_hlsvd(self):
        # Updates the plot in response to changes in the HLSVD inputs.
        # This exists just so that we can call it via wx.CallAfter().
        voxel = self.voxel

        n_data_points = self.SliderDataPoints.GetValue()
        n_singular_values = self.SliderSingularValues.GetValue()

        self.block.set.svd_last_n_data_points = n_data_points
        self.block.set.svd_last_n_singular_values = n_singular_values

        self.block.set_data_point_count(n_data_points, voxel)
        self.block.set_signal_singular_value_count(n_singular_values, voxel)
        self.block.set_do_fit(True, voxel)
        self.process_and_plot(no_draw=True)
        self.set_check_boxes()

