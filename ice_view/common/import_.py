# Python modules

import xml.etree.cElementTree as ElementTree
import logging
import gzip

# 3rd party modules

# Our modules
import ice_view.common.misc as misc
import ice_view.common.time_ as util_time
import ice_view.common.logging_ as util_logging
import ice_view.common.constants as constants


def get_element_tree(filename):
    """Given the name of an export file, returns the contents
    represented as an ElementTree.ElementTree.

    It doesn't matter if the file is compressed or not.

    This function will raise IOError if there's problems reading the file
    (doesn't exist, no read permission, etc.).

    It will raise SyntaxError if the content isn't an export file.
    """
    tree = None

    # misc.is_gzipped() calls open(), and open() raises IOError if the
    # file doesn't exist or if it exists but isn't readable.
    if misc.is_gzipped(filename):
        f = gzip.GzipFile(filename, "rb")
    else:
        f = open(filename, "rb")

    # When given a valid file object, the ElementTree ctor raises
    # SyntaxError for every garbage file type I throw at it. This is
    # perhaps a bit of an abuse of SyntaxError since it is documented as
    # being for errors in the Python parser.
    tree = ElementTree.ElementTree(file=f)

    f.close()

    if tree:
        root = tree.getroot()
        # Make sure the root tag is what I expect
        if root.tag != constants.Export.ROOT_ELEMENT_NAME:
            # May as well be consistent with ElementTree.
            raise SyntaxError

    return tree


class Importer(object):
    """An abstract base class for importers.

    When a subclass is instantiated, the source parameter can be an
    ElementTree.Element or a filename (string).
    
    If the log parameter is False, no logging is done.

    During init, this class calls get_element_tree() from this module.
    Callers should be prepared to handle the errors described there.

    Once instantiated, users should call the go() method to execute
    the import. 
    
    Subclasses of this class need to override the go() method. Subclasses 
    implementing go() must call post_import() at the end. 

    When go() is complete, the instance attributes are as follows:
      - found_count is the number of potential importables found
      - imported is a list of the objects imported

    In addition, if the import began at the root node of the XML file
    (which will be the case for most/all instances of this class instantiated
    outside of this module), the following attributes are also populated:
      - version holds the version string from the import file
      - timestamp is when the export was made
      - comment is the export comment
      - log_filename is the name of the file to which import messages were
        logged
    """
    def __init__(self, source, db, log=True):
        self.db = db

        self.root = None
        self.filename = None
        self.log_filename = None
        self.file_handler = None
        self.version = None
        self.timestamp = None
        self.comment = None
        self.found_count = 0
        self.imported = [ ]

        if hasattr(source, "makeelement"):
            # It's an ElementTree.Element
            self.root = source
        else:
            # It's a string (I hope)
            self.root = get_element_tree(source).getroot()
            self.filename = source

        if self.is_primary:
            self.version = self.root.get("version")
            self.timestamp = util_time.datetime_from_iso(self.root.findtext("timestamp"))
            self.comment = self.root.findtext("comment")

            logger = logging.getLogger(util_logging.Log.IMPORT)

            if log:
                # Set up a log handler for this import
                self.file_handler = util_logging.ImportFileHandler()
            else:
                # Log to /dev/null
                self.file_handler = util_logging.NullHandler()

            self.log_filename = self.file_handler.filename
            logger.addHandler(self.file_handler)

            # Write some metadata to the log
            logger.info("Vespa Import Log")
            logger.info("-" * 60)
            logger.info("Started at %s (%s)" % \
                        (util_time.now(util_time.DISPLAY_TIMESTAMP_FORMAT),
                         util_time.now(util_time.ISO_TIMESTAMP_FORMAT))
                       )
            if self.filename:
                logger.info("Importing from %s" % self.filename)

            s = "Export was created at %s (%s)" % \
                    (self.timestamp.strftime(util_time.DISPLAY_TIMESTAMP_FORMAT),
                    self.timestamp.isoformat())

            if self.comment:
                s += ", export comment follows --\n" + self.comment

            s += "\n"

            logger.info(s)


    @property
    def is_primary(self):
        """True if this Importer is dealing with objects that are 
        children of the XML root, False otherwise."""
        # Explicit test for None required here. See:
        # http://scion.duhs.duke.edu/vespa/project/ticket/35
        return (self.root is not None) and \
               (self.root.tag == constants.Export.ROOT_ELEMENT_NAME)


    def go(self):
        raise NotImplementedError


    def post_import(self):
        if self.is_primary:
            # Say goodbye and clean up.
            if self.file_handler:
                log = logging.getLogger(util_logging.Log.IMPORT)

                log.info("Import complete.")

                log.removeHandler(self.file_handler)


#class ExperimentImporter(Importer):
#    def __init__(self, source, db):
#        Importer.__init__(self, source, db)
#
#
#    def go(self, add_history_comment=True):
#        log = logging.getLogger(util_logging.Log.IMPORT)
#
#        for element in self.root.getiterator("experiment"):
#            self.found_count += 1
#            id_ = element.get("id")
#
#            if id_ and self.db.count_experiments(id_):
#                # Don't bother to import this; it's already in the database.
#                log.info("Ignoring experiment %s, already in database" % id_)
#            else:
#                # The id doesn't exist, so the import should proceed. However, I
#                # mustn't create a name conflict with an existing experiment.
#                # Also, I need to ensure that the pulse sequence (if any) and
#                # metabolite(s) (if any) referenced by this experiment exist.
#                importer = PulseSequenceImporter(element, self.db)
#                importer.go(add_history_comment)
#
#                # There will be zero or one pulse sequences
#                pulse_sequence = importer.imported[0] if importer.imported else None
#
#                # There should be one or more metabs, but this code doesn't
#                # need to assume that there are any at all.
#                importer = MetaboliteImporter(element, self.db)
#                importer.go(add_history_comment)
#
#                experiment = mrs_experiment.Experiment(element)
#                
#                # Imported objects are only public if they have a UUID. All of
#                # the objects we export have a UUID but 3rd party formats 
#                # converted to our format won't.
#                experiment.is_public = bool(experiment.id)
#
#                # Generate a unique name.
#                experiment.name = self.db.find_unique_name(experiment, "import")
#
#                if add_history_comment:
#                    # Append a comment marking the import
#                    _add_comment(experiment)
#
#                log.info("Importing experiment %s (%s)..." % \
#                                                (experiment.id, experiment.name))
#
#                self.db.insert_experiment(experiment)
#
#                self.imported.append(experiment)
#                
#        self.post_import()




##### Functions for Internal Use Only  ##################################

def _add_comment(imported_object):
    """Appends a comment marking the import. The passed param must be an
    object with a .comment attribute (i.e. an experiment, metab or pulse
    sequence)."""
    comment = "Imported %s\n" % util_time.now(util_time.DISPLAY_TIMESTAMP_FORMAT)
    if imported_object.comment:
        imported_object.comment += "\n" + comment
    else:
        imported_object.comment = comment


