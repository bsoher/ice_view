#!/usr/bin/env python

# Copyright (c) 2014-2019 Brian J Soher - All Rights Reserved
# 
# Redistribution and use in source and binary forms, with or without
# modification, are not permitted without explicit permission.


# Python modules


# 3rd party modules


# Our modules
import ice_view.mrsi_dataset as mrsi_dataset

from ice_view.common.import_ import Importer



class MrsiDatasetImporter(Importer):
    def __init__(self, source):
        Importer.__init__(self, source, None, False)

    def go(self, add_history_comment=False):
        for element in self.root.getiterator("ice_view_dataset"):
            self.found_count += 1

            dataset = mrsi_dataset.Dataset(element)
            
            self.imported.append(dataset)

        self.post_import()
        
        return self.imported
    
    
