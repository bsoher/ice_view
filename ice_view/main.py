#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.

# Dependencies
#
# numpy
# scipy
# nibabel
# wxpython
# matplotlib
# - pyparsing (for Matplotlib)
# - python-dateutil (for Matplotlib)
# pydicom 


# Python modules
import os
import struct

# 3rd party modules
import wx
import wx.adv as wx_adv
import wx.lib.agw.aui as aui        # NB. wx.aui version throws odd wxWidgets exception on Close/Exit
import numpy as np

# Our modules
import ice_view.util_menu as util_menu
import ice_view.util_import as util_import
import ice_view.dialog_export as dialog_export
import ice_view.mrsi_dataset as mrsi_dataset
import ice_view.mrsi_data_raw as mrsi_data_raw
import ice_view.default_content as default_content
import ice_view.notebook_ice_view as notebook_ice_view
import ice_view.util_ice_view_config as util_ice_view_config

import ice_view.common.misc as misc
import ice_view.common.export as export
import ice_view.common.wx_util as wx_util
import ice_view.common.common_dialogs as common_dialogs

from wx.lib.embeddedimage import PyEmbeddedImage

Mondrian = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAHFJ"
    "REFUWIXt1jsKgDAQRdF7xY25cpcWC60kioI6Fm/ahHBCMh+BRmGMnAgEWnvPpzK8dvrFCCCA"
    "coD8og4c5Lr6WB3Q3l1TBwLYPuF3YS1gn1HphgEEEABcKERrGy0E3B0HFJg7C1N/f/kTBBBA"
    "+Vi+AMkgFEvBPD17AAAAAElFTkSuQmCC")


    

class Main(wx.Frame):
    def __init__(self, position, size, fname=None):
        # Create a frame using values from our INI file.
        self._left,  self._top    = position
        self._width, self._height = size
    
        style = wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX | \
                wx.MAXIMIZE_BOX | wx.SYSTEM_MENU | wx.RESIZE_BORDER | \
                wx.CLIP_CHILDREN

        wx.Frame.__init__(self, None, wx.ID_ANY, default_content.APP_NAME,
                          (self._left, self._top),
                          (self._width, self._height), style)

        # GUI Creation ----------------------------------------------

        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.SetIcon(Mondrian.GetIcon())

        self.statusbar = self.CreateStatusBar(4, 0)
        self.statusbar.SetStatusText("Ready")

        bar = util_menu.IceViewMenuBar(self)
        self.SetMenuBar(bar)
        util_menu.bar = bar

        self.build_panes()
        self.bind_events()

        if fname is not None:
            self.load_on_start(fname)
            #wx.CallAfter(self.load_on_start, fname)

        
    def build_panes(self):
        
        self.notebook_ice_view = notebook_ice_view.NotebookIceView(self)

        # create center pane
        self._mgr.AddPane(self.notebook_ice_view, 
                          aui.AuiPaneInfo().
                          Name("notebook_ice_view").
                          CenterPane().
                          PaneBorder(False))
                          
        # "commit" all changes made to AuiManager
        self._mgr.Update()                          
                        

    def bind_events(self):
        self.Bind(wx.EVT_CLOSE, self.on_self_close)
        self.Bind(wx.EVT_SIZE, self.on_self_coordinate_change)
        self.Bind(wx.EVT_MOVE, self.on_self_coordinate_change)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)


    def on_erase_background(self, event):
        event.Skip()


    ##############                                    ############
    ##############       Menu handlers are below      ############
    ##############       in the order they appear     ############
    ##############             on the menu            ############
    ##############                                    ############

    ############    IceView menu

    def on_import_data_crt(self, event):

        ini_name = "import_data_crt"
        default_path = util_ice_view_config.get_path(ini_name)
        msg = 'Select file with Processed CRT Data'
        filetype_filter = "(*.npy, *.*)|*.npy;*.*"

        fname = common_dialogs.pickfile(message=msg,
                                        default_path=default_path,
                                        filetype_filter=filetype_filter)
        msg = ""
        if fname:
            try:
                crt_dat = np.load(fname)
                if crt_dat.shape == (512,24,24):
                    crt_dat = np.swapaxes(crt_dat,0,2)
                if len(crt_dat.shape) != 3:
                    msg = 'Error (import_data_crt): Wrong Dimensions, arr.shape = %d' % len(crt_dat.shape)
                elif crt_dat.dtype not in [np.complex64, np.complex128]:
                    msg = 'Error (import_data_crt): Wrong Dtype, arr.dtype = '+str(crt_dat.dtype)
            except Exception as e:
                msg = """Error (import_data_crt): Exception reading Numpy CRT dat file: \n"%s"."""%str(e)

            if msg:
                common_dialogs.message(msg, default_content.APP_NAME+" - Import CRT Data", common_dialogs.E_OK)
            else:
                path, _ = os.path.split(fname)

                # bjs hack
                crt_dat = crt_dat * np.exp(-1j*np.pi*90/180)
                crt_dat *= 1e9

                raw = mrsi_data_raw.MrsiDataRaw()
                raw.data_sources = [fname,]
                raw.data = crt_dat
                raw.sw = 1250.0
                raw.frequency = 123.9
                raw.resppm = 4.7
                raw.seqte = 110.0
                raw.seqtr = 2000.0

                dataset = mrsi_dataset.dataset_from_raw(raw)

                self.notebook_ice_view.Freeze()
                self.notebook_ice_view.add_ice_view_tab(dataset=dataset)
                self.notebook_ice_view.Thaw()
                self.notebook_ice_view.Layout()
                self.update_title()

                path, _ = os.path.split(fname)
                util_ice_view_config.set_path(ini_name, path)

    
    def on_open(self, event):
        wx.BeginBusyCursor()

        ini_name = "save_viff"
        default_path = util_ice_view_config.get_path(ini_name)

        filetype_filter=default_content.APP_NAME+" (*.xml,*.xml.gz,*.viff,*.vif)|*.xml;*.xml.gz;*.viff;*.vif"
        filename = common_dialogs.pickfile(filetype_filter=filetype_filter,
                                            multiple=False,
                                            default_path=default_path)
        if filename:
            msg = ""
            try:
                importer = util_import.MrsiDatasetImporter(filename)
            except IOError:
                msg = """I can't read the file "%s".""" % filename
            except SyntaxError:
                msg = """The file "%s" isn't valid Vespa Interchange File Format.""" % filename

            if msg:
                common_dialogs.message(msg, "MRI_Timeseries - Open File", common_dialogs.E_OK)
            else:
                # Time to rock and roll!
                wx.BeginBusyCursor()
                ice_views = importer.go()
                wx.EndBusyCursor()    

                if ice_views:
                    dataset = ice_views[0]
    
                    self.notebook_ice_view.Freeze()
                    self.notebook_ice_view.add_ice_view_tab(dataset=dataset)
                    self.notebook_ice_view.Thaw()
                    self.notebook_ice_view.Layout()
                    self.update_title()
                    
                    path, _ = os.path.split(filename)
                    util_ice_view_config.set_path(ini_name, path)
                else:
                    msg = """The file "%s" didn't contain any MRI_Timeseries.""" % filename
                    common_dialogs.message(msg)
                
        wx.EndBusyCursor()                


    def on_save_ice_view(self, event, save_as=False):
        # This event is also called programmatically by on_save_as_viff().
        dataset = self.notebook_ice_view.active_tab.dataset

        filename = dataset.dataset_filename
        if filename and (not save_as):
            # This dataset already has a filename which means it's already
            # associated with a VIFF file. We don't bug the user for a 
            # filename, we just save it.
            pass
        else:
            if not filename:
                filename = dataset.data_sources[0]
            path, filename = os.path.split(filename)
            # The default filename is the current filename with the extension
            # changed to ".xml".
            filename = os.path.splitext(filename)[0] + ".xml"

            filename = common_dialogs.save_as("Save As XML/VIFF (Vespa Interchange Format File)",
                                              "VIFF/XML files (*.xml)|*.xml",
                                              path, filename)

        if filename:
            dataset.dataset_filename = filename
        
            self._save_viff(dataset)
        
        
    def on_save_as_ice_view(self, event):
        self.on_save_ice_view(event, True)        
        
        
    def on_close_ice_view(self, event):
        self.notebook_ice_view.close_ice_view()


    def load_on_start(self, fname):

        msg=''
        if isinstance(fname, np.ndarray):
            crt_dat = fname
        elif isinstance(fname, str):
            if os.path.exists(fname):
                try:
                    crt_dat = np.load(fname)
                except Exception as e:
                    msg = """Error (load_on_start): Exception reading Numpy CRT dat file: \n"%s"."""%str(e)
                if msg:
                    common_dialogs.message(msg, default_content.APP_NAME+" - Load on Start", common_dialogs.E_OK)
                    return
        else:
            # TODO bjs - better error/warning reporting
            return

        if crt_dat.shape == (512,24,24):
            crt_dat = np.swapaxes(crt_dat,0,2)
        if len(crt_dat.shape) != 3:
            msg = 'Error (load_on_start): Wrong Dimensions, arr.shape = %d' % len(crt_dat.shape)
        elif crt_dat.dtype not in [np.complex64, np.complex128]:
            msg = 'Error (load_on_start): Wrong Dtype, arr.dtype = '+str(crt_dat.dtype)
        
        if msg:
            common_dialogs.message(msg, default_content.APP_NAME+" - Load on Start", common_dialogs.E_OK)
        else:
            path, _ = os.path.split(fname)

            # bjs hack
            crt_dat = crt_dat * np.exp(-1j*np.pi*90/180)

            raw = mrsi_data_raw.MrsiDataRaw()
            raw.data_sources = [fname,]
            raw.data = crt_dat
            raw.sw = 1250.0
            raw.frequency = 123.9
            raw.resppm = 4.7
            raw.seqte = 110.0
            raw.seqtr = 2000.0

            dataset = mrsi_dataset.dataset_from_raw(raw)

            self.notebook_ice_view.Freeze()
            self.notebook_ice_view.add_ice_view_tab(dataset=dataset)
            self.notebook_ice_view.Thaw()
            self.notebook_ice_view.Layout()
            self.update_title()



    ############    View  menu
    
    # View options affect only the dataset and so it's up to the
    # experiment notebook to react to them.

    def on_menu_view_option(self, event):
        self.notebook_ice_view.on_menu_view_option(event)
        
    # def on_menu_view_output(self, event):
    #     self.notebook_ice_view.on_menu_view_output(event)
    #
    # def on_menu_output_by_slice(self, event):
    #     self.notebook_ice_view.on_menu_output_by_slice(event)
    #
    # def on_menu_output_by_voxel(self, event):
    #     self.notebook_ice_view.on_menu_output_by_voxel(event)
    #
    # def on_menu_output_to_dicom(self, event):
    #     self.notebook_ice_view.on_menu_output_to_dicom(event)


    ############    Help menu

    def on_user_manual(self, event):
        pass
#        path = misc.get_install_directory()
#        path = os.path.join(path, "docs", "ice_view_user_manual.pdf")
#        wx_util.display_file(path)


    def on_help_online(self, event):
        pass 


    def on_about(self, event):

        version = misc.get_application_version()
        
        bit = str(8 * struct.calcsize('P')) + '-bit Python'
        info = wx_adv.AboutDialogInfo()
        info.SetVersion(version)  
        info.SetCopyright("Copyright 2023, Brian J. Soher. All rights reserved.")
        info.SetDescription(default_content.APP_NAME+" - view and tweak SI data. \nRunning on "+bit)
        wx_adv.AboutBox(info)


    def on_show_inspection_tool(self, event):
        wx_util.show_wx_inspector(self)



    ############    Global Events
    
    def on_self_close(self, event):
        # I trap this so I can save my coordinates
        config = util_ice_view_config.Config()

        config.set_window_coordinates("main", self._left, self._top, 
                                      self._width, self._height)
        config.write()
        self.Destroy()


    def on_self_coordinate_change(self, event):
        # This is invoked for move & size events
        if self.IsMaximized() or self.IsIconized():
            # Bah, forget about this. Recording coordinates doesn't make sense
            # when the window is maximized or minimized. This is only a
            # concern on Windows; GTK and OS X don't produce move or size
            # events when a window is minimized or maximized.
            pass
        else:
            if event.GetEventType() == wx.wxEVT_MOVE:
                self._left, self._top = self.GetPosition()
            else:
                # This is a size event
                self._width, self._height = self.GetSize()


    
    ##############
    ##############   Public  functions  alphabetized  below
    ##############

    def update_title(self):
        """Updates the main window title to reflect the current dataset."""
        name = ""
        
        # Create an appropriate name for whatever is selected.
        tab = self.notebook_ice_view.active_tab
        if tab:
            filename = tab.dataset.dataset_filename
            fname = " - " + os.path.split(filename)[1] 

        self.SetTitle(default_content.APP_NAME + fname)
        
        
    ##############
    ##############   Private  functions  alphabetized  below
    ##############

    def _save_viff(self, dataset):    
        msg = ""
        filename = dataset.dataset_filename
        comment  = "Processed in IceView version "+misc.get_application_version()
        try:
            export.export(filename, [dataset], db=None, comment=comment, compress=False)
            path, _ = os.path.split(filename)
            util_ice_view_config.set_path("save_viff", path)
        except IOError:
            msg = """I can't write the file "%s".""" % filename

        if msg:
            common_dialogs.message(msg, style=common_dialogs.E_OK)
        else:
            # dataset.filename is an attribute set only at run-time to maintain
            # the name of the VIFF file that was read in rather than deriving 
            # a filename from the raw data filenames with *.xml appended. We 
            # set it here to indicate the current name that the dataset has 
            # been saved to VIFF file as.
            dataset.dataset_filename = filename
                    
        self.update_title()



#------------------------------------------------------------------------------

def main(fname=None):

    # This function is for profiling with cProfile

    fname = r'D:\Users\bsoher\code\repo_github\ice_view\ice_view\test_data\2023_10_12_bjsDev_oct12_slasr_crt\dat_metab_post_hlsvd.npy'
    fname = None

    app = wx.App(0)
    
    # The app name must be set before the call to GetUserDataDir() below.
    app.SetAppName(default_content.APP_NAME)
    
    # Create the data directory if necessary - this version creates it in 
    # the Windows 'AppData/Local' location as opposed to the call to
    # wx.StandardPaths.Get().GetUserDataDir() which returns '/Roaming'
     
    data_dir = misc.get_data_dir()
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    
    # My settings are in the INI filename defined in 'default_content.py'
    config = util_ice_view_config.Config()
    position, size = config.get_window_coordinates("main")

    frame = Main(position, size, fname=fname)
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()    



if __name__ == "__main__":

    main()    
    
