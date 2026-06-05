"""
Class SifFile : Point d'entrée pour lire un fichier .sif
"""

import os
import numpy as np
from typing import Optional
from __future__ import annotations

try:
    import sif_parser
except ImportError as e:
    raise ImportError("'sif_parser' is required, install it with : pip install sif_parser") from e

from .metadata import AcquisitionMetadata
from .raw_data import AcquisitionRawData

class SifFile:
    """
    Représente un fichier .sif

    Chargement
    ----------
    f = SifFile("fichier.sif")
    """

    def __init__(self, path: str):
        """
        Ouvre et parse un fichier .sif

        Paramètres 
        ----------
        path: str
            Chemin vers le fichier .sif
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found : {path}")
        if not path.lower().endswith(".sif"):
            raise ValueError(f"Unexpected extension (expected .sif) : {path}")
        
        self._path: str = path
        self._data: Optional[np.ndarray] = None
        self._raw_info: dict = {}

        self._load()

    # ------------ #
    # Chargement interne
    # ------------ #

    def _load(self) -> None:
        """Parse le fichier et peuple _data et _raw_info"""
        try:
            data, info = sif_parser.np_open(self._path)
        except SyntaxError as e:
            raise ValueError(f"Impossible to read .sif file : {e}") from e
        
        self._data = data
        self._raw_data = AcquisitionRawData(data)
        self._raw_info = dict(info)

    # --------- #
    # Propriétés publiques
    # --------- #

    @property
    def path(self) -> str:
        """Chemin vers le fichier .sif"""
        return os.path.abspath(self._path)
    
    @property
    def metadata(self) -> AcquisitionMetadata:
        """Métadonnées d'acquisition structurées"""
        return AcquisitionMetadata.from_raw(self._raw_info)
    
    @property
    def raw_data(self) -> AcquisitionRawData:
        return self._raw_data
    
    
    
