#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Various tests to assess quality of different tags
"""

import xml.etree.cElementTree as ET
from collections import defaultdict
import os, sys, re, getopt, pprint

class TagChecker(object):
    
    """
    'lower', for tags that contain only lowercase letters and are valid,
    'lower_colon', for otherwise valid tags with a colon in their names,
    'problem_chars', for tags with problematic characters, and
    """
    LOWER_RE = re.compile(r'^([a-z]|_)*$')
    LOWER_COLON_RE = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
    PROBLEM_CHARS_RE = re.compile(r'^.*?[=\+/&\<\>;\'"\?%#$@\,\. \t\r\n].*?$')
    
    def list(self, element, keys):
        if element.tag == "tag":
            key = element.attrib['k']
            if self.LOWER_COLON_RE.match(key):
                keys["lower_colon"] = keys["lower_colon"] + 1
            elif self.LOWER_RE.match(key):
                keys["lower"] = keys["lower"] + 1
            elif not self.PROBLEM_CHARS_RE.match(key):
                keys["problemchars"] = keys["problemchars"] + 1
            else:  
                keys["other"] = keys["other"] + 1

        return keys

    def summary(self, osm_file):
        keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
        for _, element in ET.iterparse(osm_file):
            keys = self.list(element, keys)

        return keys

def usage():
    print('tags.py -o <OSM FILE>')

def main(argv):
    osm_file = None
    
    try:
        opts, args = getopt.getopt(argv,"ho:",["osm="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-o", "--osm"):
             osm_file = arg
        else:
            print("unhandled option")
            sys.exit(2)

    if osm_file is None:
        print("You need to supply -o")        
        sys.exit(2)

    pprint.pprint(TagChecker().summary(osm_file=osm_file))

if __name__ == "__main__":
    main(sys.argv[1:])
