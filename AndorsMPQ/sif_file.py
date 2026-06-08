from __future__ import annotations
"""
Class SifFile : Point d'entrée pour lire un fichier .sif
"""

import os

try:
    import sif_parser
except ImportError as e:
    raise ImportError("'sif_parser' is required, install it with : pip install sif_parser") from e

from .metadata import AcquisitionMetadata
from .raw_data import AcquisitionRawData
from .analysis import Analysis


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
        path : str
            Chemin vers le fichier .sif
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found : {path}")
        if not path.lower().endswith(".sif"):
            raise ValueError(f"Unexpected extension (expected .sif) : {path}")

        self._path: str = path
        self._raw_data: AcquisitionRawData
        self._metadata: AcquisitionMetadata

        self._load()

    # ------------------------------------------------------------------ #
    # Chargement interne                                                   #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        """Parse le fichier et construit les objets metadata et raw_data."""
        try:
            data, info = sif_parser.np_open(self._path)
        except SyntaxError as e:
            raise ValueError(f"Impossible to read .sif file : {e}") from e

        self._raw_data = AcquisitionRawData(data)
        self._metadata = AcquisitionMetadata.from_raw(dict(info))

    # ------------------------------------------------------------------ #
    # Propriétés publiques                                                 #
    # ------------------------------------------------------------------ #

    @property
    def path(self) -> str:
        """Chemin absolu vers le fichier .sif."""
        return os.path.abspath(self._path)

    @property
    def metadata(self) -> AcquisitionMetadata:
        """Métadonnées d'acquisition structurées."""
        return self._metadata

    @property
    def raw_data(self) -> AcquisitionRawData:
        """Données pixel brutes."""
        return self._raw_data

    @property
    def analysis(self) -> Analysis:
        """Outils d'analyse."""
        return Analysis(self._raw_data)

    # ------------------------------------------------------------------ #
    # Représentation                                                       #
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        name = os.path.basename(self._path)
        return (
            f"SifFile({name!r}, "
            f"frames={self._raw_data.n_frames}, "
            f"shape={self._raw_data.shape[1:]})"
        )