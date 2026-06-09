"""
AndorsMPQ
=========
Librairie orientée objet pour lire et analyser les fichiers .sif produits par les caméras Andor iXon Ultra.
"""

from .sif_file import SifFile

__all__ = ["SifFile"]
__version__ = "0.1.0"