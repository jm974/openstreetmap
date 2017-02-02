#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility class managing access to Official French Postal Code
Reference:http://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=true
"""

import pandas as pd
import io
import requests

class PostalCode(object):
    DATA_URL = "http://datanova.legroupe.laposte.fr/explore/dataset/laposte_hexasmal/download/?format=csv&timezone=Europe/Berlin&use_labels_for_header=true"

    def __init__(self, local_file=None):
        if local_file is None:
            self.data = self.load_csv()
        else:
            self.data = pd.read_csv(local_file)

    def load_csv(self, data_url=DATA_URL, encoding='utf-8', sep=";"):
        return pd.read_csv(io.StringIO(requests.get(data_url).content.decode(encoding)), sep=sep)

    def cityByPostcode(self):
        return dict(zip(self.data.Code_postal, self.data.Nom_commune))

    def postcodeByLocality(self):
        return dict(zip(self.data.Libelle_acheminement , self.data.Code_postal))
    
    def localityByPostcode(self):
        return dict(zip(self.data.Code_postal, self.data.Libelle_acheminement))

    def save(self, local_file):
        self.data.to_csv(local_file, index=False)

if __name__ == "__main__":
    postalcode = PostalCode("data/laposte_hexasmal.csv")
    #postalcode.save("data/laposte_hexasmal.csv")
    assert(postalcode.cityByPostCode()[97480] == "ST JOSEPH")