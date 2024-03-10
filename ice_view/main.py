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

from ice_view.common.common_dialogs import pickfile, save_as, message, E_OK

from wx.lib.embeddedimage import PyEmbeddedImage





class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, frame):
        wx.FileDropTarget.__init__(self)
        self.frame = frame

    def OnDropFiles(self, x, y, filenames):
        if not filenames:
            return
        item = filenames[0]
        if os.path.isfile(item):
            txt0 = "Valid file path dropped"
            txt1 = str(item)
            # self.frame.TextSourceDirectory.SetLabelText(item)
            # self.frame.path = item
        else:
            txt0 = "Object dropped was INVALID file path"
            txt1 = "Try File->Import"

        self.frame.statusbar.SetStatusText((txt0), 0)
        self.frame.statusbar.SetStatusText((txt1), 1)

        # self.frame.update_log(txt)

        return True

    

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

        self.SetIcon(IceViewIcon5.GetIcon())

        self.statusbar = self.CreateStatusBar(4, 0)
        self.statusbar.SetStatusText("Ready")

        bar = util_menu.IceViewMenuBar(self)
        self.SetMenuBar(bar)
        util_menu.bar = bar

        self.build_panes()
        self.bind_events()

        self.SetDropTarget(MyFileDropTarget(self))

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

    def get_ice_pair(self, fname):
        """ returns a hdr/dat filename pair based on ICE output rules"""
        path = os.path.dirname(fname)
        base, ext = fname.split('.')
        num = base[-5:]

        if ext.lower() == 'icehead':
            fname_hdr = fname
            # we have hdr, need binary fname
            if base[-10:-5]=='_spe_':
                fname_dat = os.path.join(path,'WriteToFile_'+num+'.spe')
            elif base[-9:-5]=='_sc_':
                fname_dat = fname_dat = os.path.join(path,'WriteToFile_'+num+'.sc')
            elif base[-10:-5] == '_ima_':
                fname_dat = fname_dat = os.path.join(path,'WriteToFile_' + num + '.ima')
            else:
                msg = 'File name does not contain "spe", "sc" of "ima", returning! - \n' + fname
                message(msg, style=E_OK)
                raise(ValueError(msg))
        elif ext.lower() in ['spe', 'sc', 'ima']:
            # we have binary, need hdr fname
            fname_dat = fname
            fname_hdr = fname_dat = os.path.join(path,'MiniHead_'+ext.lower()+'_'+num+'.IceHead')
        else:
            msg = 'This is not a *.spe, *.sc, *.ima or *.IceHead file, returning! - \n'+fname
            message(msg, style=E_OK)
            raise(ValueError(msg))

        # we have both ICE files
        return fname_hdr, fname_dat

    def on_open_spe(self, event):

        ini_name = "open_spe"
        default_path = util_ice_view_config.get_path(ini_name)
        msg = 'Select ICE *.spe or *.IceHead Spectroscopy file'
        filetype_filter = "(*.spe, *.IceHead, *.*)|*.spe;*.IceHead;*.*"

        fname = pickfile(message=msg, default_path=default_path, filetype_filter=filetype_filter)
        msg = ""
        if fname:
            try:
                # - parse Icehead, get data params
                fname_hdr, fname_dat = self.get_ice_pair(fname)

                if not os.path.isfile(fname_hdr):
                    msg = 'File does not exist, returning! - \n' + fname_hdr
                    message(msg, style=E_OK)
                    raise (ValueError(msg))
                if not os.path.isfile(fname_dat):
                    msg = 'File does not exist, returning! - \n' + fname_dat
                    message(msg, style=E_OK)
                    raise (ValueError(msg))

                # - create MrsiDataRaw()


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
                message(msg, default_content.APP_NAME+" - Import CRT Data", E_OK)
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

    def on_open_dicom(self, event):

        ini_name = "open_dicom"
        default_path = util_ice_view_config.get_path(ini_name)
        msg = 'Select ICE DICOM Spectroscopy file'
        filetype_filter = "(*.dcm, *.*)|*.dcm;*.*"

        fname = pickfile(message=msg, default_path=default_path, filetype_filter=filetype_filter)
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
                message(msg, default_content.APP_NAME+" - Import CRT Data", E_OK)
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
    
    def on_open_xml(self, event):
        wx.BeginBusyCursor()

        ini_name = "save_viff"
        default_path = util_ice_view_config.get_path(ini_name)

        filetype_filter=default_content.APP_NAME+" (*.xml,*.xml.gz,*.viff,*.vif)|*.xml;*.xml.gz;*.viff;*.vif"
        filename = pickfile(filetype_filter=filetype_filter,
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
                message(msg, "MRI_Timeseries - Open File", E_OK)
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
                    message(msg)
                
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

            filename = save_as("Save As XML/VIFF (Vespa Interchange Format File)",
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
                    message(msg, default_content.APP_NAME+" - Load on Start", E_OK)
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
            message(msg, default_content.APP_NAME+" - Load on Start", E_OK)
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
            message(msg, style=E_OK)
        else:
            # dataset.filename is an attribute set only at run-time to maintain
            # the name of the VIFF file that was read in rather than deriving 
            # a filename from the raw data filenames with *.xml appended. We 
            # set it here to indicate the current name that the dataset has 
            # been saved to VIFF file as.
            dataset.dataset_filename = filename
                    
        self.update_title()




IceViewIcon5 = PyEmbeddedImage(
    b'iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAAAXNSR0IArs4c6QAAAARnQU1B'
    b'AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAABuRSURBVHhe7V13jBXV256Ze3eBBWkq'
    b'SBNhAYHYAohGEHsJYkmMDVFjLNEYNcEWxfaHJSY2/Nk1lhhjgrFFY/0EFSsKa0EswKKA4C6w'
    b'1pVl996Z73nOPeflzNy5u8Cy7L3ceZLdOWfamTnvc95yylw3AJwEZQtPbxOUKRIClDkSApQ5'
    b'EgKUORIClDlKJQoIlixZEvz2229ev379svvtt5/nAvpYgnagJAjw2WefZQ855BBqKwo9qKmp'
    b'yR5wwAFpdTBBu1D0JqClpSV49tlnKXjX89Tjuq+99hoTSf/FdkDRawCofX/w4MGKALk9jjNx'
    b'4sTgnXfeCXr37p34MO1E0Vfgr7/+SoIq4Ruzv2DBAmft2rW+yiRoF4qeALW1tUpDUfiplGdI'
    b'4IIAohESbDuKnQDBqlWr1DNS+Nms7xiLtWLFikQDbAcUNQGam5uD77//XgnaFj7x119/JVHA'
    b'dkBREyCbzbobN25UgjbCN37ADz/8kEWEkGiBdqKoCYBWnv3ggw9EyMYPIP788880CFLUz18K'
    b'KOoKRAtPNzQ0qGc0wqcpINatW+fDRGRUJsE2o6gJ8N9//7XoJISfcjKZrHRbfPjhhy40RBIJ'
    b'tBNFTYD6+npKO8gJP+OMGzeuoUePHsYTpPBTuWSCbUVREwBCr8TGha1nNpg5c2bVkCFDpNU3'
    b'NjaKhkiwbShqAoi+B6qrq92BAwd2g93Xe5SG0KkE24piJkCwevXqJp1WYaDneZl0Oi1RATRD'
    b'hU4m2EYUMwFchHoi4E2bNvm77rpry5gxY/SesIZIsG0oahPg+7709u27775Ov379KnbZZRd5'
    b'ZmiIjdgkJGgHSsYHQOv3Kisr04wGDP7++29qiCQUbAeKlgAQdPbnn38WLx/agJ1BPnwAYQDO'
    b'SXyAdqJoCcBu3oaGBonzU6lUBhogi0hAtIKeIZSgHSjaGoT2d9HqhQC9evXKdu3a1R00aJC0'
    b'+j/++IPaIBkQageKugmZkT+iurq6Evk0TYHB0qVLOR7QphPIUcOVK1cGa9as4bmJ02ihmE2A'
    b'v3HjRlvd5zl7EH6FrSXiAD8hmD17tjN06FBqD2fOnDlkUEICjaIlwL///tsyd+5c1QdsIYAT'
    b'KF2BNBM6WRDffPNN9pprrjHv6Z5xxhkenMvofcsWRUsADgX/999/8nxG8LvssosIj1GiHSrG'
    b'IPjggw8USXC9cRrdjz/+mPsSLQAULQG0apfn69mzpxL84MGDu6odQE3NokxjY+PmwYEImpqa'
    b'nE8//VTdgwNKxn+YP3++C4KpdLmjaAkQBew3BQ8/cLNnWFu7woUfUPAdEEY6L7/8skrbiuKT'
    b'Tz5hN3OiAYCiJUBUtduCt5BCyy44ObSuro5aQ64zt0D04HJGkcqUOYqWAOvXr+dIYF4rTaVS'
    b'IQcOPIkjhgIIEBK+ta6AQ8klo/06EkVbCXAAQ+EdBKfIUFFRsQkbIUa8YsihtrZWtXIjfHtq'
    b'+Zo1a0ikPIKVG4qWAHqs30iX4Z/y2vr27RsaAIIzF9IINuAEql5DkMbJZLJK+IYwMAE0HYXZ'
    b'UyYoZh8gJJzKykpFgKqqKnsAKNCmIg/s/fvhhx/UwBFnEU2dOrVl4sSJnFWqjsNB9JEuez+g'
    b'aAkQUe3ubrvtpsI/I0CDTZs22YQQcDDJXj104IEHumPHjtU5x/nxxx8VMcodRUsACCek2qHG'
    b'47p83UJDwrg+A+0gLXzEiBHNe+65p9wTRErhr2jff0ehWCuAi0Lp7AlMy/c8j0K0VXesHf/7'
    b'77+defPm6Zzj7LXXXlWDBw/mLGOFZcuWZe11B+WKom0BcOBi43vOC8BGCFAoCvBz08nk/XBe'
    b'BuQRgdfU1HiNjY2JBtDbYkNUtfta8A7nBIwfP16k/s8//1CoeeEcrrdNSIDoIQMNoLMKvEer'
    b'I4nlgB1GgKVLl2YffPBB/5577gkWLFgQKzQbUPl20xYCdOvWrbK6uloEt3bt2lg1Xl9fTw/P'
    b'lOH26dOna48ePUL+QmICdhABuMZ/1KhRqcsvv9y7+uqr3YMOOigNEhSM3wlbtR955JFe9+7d'
    b'xSTYkQCcPQo1zw7AhKixg1xOgRfZvkOwbt26Vp+hHNDhBIAggjvvvFOl0YrhzSs5uo888ojH'
    b'uf7qQD4C+xhCQA9RQCwBdIdRHGzhZ9mRVFVVFdIKMBNddLps0eEE+O677/znn3+eH3ZUw7Et'
    b'LUqTO88884xb6DMvtN8wGRKk2wInbO0QPWaAKEDU+1FHHeVC+J7uS7CJkac54gBz4vNrZSBb'
    b'fGEljI4mQDB//nyVYAM2wjITM2AaYssHUfhlkFgHDcIPTQ0vAIaRQi6zpsAmDmGTJA4wL/6T'
    b'Tz6ZHTFihMtP1d10002BXrG806BDCQAnS2bkNDe3ODfeeGPmvPPOg3xzslm0aBE4kd+EcdxD'
    b'5YvK5wgghKfOA3l8Tg9XB4C46wFO+BD1rgrBabhHqA9h9erVzBcU6FtvveVfdNFFKUQafAcX'
    b'psy75ZZbfJinnYYEHUqAuro6//XXX5dmN3XqVPfggw+WykMs7pIkOmuDH7CU62D/GcMroYMM'
    b'bv/+/eVYbW1tM1RznkbQWkaB4wi8vkuXLtk999xTytMkkXvZgHbwZ8+enVNV0BzpdEptH330'
    b'0dRXX30Va7pKER1KALQw1XJyOSfgzFxbAGhhnJmjc2HY6nrAgAEuBc80BJkaOHCg9OhBUFw/'
    b'EBWir9cMKIwcOdLj9QgDKydMmGCbluh1Avggwbx585TvQu3BbgXzTG+//VYhzVNy6FACcC6+'
    b'TjqTJ092evfuTY/ernSXLU2nQ7AJQIFT8DorvgQBU5GKEoAjgezq1VmnT58+0ito3YampqAQ'
    b'4byqe7Is2H//8MMP32RM13vv/R8HmlS61NGRBAh+/fVXuf/o0aP9bt26uXvssUeoTJiJvGfg'
    b'QM6WTtlCxJA3qAOTkMI9REtYrTVgg9ZpjgfEmg96+1DzOuc406dPd2bNmiVlfPHFF/xSqRCs'
    b'lJFX+dsLcJScxYsX65wiABq1S1VOwYpweV4U8AsyUL9yjt3iCVs7FEDILOhZRMqBhB8gnj/M'
    b'RAoEyqsDOH1BTc0iuR4mJBgzZgxVhzwItJtOlTY6jABNTU2MnaUSBw0apFoazIA7bdo02W+r'
    b'agO0QFHZBB04nVRAXlptITLgHJ1SU8mV3ocz6FZXV8sBCD8d1R4E1funn34mN4bvAjPSO5gy'
    b'ZYre4zjLly/XqdJGhxEAtt376KOPdM5xoPpVWAcN4MEUqH0ENEBeTx5aLwUmz4YWbPfgBYwK'
    b'dFp1LlkqXmHjxo3NEJCQpmfPnqYMT/sDCoXIE1XviDqCLl26prjVu9T7YRNWTSWIDiNAQ0MD'
    b'Va3UMCpPqXQIL4sWKQJcuvTnZvb86awC5BmSzK677hrK2/0ACCXzFoeAAM7ChQt1Tt1Pp8Jp'
    b'aJo88hC4n5CEAGnA25QPMybnfvvtt+yu1rnSRYcRAPbVbtmB+bQLaxIqVY6tX7+hgo6czsai'
    b'X79+dhcue+XU9DCitraWnT4hguB+vL/ck7ZfJ7lETHwAOHqZf//9N0QegM6r7Nt///397t27'
    b'k7AeexRze5XmYvShc6WLDiMA4ntppQihSAC7pUnN0THUSUF0V7SRQgPYhPG0z2DDvgFNhmmq'
    b'AcyBaB9GKQwjddaAoan0IrIPQU9EDUBEIQ9/x0jPRShpdBgB7BBwwIABnMhh8kGvXr2khXGl'
    b'bnRcHk5Y7KIQgwgh6PGH3iOi1l20XEOQkPYA8siDe2VXr14tzwOnNUP1j6SL95DQEn5CKs5/'
    b'KTV0CAFQ/z58ABECv/CF8EvnHPYGSuabb77h1KxQK2QYppMKtgrfEmzYsCH09TB7KnmcxrEB'
    b'jeCBvPI8Y8eOTUGDqHrCc4SIuhUmIPQ+xYQOIQAq0f3pp5+koiEAVoDkI0JgOvQcsOnqE7G5'
    b'nFLhITuNy1utUDiBUY2gU+rakNQi2oLg48n1djgJE6BTCsHvv//eqgmAH+Tzc/fPP//8pvff'
    b'fz/Qw99FRYYOIQBUo19XV6dzakZu6KVhw2mTZV/UBEAthzQCzEdIaFDJYseJaBQRJZAt9EjZ'
    b'nBUUWljCZ7E/IAHfheRT58MZtFU+h6zFJESBBtBy0kknOUcccYQ3Y8aMrkcffbQ7fPhw97HH'
    b'HguammLXsnQKOoQAHKAxw8AEbH5IoLCltLsioPXr14cEGAFt+OaOA0DPBxAhQuWHahSN2n4v'
    b'NRtIpxlS2mVzNDLkA9Ac0SzpLMlrkynUgkH02OdGZJGdNWtW6uOPP4YCCVWxe8kll3gPP/ww'
    b'VyXJfToTHUIA2HBWlBAAjlSohUOl24TgGn/xCYho5VAn66QCNELoOK4PCdE+nS0QLVfKs/0B'
    b'Atom6sixTuQGdtnwYzIDBw4UbQKVbhNRsGDBguCll17yQDzjJ8g1xFVXXeV98cUXoX1RgIj+'
    b'woULM3PnznX4x5lVul63KzqEAJEBngCtLlTJUfKjldgC5m8E04mzEbqgb9++1AjmmrzVQSCE'
    b'tMzdd99dzQbS2byyI9xi+BoyERC69PbAHFQcfPDBQiZogLz5BCQvBKbeH8/lTJo0iZGOD21A'
    b'4UnhTzzxBJ8zVqCLFy/2zznnHGfChAnpo446ilPaHP5e8imnnOK89tprGXaz61PbjYIEoJ0q'
    b'9IcX54uEa9KCXnqtcOihh7LiQg+MlkG7Kucg7AtpCKhQW0NQhYdsvt0qiUgYGKxatVKEFkM2'
    b'livPE1XjIIB9b45eCnlYrq3SUW5eHXAc4b333pN7TJs2zR85cmQaRHAfeOABOf+pp55KcX1i'
    b'FF9//TWjJu+VV15RcxFskFggQRoaxPnyyy991nN9fX1ToT80xI0wx6G6iyKPAGBlwHlwZ555'
    b'pkMW2n/nnnuuSQd33323v2jRomxMJQQrV64UAfLTbN26dQuV06NHDw+qWd4uMjWLJkFadHV1'
    b'dYAWvFWMb2raFDIJNqjGhw4dKvfTvX7yDmi1ts0PmSsIRNYnEHT0og4ohcJfNjU44IAD5L2O'
    b'P/54litlvfjii9xI/ttvv83yZ3GZxjvnkZdA+Q58CA/neahbl+Tae++9U6NGjeI2PWbMaGxH'
    b'pZmnr8V6njv3/cIkoMqy8fnnnxthbNHfvffem4VW0FcHajr39OnT5R633347l2Qrp8eA559x'
    b'xhlyj/vuuy90HHk5duqppwZw1ELHITQ5zr958+bpIznY15911lktKE/92BDBe/Ge5vjs2bPl'
    b'GIFwzQhJ/aEsu+zszTffTG2ljp122mnqW4Y2cL3xC9TfkiVLWvShAI3Fh3MYqt85c+Yw6mgG'
    b'GVrgcKqyKyrS6thtt92W5Ucu4Gtk0ShZrjwblIPco62/E088UdV5HPI0AFonN7ywVRjtNHPm'
    b'TA+hjXlpRgABNIO0ID0FLKTLUG6oE4WqVScV7CxVbvR4VI231iUL7WN68hR4L/t2kTrgbGI7'
    b'oshCA9j39uB/iHbhoBOcyM0vAvzyyy+S32233Xycr3O5sqFZQ+9y+umnq9YKMqVxrUvHkVPn'
    b'0XACLqIZNmyYC2J4F1xwQYpD57fccouq6xjlUBDQEjSjsVfkqcqxY8d68+fP9znrheqGlWWX'
    b'RoHgQfz//e9/UnFXXnllesqUKfxN/xRsTwDbJsegwnVqMyhAVCyFqOJo2F2+FK/hn2KrThN5'
    b'BNJqmKpZnfP7779TjfNd1Hm2nUblVuLl7evZL8Ct+qdNmDnOXyKT2P6EE07wevbsGbpWE0Kd'
    b'88YbbwR4dg4WybPiWcRkwP9xcb3tzzj77LOP+/jjj2cvvvhie7+UQcfxjjvuYMNyrd5TgnMZ'
    b'0pyVfNFFF/kgi4fwOcPOKBILx20By7v179+/ArJBleXmVOYBwt1qkPVQWWR6gMpmwQH8giy9'
    b'b3qpzOs/H/Y9oy+zQSaLKp0xYwYsxyZ1XgsAtpuu3ADmRI4ZrFu3biMqQ65/6KGHqN+Mqs7e'
    b'euutcuz+++/Xu3PAM7acf/75ZqwhuPTSS5tYpj6szjfH0DqDqIp/++23Qyqc8x4NQFwfLVyO'
    b'Q4jKR9CHBXif7AsvvJBFeKzqEH9qC28/C+cvg+Mhk9cGeG5rf61ic1PZCkDo7sknnxxccskl'
    b'NGvqK5zPPfech8rLvPrqq/osxzn77LMDhGFxzAtNzMALyzd/2QuIGFicQDqRvL8NtLgu0Day'
    b'E/Lj+aocpH3YTQohFnTqRo8eLfffsGGD/QukSog6TVA4IcBE2sf5rSESXgHPnYXN1zll/jgb'
    b'Oa+O4eB5IAo/Wcu5hy0fffRRCxfPQvgBvPwUjse31njw3Nb+WsU2EYBARXqXX365YjrVFs3F'
    b'tddeW/n000+njOpiVyhfVmXyYVeuPChIybhe1OPgwYNDM4IJqjxbzdtEBpFCi0qAqBCpWuV8'
    b'XCuTSnGdDwGKQKnuUU6ITAgLQ5XKeYU6ybQLT16OgwAhskTBPorx48dXwFRUjhgxIoVwOfSe'
    b'OwKFhLNFoL8A1qo0WpHyF9ingxat+v9he/JakEbQtWtXidWpZm1nKmfScqCGiQOEplPh8ylM'
    b'm0AQYijMI3C+CDlSVgpRgvgAEAo7kUIC79Wrlwu/Qu63fPlyeUCEgNzYBGhX/e4ItPcBXags'
    b'F3bRB4tR9zA6sDr8VQ/6CGgthRhNz1bUMJwp33RYgAzNtgqPtsA42EIk7Dzjfp004HwE8eyp'
    b'eiF0kkTB1iz2egIDEuCQQw4RAixevJg/bKnynJ2kdubAetDJ4sV2Yehxxx3nQYj8DkDm888/'
    b'b6qpqQkiK3DyAMHYx1Ow3arlgQCuPZ8PXnRcC+YCUSFGQ0MDhRyrQfQEEFsw7pAhQ2RSiF6e'
    b'pp4F29BIIAmtkwJoFHbR6pzDbxG7UP00g/6bb74p59P/sUPAYsV2U1EMl2ASKg466KBu/fr1'
    b'a/O+aGnSCgkjNFQkNYOQA2o0KkBey95BERRCogydP6axDX0dLEI0BVxv388zDiicOO/rr7+W'
    b'Z4eZyiMf4NoE4NT3BQsW+BwAmjNnjpR17LHHcg1C6LmLEduNAFsLqFcKyVRugFakfIKoOo8I'
    b'S4EEAOFEMBC6zO9HK+YImhAgphHn+QUgnSITzqUApbxhw4bRBOSVzx+vPOyww+T6yy67LH3W'
    b'WWfZRKP/w+dJCFAIiIHtkTQuElXPAnVuj8blaQoCEUd6+PDh4qzR6aP3b9LYtPpeAwYMsAUd'
    b'rF27VvkJIFLI34jTHgTI511xxRWKZIx+oIHUSiE8qzr+yCOPBPBxil74RKcRALA1AD1w5RSC'
    b'CKFWGJmGJYCmkHNwrZ0OOW7wFfIIhH22YOVbAnV1dSRCq+QzYC8he+wY/RigbOeGG27Izpgx'
    b'g9mEAK2hqqoqyzn3OkvBq8qGGrZj+Og0rDaB6+2Kl49M20DLbunfv79Ijj1z3GoitEk+gvZ9'
    b'5syZwbvvvpu95557nPvvv9+fP39+5tZbb/U42qlPK3p02oNSsBzG1FkzjTxAOGgLjK1RSGLD'
    b'9hWifoMFF554HoGgwtOTJ0+SsnUsH0TnJbRFPpLgmGOOSYEIHA/xJk+enIZ/URIt36DTCAD1'
    b'6qOyJEaH+lQC4YiY2gGMGzeOAy0hu6wR+vUw9huw/4BpaABR4UR0ChiRI8zmmcU68nDtsgEf'
    b'zxjtQ9jp0GkEYA/bPvvsI+VzTByy8yEcMQHsHo0TIIHWJ8JZuHChGUHM+6WRCB8UQDx/6NCh'
    b'cj3DSJat/QcF2HgXjmqn1c+OQme+oGuvEoYPUIkQjt60CIYagppCZ22wM8ceK5VY3nTqtAZ4'
    b'7ilcL8JGFJBubGwMli1bJiaAz4bTSkqdbws6leH2YAln3nBsvb6+TgRDDVFoZCwSoskSL2wZ'
    b'HpprOFwdRyCu87M1AL8p5MMHEG2DZ+OPVcf6HzsTOpUAcNCkfLQ+j4Mpa9aslUrXk0ljCRCn'
    b'2onI/tAcPgtcIygEWrFiBZeDqYkuehcJkAJ52tQmpY5OJQBaoVT4unXr1IeZVq1aJc/ElTQ6'
    b'mQf4CiFJm0jAjggmTBjP7lydC8MeqOEqpjfffJNfNJGy7YmjOzM6lQD8BjC/v6OzDuJpb/Xq'
    b'1TqnPiqhU/nQ8b1cy4Ecbu2lXsOGDU/BlkuPoQ04eAHKVkImae68885KkE8dI6ABCpJvZ0Kn'
    b'EgBCcCdNmqSECHXrLFmyhCuF1TGAdrqgEGCflcB1i+fyMKXqEQUIKQqZCYIePmL43MW583Cr'
    b'XHEQfgAT0al1s6PQqS8JL58/5qRqn92ohBHC1KlTgz59+qh0HMyHn43wWvRwsunWJcy94gAN'
    b'4k6cOFE0AP/M7C2EgCUxlLs90NksDw2t5oSQ87uOOOII9sQVlCDIE3LQTBiIrbwTzuGUroK2'
    b'HAQQDUDhG4Vx/PHHs6OpMHt2InS6mmOod9JJJ6mq5xiNGVzhkjKgoBCi6t20drvVc8gZhCpI'
    b'gL333tu7/vrr1Y04IsyyJ0+e7E+ZMqUshE90OgGqqqrc6667jlIPuCCCgr3wwguD/fffvy0h'
    b'hBgA1U9BZ+HJSxdxdXV1JQgg/QpR0O+48sornVmzbgig9p2LL77Yf+KJJzhdu9PrZYcBFV4M'
    b'8BECZrlM66mnnsrU19e3OZ8dgua8ATp+JEKA6xozmUzL9OnTzWQPtURsS4CWzyVjXJPQZrk7'
    b'G4qF6Wpc4IorrvDOP//8VIG1BCGwqxYOpM6p1cxp+gF6YGerQE3A+5WL3bdRsqqO8f2wYcPE'
    b'EYTg7S5gBd1XkKAVlLStM6EjwVYMVa5W6+pdIEnXUGdRgnyULAHg7dPDl7kCsN+cTNL84Ycf'
    b'yr4hQ9Tn6MpOrW8NSpYADO/69u0rAz3Lli1r/ueff1IggZiFyvAXRRPEoGQJAPueHjlypPTz'
    b'Q/VXmpk9uT1KS8TNJkpgoaR9AAjYFja7g+1On6B79+7SJ5AgHqVOAHHwstmM+bqH2ecinIwf'
    b'C04gKGUChD7htmzZ8qyeWRzSCjqZoABKmQD8fo50+jQ2NvLr3fbYP2f1Jj5AGyhpE2DPC+R0'
    b'Mi7M0Fn1ebaqqqqCA0EJcihpAqCFS09fXV2d+9JLL1WwQ4hAhFBwSnmCzShpAvTp00eNIjKt'
    b'f9qVPx7BLMFE0gvYBkqaAL169ZJvB/ALM4E1R2Do0KHZcpjW3V6UNAHSuW8IKyEb4RvHf9Cg'
    b'QTQHSU9gGyh1DeBxCZfOKuGbeX09e/YMfWcgQTxKXQPwS5xKAxjhm4+NwQTkDQ8nyEdJEwBh'
    b'ID+troRshG9MgT1QlKAwSpoAgGtWF0WcQK4pSOz/FqDUCcCJn0oD2BHAtGnTWl1TkGAzSp4A'
    b'e+21FzdK+uaDYocddpiabawyCVpFyRMA4R6/pa/S5sdL2lpTkGAzSp4AFRUV7oUXXkg/QEn/'
    b'rrvuCsaNG5cIfwvBtXWbjWfpIuAS76amJvU7xYU+KpEgHzsLARJsI0reBCRoHxIClDkSApQ5'
    b'EgKUORIClDkSApQ1HOf/AV135oydlYAtAAAAAElFTkSuQmCC')

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
    
