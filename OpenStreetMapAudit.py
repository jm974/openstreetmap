#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Various auditing function to assess quality of input OSM file
"""
import pandas as pd
import numpy as np
import xml.etree.cElementTree as ET
from collections import defaultdict
import pprint

import OpenStreetMapTools

xtd = {ord(u'’'): u"'", ord(u'é'): u'e', ord(u'è'): u'e', ord(u'É'): u'E',}
def tr(x):
    if x.isalnum():
        return x.translate(xtd)
    else:
        return x.upper()

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def StreetNameToUTF8(x):
    return (u'%s' % x).encode('utf-8').strip().upper()

def audit_street_type(street_types, street_name, expected_way_type):
    m = OpenStreetMapTools.way_type_re.search(StreetNameToUTF8(street_name))
    if m:
        street_type = m.group('type')
        if street_type not in expected_way_type:
            street_types[street_type].add(StreetNameToUTF8(street_name))


def audit_street_name(osm_file, expected_way_type):
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'], expected_way_type)
                    
    return street_types

def audit(file_in, init_street_type_mapping = False):
    fantoir = FANTOIR()
    street_types = audit_street_name(file_in, fantoir.way_types().TYPE_NAME.values)
    
    if init_street_type_mapping:
        df = pd.DataFrame(street_types.keys(), columns=["OLD"])
        df["NEW"] = df["OLD"]
        df.to_csv("data/street_type_mapping.csv", encoding='utf-8', index=False)
        
    pprint.pprint(dict(street_types))
    
if __name__ == "__main__":
    OSM_FILE = "data/Saint-Joseph.La-Reunion.osm" 
    audit(OSM_FILE, FALSE)  
