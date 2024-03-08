#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules

import os
import sys

# 3rd party modules 
import wx
import wx.html
#import wx.aui as aui
import wx.lib.agw.aui as aui        # NB. wx.aui version throws odd wxWidgets exception on Close/Exit


# Our modules
import ice_view.default_content as default_content
import ice_view.tab_ice_view as tab_ice_view
import ice_view.common.wx_util as wx_util
import ice_view.common.notebook_base as notebook_base



class NotebookIceView(notebook_base.BaseAuiNotebook):
    
    # Need to check if we are in a PyInstaller bundle here
    if getattr(sys, 'frozen', False):
        _path = sys._MEIPASS
    else:
        # Don't want app install directory here in case we are running this as an
        # executable script, in which case we get the python27/Scripts directory.
        _path = os.path.dirname(tab_ice_view.__file__)
    
    _path = os.path.join(_path, "ice_viewscreen.png")
    
    WELCOME_TAB_TEXT = """
    <html><body>
    <h1>Welcome to "%s"</h1>
    <img src="%s" alt="Spectroscopic Imaging Viewer" />
    <p><b>Currently there are no SI datasets loaded.</b></p>
    <p>You can use the File menu to browse for data.</p>
    </body></html>
    """ % (default_content.APP_NAME, _path)
    # I tidy up my namespace by deleting this temporary variable.
    del _path
    
    
    def __init__(self, top):

        notebook_base.BaseAuiNotebook.__init__(self, top)

        self.top    = top
        self.count  = 0
        
        self.show_welcome_tab()

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_tab_close)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.on_tab_closed)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
        

    #=======================================================
    #
    #           Global and Menu Event Handlers 
    #
    #=======================================================

    def on_menu_view_option(self, event):
        if self.active_tab:
            self.active_tab.on_menu_view_option(event)

    # def on_menu_view_output(self, event):
    #     if self.active_tab:
    #         self.active_tab.on_menu_view_output(event)
    #
    # def on_menu_output_by_slice(self, event):
    #     self.active_tab.on_menu_output_by_slice(event)
    #
    # def on_menu_output_by_voxel(self, event):
    #     self.active_tab.on_menu_output_by_voxel(event)
    #
    # def on_menu_output_to_dicom(self, event):
    #     self.active_tab.on_menu_output_to_dicom(event)


    def on_tab_changed(self, event):

        self._set_title()
            
        if self.active_tab:
            self.active_tab.on_activation()
            
            
    def on_tab_close(self, event):
        """
        This is a two step event. Here we give the user a chance to cancel 
        the Close action. If user selects to continue, then the on_tab_closed()
        event will also fire.  
        
        """
        msg = "Are you sure you want to close this IceView?"
        if wx.MessageBox(msg, "Close IceView", wx.YES_NO, self) != wx.YES:
            event.Veto()


    def on_tab_closed(self, event):        
        """
        At this point the tab is already closed and the dataset removed from
        memory.        
        """
        if not self.tabs:
            self.show_welcome_tab()

        self._set_title()


    #=======================================================
    #
    #           Public methods shown below
    #             in alphabetical order 
    #
    #=======================================================

    def add_ice_view_tab(self, dataset=None):

        # If the welcome tab is open, close it.
        if self.is_welcome_tab_open:
            self.remove_tab(index=0)

        self.count += 1
        name = "IceView%d" % self.count

        # create new notebook tab with process controls 
        tab = tab_ice_view.TabIceView(self, self.top, dataset)
        self.AddPage(tab, name, True)


    def close_ice_view(self):
        if self.active_tab:
            wx_util.send_close_to_active_tab(self)


    # def set_mask(self, mask):
    #     if self.active_tab:
    #         self.active_tab.set_mask(mask)

    #=======================================================
    #
    #           Internal methods shown below
    #             in alphabetical order 
    #
    #=======================================================

    def _set_title(self):
        title = default_content.APP_NAME

        if self.active_tab:
            tab = self.active_tab

            if tab.dataset:
                title += " - " + tab.dataset.dataset_filename

        wx.GetApp().GetTopWindow().SetTitle(title)


