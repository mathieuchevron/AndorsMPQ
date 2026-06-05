"""
AndorsMPQ
=========
Librairie orientée objet pour lire et analyser les fichiers .sif
produits par les caméras Andor iXon Ultra (laboratoire MPQ/QITE).

Usage minimal
-------------
>>> from AndorsMPQ import SifFile
>>> f = SifFile("acquisition.sif")
>>> print(f.metadata.summary())
>>> arr = f.raw_data.data
"""

from .sif_file import SifFile
from .metadata import AcquisitionMetadata
from .raw_data import AcquisitionRawData

__all__ = ["SifFile", "AcquisitionMetadata", "AcquisitionRawData"]
__version__ = "0.1.0"