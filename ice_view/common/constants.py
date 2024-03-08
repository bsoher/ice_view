# Python modules

import math

# Our modules



DEGREES_TO_RADIANS = math.pi / 180
RADIANS_TO_DEGREES = 180 / math.pi
MINUTES_TO_SECONDS = 60

# We encode numeric lists (also numpy arrays) in a three step process.
# First is XDR (http://en.wikipedia.org/wiki/External_Data_Representation),
# second is zlib to save space, third is base64 to make the output of
# zlib palatable to XML.
#
# NUMERIC_LIST_ENCODING = "xdr zlib base64"
#
# As of 2019-12-2 we are using Numpy 'save()' format to encode numpy arrays
# for saving to xml because it reads/writes much faster than the decode_xdr
# methods in xdrlib. Vespa can still read in the 'xdr' encoded data, but it
# will subsequently save it using 'npy' formatting.
#
# This constant used to be in ice_view.common.xml_ module
NUMERIC_LIST_ENCODING = "npy zlib base64"


class Deflate(object):
    """Constants for the internally-used methods inflate() & deflate()
    that appear on many of our objects.
    
    These constants are arbitrary and may change.
    However, bool(NONE) is always guaranteed to be False while 
    bool(X) == True is guaranteed for all other values.
    """
    NONE = 0
    # ETREE stands for ElementTree which implies serialization to an 
    # ElementTree.Element object which is trivial to turn into XML. 
    ETREE = 1
    # DICTIONARY is to represent objects as dicts. We don't often 
    # deflate to dicts, but we inflate from dicts in the database code and
    # in some GUI code.
    DICTIONARY = 2


class Export(object):
    """Constants for our export/import format."""
    # VERSION is the version of our XML format. 
    # When we change our format at some point, it will be helpful to
    # have a version number embedded in our exported files.
    VERSION = "1.0.0"
    
    ROOT_ELEMENT_NAME = "vespa_export"
    

# These are used as default attribute values in a number of data objects
# as well as widget start values in Simulation (and maybe Analysis)
DEFAULT_ISOTOPE = "1H"
DEFAULT_B0 = 123.9
DEFAULT_PROTON_CENTER_FREQUENCY = 123.8 # [MHz]
DEFAULT_PROTON_CENTER_PPM = 4.7         # [ppm]
DEFAULT_XNUCLEI_CENTER_PPM = 0.0        # [ppm]
DEFAULT_SWEEP_WIDTH = 2000.0            # [Hz]
DEFAULT_LINEWIDTH = 3.0                 # [Hz]
DEFAULT_SPECTRAL_POINTS = 512           # integer

RESULTS_SPACE_DIMENSIONS = 4



class DataTypes(object):
    """Internal representation of data type and routines to convert between
    the three type systems we deal with: Python, XDR and numpy.
    """

    # We have to deal with types in three contexts -- Python, XDR, and numpy.
    # They mostly overlap, but not entirely seamlessly. Here's some bumps to
    # be aware of --
    # - Python ints are only guaranteed to be at least 32 bits. On (some? all?)
    #   64-bit systems, numpy ints default to the numpy.int64 type. That means 
    #   that a numpy int can't safely be represented as a Python int. One has
    #   to resort to the rarely-used Python long type to safely represent a
    #   numpy.int64 in Python. The distinction between int and long disappears
    #   in Python 3 (where ints can represent arbitrarily large values, just 
    #   like longs in Python 2).
    #
    # - XDR supports 64-bit ints under the name "hyper".
    #
    # - Going in the other direction (Python long ==> numpy.int64 or hyper) is
    #   also an overflow risk since a Python long can contain an arbitrarily 
    #   large value. Fortunately we never deal with large int values.
    # 
    # - Python floats are "usually implemented using double in C" (per Python 
    #   2.7 doc on standard types) which means 64 bits. XDR and numpy both 
    #   support higher precision (128-bit) floats, calling them "quadruple"
    #   and "float128" respectively. Python's XDR module doesn't support writing
    #   128-bit floats (which makes sense, since Python's float can't represent
    #   them), so if numpy ever hands us a 128-bit float, we're in trouble.
    #
    # - XDR doesn't understand complex numbers. It's trivial to represent them
    #   into (real, imag) float pairs, but it's nevertheless something that 
    #   our code needs to (and does) handle.



    # These constants are arbitrary and may change except that bool(NONE) is
    # always guaranteed to be False and bool() of any other value will always
    # be True.
    NONE        = 0
    BOOL        = 1 
    BYTE        = 2
    INT32       = 3
    INT64       = 4
    FLOAT32     = 5
    FLOAT64     = 6
    COMPLEX64   = 7
    COMPLEX128  = 8

    ALL = (BOOL, BYTE, INT32, INT64, FLOAT32, FLOAT64, COMPLEX64, COMPLEX128)

    # The mapping XDR_TYPE_SIZES maps our standard data types to the
    # XDR sizes in bytes (as guaranteed by the XDR standard).
    # bool(NONE) is always guaranteed to be False and bool() of any other 
    # value will always be True.
    #
    # XDR knows about lots more types than this, but these are the only ones
    # we care about. We use them to infer the # of elements contained in a 
    # glop of XDR data.
    #
    # Note that XDR doesn't define a byte, so it's ambiguous what a "byte" 
    # would mean in XDR terms. I defined it below just for completeness sake
    # but it might not be correct.
    #
    # ref: http://tools.ietf.org/html/rfc1014
    # ref: http://tools.ietf.org/html/rfc1832
    # ref: http://tools.ietf.org/html/rfc4506
    XDR_TYPE_SIZES = {
                        NONE            :     0,
                        BOOL            :     4,
                        BYTE            :     4,
                        INT32           :     4,
                        INT64           :     8,    
                        FLOAT32         :     4,
                        FLOAT64         :     8,
                        COMPLEX64       :     8,
                        COMPLEX128      :    16,
                     }


    _EXTERNAL_TO_INTERNAL = {
        # Maps external type strings and object to internal values. External 
        # strings include the many variations one can find in VASF format.
        # They also include the numpy type strings. Older code (Python & IDL) 
        # for reading & writing VASF tended to strip the spaces out of values 
        # read from the INI file, so all the VASF type names have to appear 
        # in spaceless (e.g. "doublefloat") as well as "spaced" form.

        # These are VASF strings
        'float'                     :    FLOAT32,
        'double'                    :    FLOAT64,
        'doublefloat'               :    FLOAT64,
        'double float'              :    FLOAT64,
        'shortinteger'              :    INT32,
        'short integer'             :    INT32,
        'integer'                   :    INT32,
        'unsignedinteger'           :    INT32,
        'unsigned integer'          :    INT32,
        'integer16bit'              :    INT32,
        'integer 16bit'             :    INT32,
        'integer 16 bit'            :    INT32,
        'integer'                   :    INT32,
        'long'                      :    INT64,
        'unsignedlong'              :    INT64,
        'unsigned long'             :    INT64,
        'complexinteger8bit'        :    COMPLEX64,
        'complex integer8bit'       :    COMPLEX64,
        'complex integer 8bit'      :    COMPLEX64,
        'complex integer 8 bit'     :    COMPLEX64,
        'complexinteger16bit'       :    COMPLEX64,
        'complex integer16bit'      :    COMPLEX64,
        'complex integer 16bit'     :    COMPLEX64,
        'complex integer 16 bit'    :    COMPLEX64,
        'complexfloat'              :    COMPLEX64,
        'complex float'             :    COMPLEX64,
        'complex'                   :    COMPLEX64,
        'complexdouble'             :    COMPLEX128,
        'complex double'            :    COMPLEX128,
        'byte'                      :    BYTE,
        # These are numpy types
        # We need to handle all of the numeric types in numpy.sctypeDict.values(). 
        # Here's a useful piece of code that prints them:
        # print( '\n'.join([str(type_) for type_ in sorted(set(numpy.sctypeDict.values()))]))

        # We ignore the numpy types float128 and complex256. Python can't 
        # guarantee support for them, since Python floats map to C doubles 
        # which are only guaranteed a 64 bit minimum. 
        "bool"                      :    BOOL,
        "character"                 :    BYTE,
        "int8"                      :    INT32,
        "uint8"                     :    INT32,
        "int16"                     :    INT32,
        "uint16"                    :    INT32,
        "int32"                     :    INT32,
        "uint32"                    :    INT32,
        "int32"                     :    INT32,
        "uint32"                    :    INT32,
        "int64"                     :    INT64,
        "uint64"                    :    INT64,
        "float32"                   :    FLOAT32,
        "float64"                   :    FLOAT64,
        "complex64"                 :    COMPLEX64,
        "complex128"                :    COMPLEX128,

        # These are Python types
        bool                        :    BOOL,
        int                         :    INT64,
        float                       :    FLOAT64,
        complex                     :    COMPLEX128,
    }

    _INTERNAL_TO_NUMPY = {
        # Maps internal types to numpy type strings
        # Valid numpy type names are in numpy.sctypeDict.keys()
        BOOL              :   "bool",
        BYTE              :   "byte",
        INT32             :   "int32",
        INT64             :   "int64",
        FLOAT32           :   "float32",
        FLOAT64           :   "float64",
        COMPLEX64         :   "complex64",
        COMPLEX128        :   "complex128",
    }


    @staticmethod
    def is_complex(the_type):
        return the_type in (DataTypes.COMPLEX64, DataTypes.COMPLEX128)


    @staticmethod
    def any_type_to_internal(the_type):
        if the_type in DataTypes.ALL:
            pass
            # This is already an internal type
        else:
            # If it's a string, lower case it.
            if hasattr(the_type, "lower"): 
                the_type = the_type.lower()

            if the_type in DataTypes._EXTERNAL_TO_INTERNAL:
                the_type = DataTypes._EXTERNAL_TO_INTERNAL[the_type]
            else:
                raise ValueError('Unknown type "%s"' % the_type)

        return the_type


    @staticmethod
    def any_type_to_numpy(the_type):
        the_type = DataTypes.any_type_to_internal(the_type)
        return DataTypes._INTERNAL_TO_NUMPY[the_type]


class MrsFileTypes(object):
    # These constants are arbitrary and may change.
    # However bool(NONE) is guaranteed to be False and bool() of anything
    # else will always be True.
    NONE                    =  0
    VASF                    =  1
    VASF_DATA               =  2
    VASF_PARAMETERS         =  3
    VIFF                    =  4
    DICOM_SIEMENS           =  5
    SIEMENS_RDA             =  6
    VARIAN                  =  7
    VIFF_MRS_DATA_RAW       =  8
    DICOM_SIEMENS_FIDSUM    =  9
    PHILIPS_SPAR            = 10


