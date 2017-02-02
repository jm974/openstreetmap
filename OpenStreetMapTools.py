# -*- coding: utf-8 -*-

"""The code below is designed to ease the cleansing of https://www.openstreetmap.org OSM file format
focusing on the France or associated area

Tested with Map Area: Saint-Joseph - Île de La Réunion
http://www.openstreetmap.org/relation/1282272#map=12/-21.2918/55.6440
http://overpass-api.de/api/map?bbox=55.4871,-21.4039,55.8009,-21.1796

Reference: The cleansing is driven by the JSOM file format as described at http://wiki.openstreetmap.org/wiki/API_v0.6/DTD

Note that part of the code are inspired, modified or copy&paste from udacity quizz/course
"""

import xml.etree.cElementTree as ET
from collections import defaultdict
import codecs
import json
import re
import pprint

"""
'lower', for tags that contain only lowercase letters and are valid,
'lower_colon', for otherwise valid tags with a colon in their names,
'problemchars', for tags with problematic characters, and
"""
lower_re = re.compile(r'^([a-z]|_)*$')
lower_colon_re = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars_re = re.compile(r'^.*?[=\+/&\<\>;\'"\?%#$@\,\. \t\r\n].*?$')

"""Handle optional Street Number before Street Type
"""
way_type_re = re.compile(r'^([0-9]+\s+)?(?P<type>\b\S+\.?)', re.IGNORECASE)
way_shortcut_pattern_re = re.compile("^(?P<shortcut>[rRcC](\s+)?[nNdDcC](\s+)?[0-9]+)(?P<name>.*)")


"""List of attributes to be exported under JSON sub documents named 'created'
"""
JSON_CREATED = [ "version", "changeset", "timestamp", "user", "uid" ]

"""Default Lat/Long information
"""
lat_lon_default = [0.0, 0.0]

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def process_sample(file_in, file_out, k):
    """Generate a sample osm file from an export of any area of the world in https://www.openstreetmap.org
    The depth of elements is controlled by the input parameter k
    """
    with open(file_out, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ')

        # Write every kth top level element
        for i, element in enumerate(get_element(file_in)):
            if i % k == 0:
                output.write(ET.tostring(element, encoding='utf-8'))
                
        output.write('</osm>')

def update_name(name, type_mapping, name_mapping):
    if name in name_mapping.keys():
        name = name_mapping[name]
    
    m = way_shortcut_pattern_re.match(name)
    if m is None:
        old = name.split(" ")[0]
        return name.replace(old, type_mapping[old]).title() if old in type_mapping.keys() else name.title()
    else:
        return m.group('shortcut').replace(' ', '') + m.group('name')

def shape_tag(tag, node, street_type_mapping, street_name_mapping):
    key = tag.attrib['k']
    val = tag.attrib['v']
    
    if not problemchars_re.match(key):
        if key.startswith("addr:"):
            addr_key = tag.attrib['k'][len("addr:") : ]
            if not lower_colon_re.match(addr_key):
                if addr_key == "street":
                    node.setdefault("address", {}).update({ addr_key: update_name(val, 
                                                                                  street_type_mapping, 
                                                                                  street_name_mapping) })
                else:
                    node.setdefault("address", {}).update({ addr_key: val })
                    
    elif lower_colon_re.match(tag_key):
        node[key] = val
    else:
        node[key] = val

def shape_lat_lon(key, val):
    node.setdefault("pos", [0.0, 0.0])[0 if key == "lat" else 1] = val
    
def shape_element(element, street_type_mapping, street_name_mapping):
    node = {}
    # you should process only 2 types of top level tags: "node" and "way"
    if element.tag == "node" or element.tag == "way" :
        for key in element.attrib.keys():
            val = element.attrib[key]
            node["type"] = element.tag
            
            if key in JSON_CREATED:
                node.setdefault("created", {}).update({ key: val })
            elif key == "lat" or key == "lon":
                shape_lat_lon(key, val)
            else:
                node[key] = val
                
            for tag in element.iter("tag"):
                shape_tag(tag, node, street_type_mapping, street_name_mapping)
    
        for tag in element.iter("nd"):
            node.setdefault("node_refs", []).append(tag.attrib["ref"])

        return node
    else:
        return None

def process_map(file_in, street_type_mapping, street_name_mapping, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element, street_type_mapping, street_name_mapping)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

