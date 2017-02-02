#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility class to manage FANTOIR API for french ways and places dataset from a certified French Public Service
Reference: https://www.data.gouv.fr/fr/datasets/fichier-fantoir-des-voies-et-lieux-dits/
"""

import pandas as pd
import io
import requests


class FANTOIR(object):
    DATA_URL = "https://www.data.gouv.fr/s/resources/fichier-fantoir-des-voies-et-lieux-dits/20161116-165500/FANTOIR1016.zip"
    
    def ways(self, csv_file, code):
        self.data = pd.read_table(csv_file, header=None)
        df = self.data[self.data[0].str.startswith(code) == True][0]
        
        """
        For the project we are only considering the first 41 characters 
        in FANTOIR1016 database (see §3.4 of referenced document)
        | Code département 
        | Code direction 
        | Code commune 
        | Identifiant de la voie dans la commune 
        | Clé RIVOLI 
        | Code nature de voie 
        | Libellé voie
        """
        df = df.apply(lambda x : pd.Series(x[:41]))
        
        """
        Next we are filtering all lines not having at least 11 characters 
        before a first space Last steps: split the data into two groupes

        | Code département 
        | Code direction 
        | Code commune 
        | Identifiant de la voie dans la commune 
        | Clé RIVOLI
        | Code nature de voie 
        | Libellé voie
        """
        df["KEEP"] =df[0].apply(lambda x: len(x.split(' ')[0]) >= 11)
        df = df[df.KEEP == True][0].apply(lambda x: pd.Series([x[:11].strip(),
                                                               x[11:15].strip(), 
                                                               x[15:41].strip()]))
        df.columns = ["REFERENCE", "TYPE", "NAME"]
        df = pd.merge(left=df, right=self.way_types(), on="TYPE")[["REFERENCE",
                                                                   "TYPE", 
                                                                   "TYPE_NAME", 
                                                                   "NAME"]]
        df["FULL_NAME"] = df[["TYPE_NAME", "NAME"]].apply(lambda x: ' '.join(x), axis=1)
        
        return df
        
    def way_types(self, csv_file="data/FANTOIR1016-WAY-TYPE.csv"):
        """Return a dataframe of all different french way types
        Extracted from https://www.data.gouv.fr/s/resources/fichier-fantoir-des-voies-et-lieux-dits/community/20150512-103719/Descriptif_FANTOIR.pdf section 3.4
        """
        return pd.read_csv(csv_file, sep=";")
    
        
if __name__ == "__main__":
    
    fantoir974 = FANTOIR().ways("data/FANTOIR1016", "974")
    assert(fantoir974[fantoir974.REFERENCE == "974401A001V"].loc[0, ("FULL_NAME")] == "LOTISSEMENT PITON ROUGE")
