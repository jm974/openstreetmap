#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility class simplifying access to all functionalties 
required for auditing an OpenStreetMap OSM file for a French Area

Tested with Map Area: Saint-Joseph - Île de La Réunion
http://www.openstreetmap.org/relation/1282272#map=12/-21.2918/55.6440
http://overpass-api.de/api/map?bbox=55.4871,-21.4039,55.8009,-21.1796

Reference: The cleansing is driven by the JSOM file format as described at http://wiki.openstreetmap.org/wiki/API_v0.6/DTD
"""

import pandas as pd
import numpy as np
import csv
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import unicodedata

import sys, getopt

from data_gouv_fr import fantoir, postalcode

class MyPrettyPrinter(pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, unicode):
            return (object.encode('utf8'), True, False)
        return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

class Audit(object):
    CITY_RE = re.compile(r'(.*)')
    POPULATION_RE = re.compile(r'^([1-9][0-9]*)$')
    POSTCODE_RE = re.compile(r'^(974[0-9]{2})$')
    DIRECTION_RE = re.compile(r'^([1-9][0-9]{0,2})$')
    CAPACITY_RE = re.compile(r'^([1-9][0-9]*)$')
    PHONE_RE = re.compile(r'^(?P<phone>(0([-.]|\s+)?|\+)(?:[0-9]([-.]|\s+)?){6,14}[0-9])\s*$')
    ELEVATION_RE = re.compile(r'^(?P<elevation>[-+]?[0-9]*\.?[0-9]+)$')
    
    def __init__(self):
        mentions = ["bis", "ter", "quater", "ante"]
        """Handle optional House Number before Street Type (french format)"""
        r_exp = r"^((?P<housenumber>(\d+)\s*(%s)?)\,?\s+)?((?P<type>(%s))\s+)?(?P<name>(.*))$" % (
            '|'.join(mentions),
            '|'.join(np.concatenate((fantoir.FANTOIR().way_types().TYPE.values,
                                     fantoir.FANTOIR().way_types().TYPE_NAME.values,
                                     ["place"]
                                    )
                                   )
                    )
        )
        
        self.way_re = re.compile(r_exp, re.IGNORECASE)
        
        # House number can be expressed with the below simplified expression:
        # HOUSENUMBER = <PO BOX>
        #             | <NUMBER>
        #             | <NUMBER> (BIS|TER...) 
        #             | <NUMBER> (BIS|TER...) (<NUMBER> 
        #             | <NUMBER> APPT {<NUMBER>, ...}
        #             | <NUMBER> (BIS|TER...) APPT {<NUMBER>, ...}
        #             | <NUMBER> (BIS|TER...) (<NUMBER>  APPT {<NUMBER>, ...}
        # the first <NUMBER> could also be considered optional (as seen in the data) 
        # adding a question mark for the first group (?:\d+\s*) of the regular expression
        
        # Note: a parser is probably more adapted for this kind of value compared to regular expression
        # but i will keep using a regular expression at this stage
        
        mention_sub_exp = "%s" % '|'.join(mentions)
        bat_sub_exp = "bat\s+[0-9a-z]+"
        appt_sub_exp = "appt\s+[0-9a-z]+(?:,[0-9a-z]+)*"
        pobox_sub_exp = "b\.?p\.?\s+[0-9 a-z]+"
        housenumber_exp = "(?:(?:\d+\s*)?(?:(?:(?:%s)?\s*)?(?:(?:(?:(?:%s)\s*)?(?:%s)?)|(?:[0-9a-z]+)?))?)|(?:%s)" % (mention_sub_exp, bat_sub_exp, appt_sub_exp, pobox_sub_exp)

        self.housenumber_re = re.compile(r"(?P<housenumber>%s)" % (housenumber_exp), re.IGNORECASE)
    
        
    def is_city_name(self, elem):
        return (elem.attrib['k'] == "addr:city")

    def is_street_name(self, elem):
        return (elem.attrib['k'] == "addr:street")

    def is_house_number(self, elem):
        return (elem.attrib['k'] == "addr:housenumber")
    
    def is_house_postcode(self, elem):
        return (elem.attrib['k'] == "addr:postcode")

    def is_postal_code(self, elem):
        return (elem.attrib['k'] == "postal_code")

    def is_population(self, elem):
        return (elem.attrib['k'] == "population")

    def is_direction(self, elem):
        return (elem.attrib['k'] == "direction")

    def is_elevation(self, elem):
        return (elem.attrib['k'] == "ele")

    def is_capacity(self, elem):
        return (elem.attrib['k'] == "capacity")
    
    def is_phone(self, elem):
        return (elem.attrib['k'] == "phone")


    def toASCII(self, x):
        """Downgrade to ascii 
        Input data are a mix of ascii or unicode string but
        all names from FANTOIR database are encoded as ascii
        """
        return unicodedata.normalize('NFKD', u'%s' % x).encode('ascii', 'ignore')

    def audit_street(self, street_types, street_names, street_name, expected_way_type, expected_way_name):
        m = self.way_re.search(street_name)
        if m:
            street_type = m.group('type')
            if street_type is None:
                street_types[street_type].add(street_name)
                street_names[street_name].add(street_name) # Manage one single for manual update
                
            name = m.group('name')
            if name is None or self.toASCII(name).upper() not in expected_way_name:
                street_names[street_name].add(street_name)
        else:
            street_names[street_name].add(street_name)
          
    def audit_city_name(self, cities, city, expected_cities):
        if not(self.CITY_RE.match(city) is None or self.toASCII(city).upper() in expected_cities):
            cities[city].add(city)
     
    def audit_house_number(self, house_numbers, house_number):
        # multiple housenumber are separated by coma... need to check each individuals one against 
        # the housenumber regular expression. As Appt keyword could be followed by a list numbers separated by a coma
        # a first check for any housenumber starting with Appt will done before the other split and check
        if bool(re.match('^Appt', house_number.strip(), re.I)):
            if self.housenumber_re.match(house_number) is None:
                house_numbers[house_number].add(house_number)
        else:
            for n in house_number.split(","):
                n = n.strip()
                if not (n.isdigit()):
                    if self.housenumber_re.match(n) is None:
                        house_numbers[house_number].add(house_number)
    
    def audit_house_postcode(self, house_postcodes, house_postcode, expected_postal_code):
        if self.POSTCODE_RE.match(house_postcode) is None or not house_postcode in expected_postal_code:
            house_postcodes[house_postcode].add(house_postcode)
    
    def audit_postal_code(self, postal_codes, postal_code, expected_postal_code):
        if self.POSTCODE_RE.match(postal_code) is None or not postal_code in expected_postal_code:
            postal_codes[postal_code].add(postal_code)
    
    def audit_population(self, populations, population):
        if self.POPULATION_RE.match(population) is None:
            populations[code].add(population)
    
    def audit_direction(self, directions, direction):
        if self.DIRECTION_RE.match(direction) is None:
            directions[code].add(direction)
    
    def audit_elevation(self, elevations, elevation):
        if self.ELEVATION_RE.match(elevation) is None:
            elevations[elevation].add(elevation)
    
    def audit_capacity(self, capacities, capacity):
        if self.CAPACITY_RE.match(capacity) is None:
            capacities[capacity].add(capacity)
    
    def audit_phone(self, phones, phone):
        if self.PHONE_RE.match(phone) is None:
            phones[phone].add(phone)
    
    
    def audit_way_node(self, osm_file, expected_way_type, expected_way_name, expected_postal_code, expected_city):
        cities = defaultdict(set)
        street_types = defaultdict(set)
        street_names = defaultdict(set)
        house_numbers = defaultdict(set)
        house_postcodes = defaultdict(set)
        postal_codes = defaultdict(set)
        populations = defaultdict(set)
        directions = defaultdict(set)
        elevations = defaultdict(set)
        capacities = defaultdict(set)
        phones = defaultdict(set)
        
        for event, elem in ET.iterparse(osm_file, events=("start",)):
            if elem.tag in ["node", "way"]:
                for tag in elem.iter("tag"):
                    if self.is_city_name(tag):
                        self.audit_city_name(cities, tag.attrib['v'], expected_city)
                    elif self.is_street_name(tag):
                        self.audit_street(street_types, street_names, tag.attrib['v'], expected_way_type, expected_way_name)
                    elif self.is_house_number(tag):
                        self.audit_house_number(house_numbers, tag.attrib['v'])
                    elif self.is_house_postcode(tag):
                        self.audit_house_postcode(house_postcodes, tag.attrib['v'], expected_postal_code)
                    elif self.is_postal_code(tag):
                        self.audit_postal_code(postal_codes, tag.attrib['v'], expected_postal_code)
                    elif self.is_population(tag):
                        self.audit_population(populations, tag.attrib['v'])
                    elif self.is_direction(tag):
                        self.audit_direction(directions, tag.attrib['v'])
                    elif self.is_elevation(tag):
                        self.audit_elevation(elevations, tag.attrib['v'])
                    elif self.is_direction(tag):
                        self.audit_capacity(capacities, tag.attrib['v'])
                    elif self.is_phone(tag):
                        self.audit_phone(phones, tag.attrib['v'])
                        
        return {
            "cities": cities, 
            "street_names": street_names, 
            "street_types": street_types, 
            "house_numbers": house_numbers, 
            "house_postcodes": house_postcodes, 
            "postal_codes": postal_codes, 
            "populations": populations, 
            "directions": directions, 
            "elevations": elevations, 
            "capacities": capacities, 
            "phones": phones  
        }   
    
    def audit(self, osm_file,
              fantoir_file="data/FANTOIR1016", 
              area_code="974",
              update_folder="data",
              verbose= False, 
              init_mapping= False
             ):
        db = fantoir.FANTOIR()
        postcodes = postalcode.PostalCode()
        
        results = self.audit_way_node(
            osm_file, 
            db.way_types().TYPE_NAME.values,
            db.ways(fantoir_file, area_code).NAME.values,
            postcodes.postcodeByLocality().keys(),
            postcodes.cityByPostcode().keys()
        )

        if init_mapping or verbose:
            for k, v in results.items():
                if init_mapping:
                    """Generate mapping file to be updated for manual data cleansing"""
                    if len(v):
                        mapping = [value for nested in v.values() for value in nested]
                        df = pd.DataFrame.from_dict({ "OLD": mapping, "NEW": mapping })
                        df.to_csv("%s/%s-update.csv" % (update_folder, k), 
                                  encoding='utf-8', 
                                  index=False, 
                                  quoting=csv.QUOTE_ALL)
                    """Once updated, the files shall be manually transferred to update folder"""
                if verbose:
                    print("++++++ AUDIT %s ++++++" %k)
                    pprint.pprint(dict(v))
                    print("")


def usage():
    print 'audit.py -i -v -o <OSM FILE> -f <FANTOIR FILE> -a <AREA> -u <AUDIT FOLDER>'

def main(argv):
    verbose = False
    init_mapping = False
    osm_file = None
    fantoir_file = None
    area_code = None
    update_folder = None
    
    try:
        opts, args = getopt.getopt(argv,"hivo:f:a:u:",["init", "verbose", 
                                                     "osm=", "fantoir=", 
                                                     "area=", "ufolder="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-i", "--init"):
            init_mapping = True
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-o", "--osm"):
             osm_file = arg
        elif opt in ("-f", "--fantoir"):
             fantoir_file = arg
        elif opt in ("-a", "--area"):
             area_code = arg
        elif opt in ("-u", "--ufolder"):
             update_folder = arg
        else:
            print("unhandled option")
            sys.exit(2)

    if osm_file is None or fantoir_file is None or area_code is None or update_folder is None:
        print("You need to supply -o, -f, -a and -u")        
        sys.exit(2)

    Audit().audit(osm_file= osm_file, 
                  fantoir_file= fantoir_file, 
                  area_code= area_code,
                  update_folder= update_folder,
                  init_mapping= init_mapping, 
                  verbose= verbose, 
                  )

if __name__ == "__main__":
    main(sys.argv[1:])
