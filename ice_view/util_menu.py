#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules
import wx

# Our modules
import ice_view.util_ice_view_config as util_ice_view_config
import ice_view.common.menu as common_menu


########################################################################
# This is a collection of menu-related constants, functions and utilities. 
# The function that builds the menu bar lives here, as does the menu 
# definition.
########################################################################


class ViewIds(common_menu.IdContainer):
    """A container for the ids of all of the menu items to which we need 
    explicit references.
    """
    ZERO_LINE_SHOW = "replace me"
    ZERO_LINE_TOP = "replace me"
    ZERO_LINE_MIDDLE = "replace me"
    ZERO_LINE_BOTTOM = "replace me"

    XAXIS_SHOW = "replace me"

    DATA_TYPE_REAL      = "replace me"
    DATA_TYPE_IMAGINARY = "replace me"
    DATA_TYPE_MAGNITUDE = "replace me"

    AREA_CALC_PLOT_A = "replace me"
    AREA_CALC_PLOT_B = "replace me"
    AREA_CALC_PLOT_C = "replace me"

    PLOT_C_FUNCTION_NONE = "replace me"
    PLOT_C_FUNCTION_A_MINUS_B = "replace me"
    PLOT_C_FUNCTION_B_MINUS_A = "replace me"
    PLOT_C_FUNCTION_A_PLUS_B = "replace me"

    USER_BUTTON_PHASING = "replace me"
    USER_BUTTON_AREA = "replace me"

    # CMAP_AUTUMN = "replace me"
    # CMAP_BLUES  = "replace me"
    # CMAP_JET    = "replace me"
    # CMAP_RDBU   = "replace me"
    # CMAP_GRAY   = "replace me"
    # CMAP_RDYLBU = "replace me"

    # MASK_TO_MOSAIC = "replace me"
    # FITS_TO_MOSAIC = "replace me"
    # MASK_TO_STRIP = "replace me"
    # FITS_TO_STRIP = "replace me"
    # MRI_TO_VSTRIP = "replace me"
    # MRI_TO_HSTRIP = "replace me"
    #
    # VIEW_TO_PNG = "replace me"
    # VIEW_TO_SVG = "replace me"
    # VIEW_TO_PDF = "replace me"
    # VIEW_TO_EPS = "replace me"
    #
    # VIEW_TO_CSV1 = "replace me"
    # VIEW_TO_CSV2 = "replace me"
    # VIEW_TO_DICOM = "replace me"


# When main creates an instance of PriorsetMenuBar(), it sets the variable
# below to that instance. It's a convenience. It's the same as 
# wx.GetApp().GetTopWindow().GetMenuBar(), but much easier to type.
bar = None


class IceViewMenuBar(common_menu.TemplateMenuBar):
    """
    A subclass of wx.MenuBar that adds some app-specific functions
    and constants.
    
    There should be only one instance of this class per invocation of the 
    app. It's a singleton class.
    """
    
    def __init__(self, main):
        common_menu.TemplateMenuBar.__init__(self, main)
        
        ViewIds.init_ids()

        # _get_menu_data() is called just once, right here. 
        ice_view, view, help = _get_menu_data(main)

        # Build the top-level menus that are always present. 
        ice_view = common_menu.create_menu(main, "File", ice_view)
        view     = common_menu.create_menu(main, "&View", view)
        help     = common_menu.create_menu(main, "&Help", help)

        for menu in (ice_view, view, help):
            self.Append(menu, menu.label)

        ViewIds.enumerate_booleans(self.view_menu)


# ================    Module Internal Use Only    =======================


def _get_menu_data(main):
    # Note that wx treats the ids wx.ID_EXIT and wx.ID_ABOUT specially by 
    # moving them to their proper location on the Mac. wx will also change
    # the text of the ID_EXIT item to "Quit" as is standard under OS X. 
    # Quit is also the standard under Gnome but unfortunately wx doesn't seem
    # to change Exit --> Quit there, so our menu looks a little funny under
    # Gnome.

    study = (
                # ("O&pen...\tCTRL+O", (
                #     ("IceView XML", main.on_open_xml),
                #     common_menu.SEPARATOR,
                #     ("ICE Spectroscopy IceHead/spe File", main.on_open_spe),
                #     ("ICE Spectroscopy DICOM File", main.on_open_dicom))),
                ("O&pen ICE SPE File\tCTRL+O",   main.on_open_spe),
                ("O&pen ICE DICOM File\tCTRL+D", main.on_open_dicom),
                ("Open IceView XML File", main.on_open_xml),
                common_menu.SEPARATOR,
                ("S&ave\tCTRL+S",       main.on_save_ice_view),
                ("S&ave As...",         main.on_save_as_ice_view),
                common_menu.SEPARATOR,
                ("Close\tCTRL+W",       main.on_close_ice_view),
                #common_menu.SEPARATOR,
                #("Import Processed CRT Data", main.on_import_data_crt),
                common_menu.SEPARATOR,
                ("&Exit",               main.on_self_close))

    view = (    
                ("Zero Line", (
                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.ZERO_LINE_SHOW),
                    common_menu.SEPARATOR,
                    ("Top",    main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_TOP),
                    ("Middle", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_MIDDLE),
                    ("Bottom", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.ZERO_LINE_BOTTOM))),
                ("Show X-Axis", main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.XAXIS_SHOW),
#                ("X-Axis", (
#                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.XAXIS_SHOW),
#                    ("Show",   main.on_menu_view_option, wx.ITEM_CHECK, ViewIds.XAXIS_SHOW))),
                common_menu.SEPARATOR,
                ("Data Type", (
                    ("Real",      main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.DATA_TYPE_REAL),
                    ("Imaginary", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.DATA_TYPE_IMAGINARY),
                    ("Magnitude", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.DATA_TYPE_MAGNITUDE),
                )),
                common_menu.SEPARATOR,
                ("Area Calculation", (
                    ("From Plot A", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.AREA_CALC_PLOT_A),
                    ("From Plot B", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.AREA_CALC_PLOT_B),
                    ("From Plot C", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.AREA_CALC_PLOT_C),
                )),
                ("Plot C Function", (
                    ("None", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.PLOT_C_FUNCTION_NONE),
                    (
                    "Residual A-B", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.PLOT_C_FUNCTION_A_MINUS_B),
                    (
                    "Residual B-A", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.PLOT_C_FUNCTION_B_MINUS_A),
                    ("Sum A+B", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.PLOT_C_FUNCTION_A_PLUS_B),
                )),
                ("User Button Function", (
                    ("Automatic Phasing", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.USER_BUTTON_PHASING),
                    ("Output Area Value", main.on_menu_view_option, wx.ITEM_RADIO, ViewIds.USER_BUTTON_AREA),
                )),
                )

    help = (
                ("&User Manual",          main.on_user_manual),
                ("&About", main.on_about, wx.ITEM_NORMAL, wx.ID_ABOUT),
           )

    if util_ice_view_config.Config().show_wx_inspector:
        help = list(help)
        help.append(common_menu.SEPARATOR)
        help.append( ("Show Inspection Tool", main.on_show_inspection_tool) )
    
    return (study, view, help)          

