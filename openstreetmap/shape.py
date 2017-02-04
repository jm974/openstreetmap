#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""The code below is designed to ease the cleansing of https://www.openstreetmap.org OSM file format
focusing on French area

Tested with Map Area: Saint-Joseph - Île de La Réunion
http://www.openstreetmap.org/relation/1282272#map=12/-21.2918/55.6440
http://overpass-api.de/api/map?bbox=55.4871,-21.4039,55.8009,-21.1796

Reference: The cleansing is driven by the JSOM file format as described at http://wiki.openstreetmap.org/wiki/API_v0.6/DTD

Note that part of the code are inspired, modified or copy&paste from udacity quizz/course
"""
import pandas as pd
import numpy as np
import xml.etree.cElementTree as ET
from collections import defaultdict
import codecs
import json
import re
import pprint
import sys, os, getopt
import unicodedata

from data_gouv_fr import fantoir, postalcode

class Shape(object):
    """
    'lower', for tags that contain only lowercase letters and are valid,
    'lower_colon', for otherwise valid tags with a colon in their names,
    'problem_chars', for tags with problematic characters, and
    """
    LOWER_RE = re.compile(r'^([a-z]|_)*$')
    LOWER_COLON_RE = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
    PROBLEM_CHARS_RE = re.compile(r'^.*?[=\+/&\<\>;\'"\?%#$@\,\. \t\r\n].*?$')
    
    """List of attributes to be exported under JSON sub documents named 'created'
    """
    JSON_CREATED = [ "version", "changeset", "timestamp", "user", "uid" ]

    def update_key(self, val, mapping):
        if val in mapping.keys():
            val = mapping[val]
        return val

    def shape_tag(self, tag, node, mappings):
        key = tag.attrib['k']
        val = tag.attrib['v']
 
        if not self.PROBLEM_CHARS_RE.match(key):
            if key.startswith("addr:"):
                address = node.setdefault("address", {})
                addr_key = tag.attrib['k'][len("addr:") : ]
                if not self.LOWER_COLON_RE.match(addr_key):
                    if addr_key == "street":
                        new_val = self.update_key(u'%s' % val, mappings["street_names"])
                        address.update({ addr_key: new_val })
                    elif addr_key == "city":
                        new_val = self.update_key(u'%s' % val, mappings["cities"])
                        address.update({ addr_key: new_val })
                    elif addr_key == "housenumber":
                        new_val = self.update_key(u'%s' % val, mappings["house_numbers"])
                        address.update({ addr_key: new_val})
                    elif addr_key == "postcode":
                        # one fix for an extra space character inside the postcode value
                        address.update({ addr_key: self.update_key(val.replace(' ', ''), mappings["house_postcodes"]) })
                    else:
                        address.update({ addr_key: u'%s' % val })
            
            elif key == "phone":
                node[key] = self.update_key(val, mappings["phones"])
            elif key == "capacity":
                node[key] = self.update_key(val, mappings["capacities"])
            elif key == "direction":
                node[key] = self.update_key(val, mappings["directions"])
            elif key == "ele":
                node[key] = self.update_key(val, mappings["elevations"])
            elif key == "postal_code":
                node[key] = self.update_key(val, mappings["postal_codes"])
            elif key == "population":
                node[key] = self.update_key(val, mappings["populations"])
            if key == "name":
                node[key] = self.update_key(u'%s' % val, mappings["street_names"])
            elif self.LOWER_RE.match(key):
                node[key] = u'%s' % val

    def shape_lat_lon(self, node, key, val):
        node.setdefault("pos", [0.0, 0.0])[0 if key == "lat" else 1] = float(val)

    def shape_element(self, element, mappings):
        node = {}
        # you should process only 2 types of top level tags: "node" and "way"
        if element.tag == "node" or element.tag == "way" :
            created = node.setdefault("created", {})
            for key in element.attrib.keys():
                val = element.attrib[key]
                node["type"] = element.tag

                if key in self.JSON_CREATED:
                    created.update({ key: val })
                elif key == "lat" or key == "lon":
                    self.shape_lat_lon(node, key, val)
                else:
                    node[key] = val

                for tag in element.iter("tag"):
                    self.shape_tag(tag, node, mappings)

            node_refs = node.setdefault("node_refs", [])        
            for tag in element.iter("nd"):
                node_refs.append(tag.attrib["ref"])

            return node
        else:
            return None

    def shape(self, osm_file, mappings, pretty = False):
        # You do not need to change this file
        file_out = "{0}.json".format(osm_file)
        data = []
        with codecs.open(file_out, "w", "utf-8") as fo:
            for _, element in ET.iterparse(osm_file):
                el = self.shape_element(element, mappings)
                if el:
                    data.append(el)
                    if pretty:
                        fo.write(json.dumps(el, indent=2, ensure_ascii=False, encoding='utf8')+"\n")
                    else:
                        fo.write(json.dumps(el, ensure_ascii=False, encoding='utf8') + "\n")
        return data
    
def usage():
    print 'shape.py -i -v -o <OSM FILE> -u <UPDATE MAPPING FOLDER>'

def main(argv):
    pretty = False
    osm_file = None
    update_folder = None
    
    try:
        opts, args = getopt.getopt(argv,"hpvo:u:",["pretty", "osm=", "ufolder="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-p", "--pretty"):
            pretty = True
        elif opt in ("-o", "--osm"):
             osm_file = arg
        elif opt in ("-u", "--ufolder"):
             update_folder = arg
        else:
            print("unhandled option")
            sys.exit(2)

    if osm_file is None or update_folder is None:
        print("You need to supply -o and -u")        
        sys.exit(2)

    """Get all updated mapped key"""
    mapping_files = [
        "cities", 
        "street_names", 
        "street_types", 
        "house_numbers", 
        "house_postcodes", 
        "postal_codes", 
        "populations", 
        "directions", 
        "elevations", 
        "capacities", 
        "phones", 
        "ref_insees"
    ]
    
    mappings = {}
    for f in mapping_files:
        mappings[f] = {}
        
    for f in [mf for mf in mapping_files if os.path.exists("%s/%s-update.csv" % (update_folder, mf))]:
        df = pd.read_csv("%s/%s-update.csv" % (update_folder, f), encoding = 'utf-8')
        mappings[f] = df.set_index("NEW")["OLD"].to_dict()
        
    data = Shape().shape(
        osm_file= osm_file,
        mappings=mappings, 
        pretty=pretty
    )
    
    print("- SAMPLE -")
    pprint.pprint([x for x in data if x["id"] == "3480487005"])
    print("")
    print("Number of documents: %d" %len(data))
    
if __name__ == "__main__":
    main(sys.argv[1:])
    