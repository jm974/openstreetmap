# openstreetmap
Udacity Nano Degree Program: P3: Wrangle OpenStreetMap Data


# Input Data

Download all required inputs (FANTOIR a French offcial ways Database, Official French Postal Code, OSM file from OpenStreetMap)

'''
$ mkdir data

$ curl -O https://www.data.gouv.fr/s/resources/fichier-fantoir-des-voies-et-lieux-dits/20161116-165500/FANTOIR1016.zip > /tmp/FANTOIR1016.zip && unzip /tmp/FANTOIR1016.zip -d data && rm /tmp/FANTOIR1016.zip

$ curl -O http://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=true > data/laposte_hexasmal.csv

$ curl -O http://overpass-api.de/api/map?bbox=55.4871,-21.4039,55.8009,-21.1796 > data/Saint-Joseph.La-Reunion.osm
'''

# Data Auditing

Get a set of files to be manually updated for input OSM file manual cleansing.

'''
$ mkdir audit
$ audit.py -i -o data/Saint-Joseph.La-Reunion.osm -f data/FANTOIR1016 -a 974 -u audit
'''