# Python modules

import os
import os.path
import sys

# 3rd party modules
import wx
import xdrlib
#import common_dialogs
from numpy import ndarray, fromfile, zeros, arange, array_equal, \
                  int32, float32, float64, complex64, complex128


# Some shortcut styles for message boxes
Q_OK_CANCEL = wx.ICON_QUESTION | wx.OK | wx.CANCEL
Q_YES_NO = wx.ICON_QUESTION | wx.YES_NO
I_OK = wx.ICON_INFORMATION | wx.OK
X_OK = wx.ICON_EXCLAMATION | wx.OK
E_OK = wx.ICON_ERROR | wx.OK



def message(message_text, title=None, style=wx.ICON_INFORMATION | wx.OK):
    """
    Launch a modal message dialog widget.

    Parameter arguments:
    message -- string, Text inserted into the dialog panel indicating the
               message, question or error.

    Message styles are: wx.ICON_EXCLAMATION, wx.ICON_ERROR, wx.ICON_QUESTION
    and wx.ICON_INFORMATION.

    The button styles are: wx.OK, wx.CANCEL and wx.YES_NO. 
    You can add wx.YES_DEFAULT or wx.NO_DEFAULT to make Yes or No the
    default choice.

    NOTE: the return code is one of wx.OK, wx.CANCEL, wx.YES or wx.NO.
    
    This differs from wx.MessageDialog.ShowModal() which returns wx.ID_OK,
    wx.ID_CANCEL, etc.


    """
    app = wx.App()      # need this or get error running dialog
    
    if not title:
        # An app may call this to display a message box before it has 
        # created any windows, so we can't assume a top window always exists.
        top_window = wx.GetApp().GetTopWindow()
        title = top_window.GetTitle() if top_window else "Message Dialog"
    
    val = wx.MessageBox(message_text, title, style)
    
    return val


def parse_selection(value=None):
    if value is None:
        return 'None'
    elif value == wx.OK:
        return 'OK'
    elif value == wx.CANCEL:
        return 'CANCEL'
    elif value == wx.YES:
        return 'YES'
    elif value == wx.NO:
        return 'NO'


def pickdir(message="", default_path=""):
    """
    Prompts the user to select a directory and returns the selected
    directory as a string. If the user hits cancel, the function returns an
    empty string.
    
    If the message param is empty (the default), the message is a standard
    one chosen by wx.

    Under OS X and Windows, this dialog remembers the directory where it was 
    last invoked, and if the default_path param is empty, it will start in 
    that same directory. Under GTK a reasonable default is used.
    """    
    app = wx.App()      # need this or get error running dialog

    if not message:
        message = wx.DirSelectorPromptStr

    val =  wx.DirSelector(message, default_path)
    
    return val
        


def pickfile(message="", 
             filetype_filter="All files (*.*)|*.*", 
             enforce_filter=False, 
             default_path="", 
             default_file="",
             multiple=False, 
             new_file=False):
    """
    Launch a modal file or directory selection widget.

    Prompts the user to select a single file to be opened and returns the 
    selected file as a string. If the user hits cancel, the function returns 
    an empty string.
    
    If the message param is empty, the message is a standard one chosen by wx
    (which is "Select a file" under OS X, Windows & Linux).

    If you supply a filetype_filter, it should look something like this:
       "JPEG files (*.jpg)|*.jpg"
    One can supply multiple file types like so:
       "JPEG files (*.jpg)|*.jpg|Bitmap files (*.bmp)|*.bmp"
       
    If you supply a filetype_filter and enforce_filter is False (the default), 
    this function will append "|All files (*.*)|*.*" to the filter to allow 
    users to select a file with any extension. Otherwise, the user is limited
    to selecting a file that has one of the extensions in the filter.
    
    Under OS X and Windows, this dialog remembers the directory where it was 
    last invoked, and if the default_path param is empty, it will start in 
    that same directory. Under GTK a reasonable default is used.

    When multiple=False (the default), the function returns a string ("" if 
    the user chose cancel). When multiple=True, a sorted list (possibly empty)
    is returned. 
    
    When new_file=False (the default), the user must select a file that 
    already exists. When new_file=True, the user may type in the name of a
    file that does not yet exist.

    """
    app = wx.App()      # need this or get error running dialog
    
    flags = wx.OPEN | wx.FILE_MUST_EXIST
    if new_file:
        flags = wx.OPEN
    
    if multiple:
        return_value = [ ]
        flags |= wx.FD_MULTIPLE
    else:
        return_value = ""
    
    if not message:
        message = wx.FileSelectorPromptStr

    if not enforce_filter and not filetype_filter.endswith("*.*"):
        # Ensure the user can select all file types.
        if not filetype_filter.endswith("|"):
            filetype_filter += "|"
        filetype_filter += "All files (*.*)|*.*"

    dialog = wx.FileDialog(wx.GetApp().GetTopWindow(), message, default_path, 
                           default_file, filetype_filter, flags)

    if dialog.ShowModal() == wx.ID_OK:
        if multiple:
            return_value = sorted(dialog.GetPaths())
        else:
            return_value = dialog.GetPath()

    return return_value
   
 
 
def readfile(nparr, fname=None, xdr=None):
    """
    Read filename into given NumPy array based on its size and dtype.

    Parameter arguments:
    nparr  -- NumPy array
    fname  -- string, name of a file

    Keyword arguments:
    xdr   -- set to non-None to load file as if it were saved using XDR methods
    
    Return arguments:
    Copy of NPARR is made and returned filled with contents of file.

    """ 
    if not isinstance(nparr, ndarray) or not isinstance(fname, str):
        errmsg = 'Error(readfile()): Incorrect parameters, returning. '+\
                 'param nparr :  a numpy array  '+\
                 'param fname :  a string or unicode string'
        raise UtilFileError(errmsg) 
  
    if not fname:            
        fname = pickfile()
        if fname is '': 
            return nparr
  
    ndim   = nparr.ndim
    shape  = nparr.shape
    dtype  = nparr.dtype.name
    nbyt   = nparr.itemsize
    npts   = nparr.size
    nbytes = npts*nbyt
    
    nparr.resize(nparr.size)

    if not os.path.isfile(fname):
        errmsg = 'Error(readfile()): File does not exist, returning!'
        raise UtilFileError(errmsg)

    try:
        fp = open(fname,'rb')
    except:
        errmsg = 'Error(readfile()): Unable to open file - '+fname+\
                 'exc_type : '+str(sys.exc_info()[0]), 'exc_info : '+str(sys.exc_info())
        raise UtilFileError(errmsg)

    if xdr is None:      
        nparr = fromfile(file=fp, dtype=dtype, count=npts)
    else:
        buf = fp.read(nbytes)
        p = xdrlib.Unpacker(buf)
        try:
            if   dtype == 'complex64'  : raw = p.unpack_farray(npts*2, p.unpack_float)
            elif dtype == 'complex128' : raw = p.unpack_farray(npts*2, p.unpack_double)
            elif dtype == 'float64'    : raw = p.unpack_farray(npts,   p.unpack_double)
            elif dtype == 'float32'    : raw = p.unpack_farray(npts,   p.unpack_float)
            elif dtype == 'int32'      : raw = p.unpack_farray(npts,   p.unpack_int)
            elif dtype == 'character'  : raw = p.unpack_farray(npts,   p.unpack_byte)
            else:
                errmsg = 'Error(readfile()): Unable to unpack this dtype to XDR, returning.'
                raise UtilFileError(errmsg)
            
            if dtype == 'complex128' or dtype == 'complex64' :
                for i in range(npts):
                    nparr.real[i] = raw[2*i]
                    nparr.imag[i] = raw[2*i+1]
            else:
                for i in range(npts):
                    nparr[i] = raw[i]

        except xdrlib.ConversionError as instance:
            errmsg = 'Error(readfile()): Unexpected error unpacking XDR data, Msg = '+instance.msg
            raise UtilFileError(errmsg)

    nparr.resize(shape)
    return nparr         
        
        
def readtextfile(filename):
    """
    Read ASCII file into string array, one line per array element

    Parameter arguments:
    filename  -- string, name of a file

    Return arguments:
    array = returns string array containing whole file contents
    error =  0 IF successful
    error = -1 IF could not open or read file

    """ 

    if len(filename) is 0 or filename is '':
        errmsg = 'Error (readtextfile): No Filename defined'
        raise UtilFileError(errmsg)
    
    read_line = ''
    try:
        fp = open(filename, 'rb')
    except:
        errmsg = '(readtextfile), On opening file for reading '+filename
        raise UtilFileError(errmsg)
    
    try:
        read_line = fp.readline()
        strarray=[read_line]
        while read_line:
            read_line = fp.readline()
            strarray.append(read_line)
    except:
        errmsg = '(readtextfile), On reading from file'+filename
        raise UtilFileError(errmsg)
    
    if len(strarray) <= 1:
        errmsg = '(readtextfile), Error reading parameters, list must be a string array. In file: '+filename
        raise UtilFileError(errmsg)
    
    return strarray


def writefile(nparr, fname=None, xdr=None):
    """
    Write NumPy array into filename based on its size and dtype.

    Parameter arguments:
    nparr  -- NumPy array
    fname  -- string, name of a file

    Keyword arguments:
    xdr   -- set to non-None to save file using XDR methods
    
    Return arguments:
    none

    """ 
    if not isinstance(nparr, ndarray) or not isinstance(fname, str):
        errmsg = 'Error(readfile()): Incorrect parameters, returning. '+\
                 'param nparr :  a numpy array  '+\
                 'param fname :  a string or unicode string'
        raise UtilFileError(errmsg) 
  
    if not fname:            
        fname = pickfile()
        if fname is '': 
            errmsg = 'cancel'
            raise UtilFileError(errmsg)
  
    shape  = nparr.shape
    dtype  = nparr.dtype.name
    nbyt   = nparr.itemsize
    npts   = nparr.size
    nbytes = npts*nbyt
    
    nparr.resize([npts])
    
    if xdr is None: 
        try:     
            nparr.tofile(fname)
        except:
            errmsg = 'Error(writefile()): Unable to write data to - '+fname+'  '+\
                     'exc_info : '+str(sys.exc_info())
            raise UtilFileError(errmsg)
    else:
        try:
            p = xdrlib.Packer()
            if   dtype == 'complex64': 
                tmp = zeros(npts*2,dtype=float32)
                for i in range(npts): 
                    tmp[i*2]   = nparr.real[i]
                    tmp[i*2+1] = nparr.imag[i]
                p.pack_farray(npts*2, tmp, p.pack_float)
            elif dtype == 'complex128' : 
                tmp = zeros(npts*2,dtype=float64)
                for i in range(npts): 
                    tmp[i*2]   = nparr.real[i]
                    tmp[i*2+1] = nparr.imag[i]
                p.pack_farray(npts*2, tmp, p.pack_double)
            elif dtype == 'float64'  : p.pack_farray(npts, nparr, p.pack_double)
            elif dtype == 'float32'  : p.pack_farray(npts, nparr, p.pack_float)
            elif dtype == 'int32'    : p.pack_farray(npts, nparr, p.pack_int)
            elif dtype == 'character': p.pack_farray(npts, nparr, p.pack_byte)
            else:
                errmsg = 'Error(writefile()): Unable to pack this dtype to XDR, returning.'
                raise UtilFileError(errmsg)
            buf = p.get_buffer()
 
        except xdrlib.ConversionError as instance:
            errmsg = 'Error(writefile()): Unexpected error packing XDR data, Msg = '+instance.msg
            raise UtilFileError(errmsg)

        try:
            fp = open(fname, 'wb')
            fp.write(buf)
        except:
            errmsg = 'Error(writefile()): Unable to write XDR data to - '+fname+'  '+\
                     'exc_info : '+str(sys.exc_info())
            raise UtilFileError(errmsg)
    
    nparr.resize(shape)
    return    


def strip_extn(fname, extn=None):
    """ Takes filename or filelist and strips off any extension after '.' """
    if   isinstance(fname, str) or isinstance(fname, str):
        res = os.path.splitext(fname)
        if not extn:
            return res[0]
        else:
            return res[0], res[1]
    elif isinstance(fname, list):
        fextn = []
        for i,item in enumerate(fname):
            if isinstance(item, str) or isinstance(item, str):
                res = os.path.splitext(item)
                fextn.append(res[1])
                fname[i] = res[0]
        if not extn:
            return fname
        else:
            return fname, extn
    else:
        if not extn:
            return fname
        else:
            return fname, ''
    

def strip_file(fname):
    """ Takes a filename or filelist and returns path """
    if   isinstance(fname, str) or isinstance(fname, str):
        return os.path.dirname(fname)
    elif isinstance(fname, list):
        for i,item in enumerate(fname):
            if isinstance(item, str) or isinstance(item, str):
                fname[i] = os.path.dirname(item)
                
        return fname
    else:
        return fname
    
        
def strip_path(fname):
    """ Takes a filename or filelist and returns filename """
    if   isinstance(fname, str) or isinstance(fname, str):
        return os.path.basename(fname)
    elif isinstance(fname, list):
        for i,item in enumerate(fname):
            if isinstance(item, str) or isinstance(item, str):
                fname[i] = os.path.basename(item)
        return fname
    else:
        return fname    
            
  
 
#----------------------------------------------------------
# Exception classes
#----------------------------------------------------------

class UtilFileError(Exception):
    """Exception raised for errors in the generic utility function

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, errmsg):
        self.errmsg = errmsg




def main():

#    app = wx.App()      # need this or get error running dialog
    try:
        msg = "Test an Info box"
        print(("Dialog returned - " + parse_selection(message(msg, title="INFO!"))))
        msg = "Test an Error box"
        print(("Dialog returned - " + parse_selection(message(msg, title="ERROR!", style=E_OK))))
        msg = "Test an Question box"
        print(("Dialog returned - " + parse_selection(message(msg, title="QUESTION!", style=Q_YES_NO))))
    except UtilFileError as e:
        print((e.errmsg))
        
    try:
        print((pickfile(message='Select a Python File')))
        print((pickdir(default_path='C:\\bsoher\\code')))
    except UtilFileError as e:
        print((e.errmsg))
        
    try:
        print(('strip_extn = '+strip_extn('C:\\bsoher\\code\\code_python\\myfile.py')))
        print(('strip_file = '+strip_file('C:\\bsoher\\code\\code_python\\myfile.py')))
        print(('strip_path = '+strip_path('C:\\bsoher\\code\\code_python\\myfile.py')))
        print(' ' )
        print(('strip_extn = '+strip_extn('C:\\bsoher\\code\\code_python\\')))
        print(('strip_file = '+strip_file('C:\\bsoher\\code\\code_python\\')))
        print(('strip_path = '+strip_path('C:\\bsoher\\code\\code_python\\')))
        fname = ['C:\\bsoher\\myfile1.py',3,'C:\\bsoher\\myfile2.py','C:\\bsoher\\myfile3.py']
        print('strip_extn multi = ...')
        print((strip_extn(fname)))
        print(' ')         
        fname = ['C:\\bsoher\\myfile1.py',3,'C:\\bsoher\\myfile2.py','C:\\bsoher\\myfile3.py']
        print('strip_file multi = ...')
        print((strip_file(fname)))
        print(' ') 
        fname = ['C:\\bsoher\\myfile1.py',3,'C:\\bsoher\\myfile2.py','C:\\bsoher\\myfile3.py']
        print('strip_path multi = ...')
        print((strip_path(fname)))
        print(' ') 
    except:
        print((sys.exc_info())) 
        
    bob   = 0
    dtype = [int32,float32,float64,complex64,complex128]
    typ   = ['int32','float32','float64','complex64','complex128']
    for i in arange(len(typ)):
        try:
            fname = 'C:\\Users\\bsoher\\test_gen_'+typ[i]+'.dat'
            data0 = arange(10,dtype=dtype[i]).reshape(2,5)
            writefile(data0,fname,xdr=0)
            data1 = zeros((2,5),dtype=dtype[i])
            data1 = readfile(data1,fname,xdr=0)
            fname = 'C:\\Users\\bsoher\\test_gen_'+typ[i]+'_xdr.dat'
            data2 = arange(10,dtype=dtype[i]).reshape(2,5)
            writefile(data2,fname,xdr=1)
            data3 = zeros((2,5),dtype=dtype[i])
            data3 = readfile(data3,fname,xdr=1)
    
            if array_equal(data0,data1) and array_equal(data1,data2) and array_equal(data2,data3):
                bob = bob+10**i
        
        except UtilFileError as e:
            print((e.errmsg))
 
        temp = 11

        print( "if bob = 11111 then all conditions ran successfully")
        print(( " bob = "+str(bob)))
        

    print( "Finished all tests successfully ... quitting." )
    

if __name__ == '__main__':
    main()
