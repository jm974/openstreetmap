#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Various tests to assess quality of input OSM file
"""

import xml.etree.cElementTree as ET
from collections import defaultdict
import pprint

import OpenStreetMapTools

def key_type(element, keys):
    if element.tag == "tag":
        key = element.attrib['k']
        if OpenStreetMapTools.lower_colon_re.match(key):
            keys["lower_colon"] = keys["lower_colon"] + 1
        elif OpenStreetMapTools.lower_re.match(key):
            keys["lower"] = keys["lower"] + 1
        elif not OpenStreetMapTools.problemchars_re.match(key):
            keys["problemchars"] = keys["problemchars"] + 1
        else:  
            keys["other"] = keys["other"] + 1
            
    return keys

def process_map_key_type(filename):
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)
        
    return keys
        
def test_key_type(file_in):
    keys = process_map_key_type(file_in)
    pprint.pprint(keys)
    assert keys == {'lower': 28409, 'lower_colon': 5122, 'other': 0, 'problemchars': 72}


if __name__ == "__main__":
    OSM_FILE = "data/Saint-Joseph.La-Reunion.osm" 
    
    SAMPLE_FILE = "%s.sample" % OSM_FILE
    OpenStreetMapTools.process_sample(file_in=OSM_FILE, file_out=SAMPLE_FILE, k=10)
    
    test_key_type(SAMPLE_FILE)
