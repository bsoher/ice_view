# Python modules
import os
import copy
import collections

# 3rd party modules
import numpy as np
import xml.etree.cElementTree as ElementTree

# Our modules
import ice_view.block_raw as block_raw
import ice_view.block_spectral_identity as block_spectral_identity

import ice_view.block_spectral as block_spectral

import ice_view.mrs_user_prior as mrs_user_prior

import ice_view.common.misc as util_misc
import ice_view.common.xml_ as util_xml
import ice_view.common.constants as common_constants

from ice_view.common.constants import Deflate



###########    Start of "private" constants, functions and classes    #########

# _XML_TAG_TO_SLOT_CLASS_MAP maps XML element tags to 2-tuples of
# (slot name, block class) where slot name is one of "raw", "prep", "spectral",
# or "fit" and the class can be any class appropriate for that slot.
_XML_TAG_TO_SLOT_CLASS_MAP = {
    "block_raw"                 : ("raw", block_raw.BlockRaw),
    "block_spectral_identity"   : ("spectral", block_spectral_identity.BlockSpectralIdentity),
    "block_spectral"            : ("spectral", block_spectral.BlockSpectral),
}


# DEFAULT_BLOCK_CLASSES defines which block slots are filled and with which
# classes when a Dataset object is instantiated. We use mostly identity
# classes which means they're not very useful as-is but they serve as
# lightweight placeholders.
# This dict is also a model for custom dicts that might get passed to
# dataset_from_raw().
# This dict should be read-only, and if Python had a read-only dict I would
# use it here. Don't modify it at runtime.
DEFAULT_BLOCK_CLASSES = {
    "raw"       : block_raw.BlockRaw,
    "spectral"  : block_spectral_identity.BlockSpectralIdentity,
}


# End of "private" constants, functions and classes    #########



# Start of public constants, functions and classes    ##########

def dataset_from_raw(raw, block_classes={ }, zero_fill_multiplier=0):
    """
    Given an MrsiDataRaw object and some optional params, returns a dataset
    containing the minimal set of operational blocks for use in Analysis: raw
    and spectral. Other block slots (prep, spatial and fit) contain identity
    blocks.

    If block_classes is populated, it must be a dict that maps slot names
    to block classes like the dict DEFAULT_BLOCK_CLASSES in this module. The
    classes specified will be used in the slots specified.

    If the zero_fill_multiplier is non-zero, it is applied to the newly-created
    dataset.
    """
    dataset = Dataset()

    # Replace the default raw block. Note that even if the default raw block is of the
    # correct type (which is probably the case), I can't just call its inflate() method
    # because _create_block() does other stuff besides just inflating the block.
    klass = block_classes.get("raw", block_raw.BlockRaw)
    dataset._create_block(("raw", klass), raw.deflate(Deflate.DICTIONARY))

    # At present, we never create/replace a prep block via this method.

    klass = block_classes.get("spectral", block_spectral.BlockSpectral)
    dataset._create_block(("spectral", klass))

    # Update prior spectra now that the spectral block exists.
    dataset.user_prior.basis.update(dataset)

    # Adjust the zerofill if necessary.
    if zero_fill_multiplier:
        dataset.update_for_zerofill_change(zero_fill_multiplier)

    return dataset


class Dataset(object):
    """
    This is the primary data object for the IceView program.

    On the GUI side, the IceView application is just a notebook filled with
    dataset Tabs. These can be opened, closed, and organized on screen in many
    ways, but each dataset Tab contains only one Dataset object.

    A Dataset object has a 'blocks' attribute which is an ordered dictionary of
    Block objects. Taken together, the 'blocks' comprise the entire processing
    workflow for the MRS data. The 'blocks' dict is keyed with the names "raw",
    "prep", "spatial", "spectral", "fit", and "quant" in that order. These represent
    "slots", each of which can be filled with one block of the appropriate type.

    The first slot, 'raw', is a Block containg the raw Data. It does no
    processing, but just holds the incoming data and information about the data
    and its header. All the other blocks have the option of transforming the
    data somehow. When a slot's transformation doesn't need to do anything, it
    is filled with a lightweight version of the block that just performs the
    identity transform on the data.

    Each Block has a 'Settings' object that contain the processing parameter
    settings that describe how to process the data in a Block. These are kept
    in a separate object within each block to delineate the inputs from the
    outputs variables and makes it easier to create 'Preset' files for batch
    processing from an existing Dataset.

    Each Block also has a 'data' attribute that contains the state of the data
    after processing. There may also be additional results attributes that hold
    intermediate processing steps results. Each Block references the previous
    step to get the input data for the current processing step.

    Each Block has a 'Chain' object that performs the actual scientific
    algorithms on the data. Chain objects are created at run-time and are not
    saved. The Block, Tab, and Chain objects are how Analysis implements the
    Model-View-Controller paradigm. Only the Block objects are saved (when the
    user chooses File->Save). All other objects are recreated at run-time.

    """
    # The XML_VERSION enables us to change the XML output format in the future
    XML_VERSION = "1.0.0"

    def __init__(self, attributes=None):
        #------------------------------------------------------------
        # Set up elements of the processing chain for the data set
        #
        # Each dataset tab is located in the "outer" notebook which
        # is used to organize the one or more data sets that are open
        # in the application.
        #
        # - The blocks list contain objects that correspond to the
        #   processing tabs in the dataset (or "inner") notebook. A
        #   "block" contains a "chain" object that contains
        #   the code to run the functor chain of processing steps for
        #   a given block. The functor chain is dynamically allocated
        #   for each call depending on the widget settings in the tab.
        #
        #------------------------------------------------------------

        self.id = util_misc.uuid()

        # dataset_filename is only set on-the-fly (as opposed to being set
        # via inflate()). It's only set when the current dataset is read in,
        # or saved to, a VIFF file.
        self.dataset_filename = ''

        # preset_filename only set if apply_preset() is called, it is just for 
        # provenance, we do NOT keep track if setting changed manually afterwards
        self.behave_as_preset = False
        self.preset_filename  = ''

        self.user_prior = mrs_user_prior.UserPrior()

        # Create default blocks. We replace these as needed. Note that the
        # order in which these are added drives the order of the blocks and
        # tabs in the application as a whole.
        self.blocks = collections.OrderedDict()
        for name in ("raw", "spectral"):
            self._create_block( (name, DEFAULT_BLOCK_CLASSES[name]) )

        if attributes is not None:
            self.inflate(attributes)

        # # Update the user prior spectrum and fid caches
        # self.user_prior.basis.update(self)

    @property
    def data_sources(self):
        """Raw/All data sweep width. It's read only."""
        return self.blocks["raw"].data_sources if self.blocks else []

    @property
    def raw_shape(self):
        """Raw data dimensionality. It's read only."""
        if self.blocks:
            return self.blocks["raw"].data_shape
        return None

    @property
    def raw_dims(self):
        """Raw data dimensionality. It's read only."""
        if self.blocks:
            return self.blocks["raw"].dims
        return None

    @property
    def spectral_dims(self):
        """Spectral data dimensionality. It's read only."""
        if self.blocks:
            spectral_dims = self.raw_dims
            zfmult = self.zero_fill_multiplier
            if zfmult:
                spectral_dims[0] *= zfmult
                return spectral_dims
        return None

    @property
    def spectral_hpp(self):
        """Raw/All data center frequency. It's read only."""
        if self.blocks:
            spectral_dims = self.spectral_dims
            if spectral_dims:
                return self.sw / spectral_dims[0]
        return None

    @property
    def sw(self):
        """Raw/All data sweep width. It's read only."""
        return self.blocks["raw"].sw if self.blocks else None

    @property
    def raw_hpp(self):
        """Raw/All data center frequency. It's read only."""
        return self.sw / self.raw_dims[0] if self.blocks else None

    @property
    def frequency(self):
        """Raw/All data center frequency. It's read only."""
        return self.blocks["raw"].frequency if self.blocks else None

    @property
    def resppm(self):
        """Raw/All data resonance PPM value. It's read only."""
        return self.blocks["raw"].resppm if self.blocks else None

    @property
    def echopeak(self):
        """ Acquisition echo peak (0.0 for FID data, 0.5 for full echo) """
        return self.blocks["raw"].echopeak if self.blocks else None

    @property
    def is_fid(self):
        """Boolean. It's read only."""
        return self.blocks["raw"].is_fid if self.blocks else None

    @property
    def seqte(self):
        """Acquisition echo time in msec. It's read only."""
        return self.blocks["raw"].seqte if self.blocks else None

    @property
    def seqtr(self):
        """Acquisition repetition time in msec. It's read only."""
        return self.blocks["raw"].seqtr if self.blocks else None

    @property
    def voxel_dimensions(self):
        """Acquisition repetition time in msec. It's read only."""
        return self.blocks["raw"].voxel_dimensions if self.blocks else None

    @property
    def fov(self):
        """Acquisition repetition time in msec. It's read only."""
        return self.blocks["raw"].fov if self.blocks else None

    @property
    def nucleus(self):
        """Acquisition nucleus. It's read only."""
        return self.blocks["raw"].nucleus if self.blocks else None

    @property
    def zero_fill_multiplier(self):
        """Spectral dimension zero fill factor. It's read only."""
        return self.blocks["spectral"].set.zero_fill_multiplier if self.blocks else None

    @property
    def phase_1_pivot(self):
        """Spectral phase 1 pivot location in ppm. It's read only."""
        return self.blocks["spectral"].set.phase_1_pivot if self.blocks else None

    @property
    def auto_b0_range_start(self):
        """ PPM start range for automated B0 shift routine searches """
        return self.user_prior.auto_b0_range_start

    @property
    def auto_b0_range_end(self):
        """ PPM end range for automated B0 shift routine searches """
        return self.user_prior.auto_b0_range_end

    @property
    def auto_phase0_range_start(self):
        """ PPM start range for automated Phase0 shift routine searches """
        return self.user_prior.auto_phase0_range_start

    @property
    def auto_phase0_range_end(self):
        """ PPM end range for automated Phase0 shift routine searches """
        return self.user_prior.auto_phase0_range_end

    @property
    def auto_phase1_range_start(self):
        """ PPM start range for automated Phase1 shift routine searches """
        return self.user_prior.auto_phase1_range_start

    @property
    def auto_phase1_range_end(self):
        """ PPM end range for automated Phase1 shift routine searches """
        return self.user_prior.auto_phase1_range_end

    @property
    def auto_phase1_pivot(self):
        """ PPM value at which automated Phase1 routine rotates phase """
        return self.user_prior.auto_phase1_pivot

    @property
    def metinfo(self):
        """
        Returns the Metinfo object stored in Dataset. This provides info about
        literature values of metabolites, such as concentrations and spins that
        are used in the fitting initial values routines.
        """
        return self.user_prior.metinfo

    @property
    def user_prior_summed_spectrum(self):
        """
        Returns Numpy array with frequency spectrum created from the UserPrior
        values in that dialog. This is the model spectrum used in the automated
        B0 and Phase routines. This spectrum matches the spectral resolution of
        the data. Obtained from UserPrior object in Dataset. Read only!
        """
        return self.user_prior.basis.get_spectrum_sum(self)

    @property
    def all_voxels(self):
        """ return list of all voxel indices based on spectral_dims """
        dims = self.spectral_dims
        all = []
        for k in range(dims[3]):
            for j in range(dims[2]):
                for i in range(dims[1]):
                    all.append((i,j,k))
        return all

    @property
    def prior_list_unique(self):
        """ 
        Get list of metabolites in the prior set listed only as unique abbreviations.
        This makes it easier for me to check if a fitting condition can be set. 
        
        """
        metinfo = self.user_prior.metinfo
        prior_list = self.blocks['fit'].set.prior_list
        prior_list_unique = [metinfo.get_abbreviation(item.lower()) for item in prior_list]
        return prior_list_unique

    @property
    def minppm(self):
        return self.pts2ppm(self.spectral_dims[0])

    @property
    def maxppm(self):
        return self.pts2ppm(0)

    @property
    def minmaxppm(self):
        return self.minppm, self.maxppm

    def ppm2pts(self, val, acq=False, rel=False):
        """
        Returns the point index along spectrum for given ppm value.
        - Assumes center point <--> resppm for rel False
        - Assumes center point <--> 0.0 ppm for rel True

        """
        dim0 = self.raw_dims[0] if acq else self.spectral_dims[0]
        hpp = self.raw_hpp if acq else self.spectral_hpp
        pts = self.frequency*val/hpp if rel else (dim0/2) - (self.frequency*(val-self.resppm)/hpp)
        pts = np.where(pts > 0, pts, 0)
        return pts

    def ppm2hz(self, val, acq=False, rel=False):
        """
        Returns the absolute number of hz away from 0.0 ppm based on an assumed ppm
        value for the center data point.

        If rel=True, assumes that center point is 0.0 ppm and calculates the
        relative hertz away represented by the ppm value.

        """
        hpp = self.raw_hpp if acq else self.spectral_hpp
        ppm = self.pts2hz(self.ppm2pts(val)) if rel else self.ppm2pts(val, rel=rel) * hpp
        return ppm

    def pts2ppm(self, val, acq=False, rel=False):
        """
        Returns the ppm value of the given point index along spectrum.
        - Assumes center point <--> resppm for rel False
        - Assumes center point <--> 0.0 ppm for rel True

        """
        dim0 = self.raw_dims[0] if acq else self.spectral_dims[0]
        hpp = self.raw_hpp if acq else self.spectral_hpp
        ppm = val*hpp/self.frequency if rel else (((dim0/2)-val)*(hpp/self.frequency))+self.resppm
        return ppm

    def pts2hz(self, val, acq=False, rel=False):
        """
        Returns the number of hertz away from 0.0 ppm from the points based on an
        assumed ppm value for the center point.

        If rel=True, assumes that center point is 0.0 ppm and calculates the
        relative hz away represented by the points value.

        """
        hpp = self.raw_hpp if acq else self.spectral_hpp
        hz = val * hpp if rel else (self.ppm2pts(0.0) - val) * hpp
        return hz

    def hz2ppm(self, val, acq=False, rel=False):
        """
        Returns the number of ppm from hertz based on an assumed ppm value for the
        center point.

        If rel=True, it is assumed that the hertz value is relative to 0.0 ppm
        equals 0.0 hertz. Thus we convert the hz value to points, take the distance
        in points from the 0.0 ppm point and convert that to ppm

        """
        hpp = self.raw_hpp if acq else self.spectral_hpp
        val = self.pts2ppm(self.hz2pts(val)) if rel else self.pts2ppm(val / hpp)
        return val

    def hz2pts(self, val, acq=False, rel=False):
        """
        Returns the number of points away from 0.0 hertz (0.0 ppm) based on an
        assumed ppm value for the center point.

        If rel=True, it is assumed that the hertz value is relative to 0.0 ppm
        equals 0.0 hertz. Thus we convert the hz value to points, take the distance
        in points from the 0.0 ppm point and convert that to points.

        """
        hpp = self.raw_hpp if acq else self.spectral_hpp
        pts = val / hpp if rel else self.ppm2pts(0.0) - (val / hpp)
        return pts


    def __str__(self):

        lines = []
        lines.append("------- {0} Object -------".format(self.__class__.__name__))
        lines.append("filename: %s" % self.dataset_filename)
        for block in self.blocks.values():
            lines.append(str(block))

        return '\n'.join(lines)


##########################    Public methods    #########################

    def update_for_zerofill_change(self, zf_mult):
        """
        Here we assume that the dims coming in are for the new setting of
        the zero fill parameter. We check if we already match those values
        or if we need to reset block and chain dimensional results arrays

        """
        self.blocks["spectral"].set.zero_fill_multiplier = zf_mult
        # Let everyone know that the zerofill changed
        for block in self.blocks.values():
            block.set_dims(self)
        self.user_prior.basis.update(self)


    def update_for_preprocess_change(self):
        """
        Here we assume that the dims coming in are for the new setting of
        the zero fill parameter. We check if we already match those values
        or if we need to reset block and chain dimensional results arrays

        """
        # Let everyone know that the dims in preprocess block have changed
        for block in self.blocks.values():
            block.set_dims(self)


    def set_behave_as_preset(self, flag):
        """
        This will set all 'behave_as_preset' flags in the dataset and in
        the self.blocks list to the value of flag. User is responsible for
        setting/resetting these flags using this function.

        """
        val = flag == True
        self.behave_as_preset = flag
        for block in self.blocks.values():
            block.behave_as_preset = val








########################   Inflate()/Deflate()    ########################


    def deflate(self, flavor=Deflate.ETREE, is_main_dataset=True):

        if flavor == Deflate.ETREE:
            e = ElementTree.Element("ice_view_dataset",
                                      { "id" : self.id,
                                        "version" : self.XML_VERSION})

            util_xml.TextSubElement(e, "preset_filename", self.preset_filename)

            e.append(self.user_prior.deflate())

            ee = ElementTree.SubElement(e, "blocks")

            for block in self.blocks.values():
                if not block.is_identity:
                    ee.append(block.deflate())
                #else:
                    # We don't clutter up the XML with identity blocks.
            return e

        elif flavor == Deflate.DICTIONARY:
            return self.__dict__.copy()



    def inflate(self, source):
        if hasattr(source, "makeelement"):
            # Quacks like an ElementTree.Element
            xml_version = source.get("version")
            self.id = source.get("id")

            val = source.findtext("behave_as_preset")       # default is False
            if val is not None:
                self.behave_as_preset = util_xml.BOOLEANS[val]

            for val in ("preset_filename",):
                setattr(self, val, source.findtext(val))      # this code allows 'None' value

            self.user_prior.inflate(source.find("user_prior"))

            # The individual <block> elements are wrapped in a <blocks>
            # element. The <blocks> element has no attributes and its only
            # children are <block> elements. <blocks> is just a wrapper.
            # Note that ElementTree elements with children are designed to
            # behave quite a lot like ordinary Python lists, and that's how we
            # regard this one.

            block_elements = source.find("blocks")
            if block_elements is None:
                # block_elements is None or has no kids. If either of these
                # conditions occurs, we are in undefined territory since every
                # dataset has at least a raw block.
                raise ValueError("<block> element must have children")

            for block_element in block_elements:
                self._create_block(block_element.tag, block_element)

        elif hasattr(source, "keys"):
            # Quacks like a dict
            raise NotImplementedError



    #################################################################
    ##### Public functions for Phase0/1 Frequency Shift
    #####
    ##### Phase 0 and 1 are used in a number of processing tabs (for
    ##### View typically). To facilitate set/get of these values,
    ##### which are traditionally stored in the Spectral processing
    ##### module, we create these helper functions at the level of
    ##### the Dataset
    #################################################################

    def get_phase_0(self, xyz):
        """ Returns 0th order phase for the voxel at the xyz tuple """
        return self.blocks["spectral"].get_phase_0(xyz)

    def set_phase_0(self, phase_0, xyz):
        """ Sets 0th order phase for the voxel at the xyz tuple """
        self.blocks["spectral"].set_phase_0(phase_0, xyz)

    def get_phase_1(self, xyz):
        """ Returns 1st order phase for the voxel at the xyz tuple """
        return self.blocks["spectral"].get_phase_1(xyz)

    def set_phase_1(self, phase_1, xyz):
        """ Sets 1st order phase for the voxel at the xyz tuple """
        self.blocks["spectral"].set_phase_1(phase_1, xyz)

    def get_frequency_shift(self, xyz):
        """ Returns frequency_shift for the voxel at the xyz tuple """
        return self.blocks["spectral"].get_frequency_shift(xyz)

    def set_frequency_shift(self, frequency_shift, xyz):
        """ Sets frequency_shift for the voxel at the xyz tuple """
        self.blocks["spectral"].set_frequency_shift(frequency_shift, xyz)

    def get_source_data(self, block_name):
        """
        Returns the data from the first block to the left of the named block
        that is not None

        """
        keys = list(self.blocks.keys())
        keys = keys[0:keys.index(block_name)]
        for key in keys[::-1]:
            data = self.blocks[key].data
            if data is not None:
                return data
        return self.blocks[block_name].data


    def get_source_chain(self, block_name):
        """
        Returns the chain object from the first block to the left of the named
        block that is not None

        """
        keys = list(self.blocks.keys())
        keys = keys[0:keys.index(block_name)]
        for key in keys[::-1]:
            data = self.blocks[key].chain
            if data is not None:
                return data
        return self.blocks[block_name].chain


########################   "Private" Methods    ########################


    def _create_block(self, type_info, attributes=None):
        """
        Given block type info (see below) and optional attributes (suitable
        for passing to inflate()), creates a block of the specified type,
        places it in this dataset's dict of blocks, and returns the
        newly-created block.

        The type_info can be either one of the keys in _XML_TAG_TO_SLOT_CLASS_MAP
        or a 2-tuple of (slot name, class). In the former case,
        _XML_TAG_TO_SLOT_CLASS_MAP is used to look up the 2-tuple. That makes
        this method very convenient for calling from Dataset.inflate().

        In both cases, this method replaces the class in the slot name with
        an instance of the class in the 2-tuple.

        The newly-created block is also asked to create its chain and
        set its dims.
        """
        if type_info in _XML_TAG_TO_SLOT_CLASS_MAP:
            name, klass = _XML_TAG_TO_SLOT_CLASS_MAP[type_info]
        else:
            # If this isn't a tuple, there's going to be trouble!
            name, klass = type_info

        # Instantiate and replace the existing block with the new one.
        block = klass(attributes)
        self.blocks[name] = block
        block.set_dims(self)
        # setting of helper attributes self.raw_xxx depends on self.data
        # having correct dimensions, so this has to follow set_dims()
        block.create_chain(self)

        return block



    def automatic_phasing_max_real_freq(self, freq):
        """ Return phase 0 that produces largest summed area under real data """
        max_freq = -1e40
        for i in range(-180,180):
            phase = np.exp(1j * i * common_constants.DEGREES_TO_RADIANS)
            max_  = np.sum((freq * phase).real)
            if max_ > max_freq:
                max_freq = max_
                max_index = i
        return max_index



