from __future__ import annotations
"""
AndorsMPQ.analysis
==================
Classe d'analyse des données brutes d'un fichier .sif Andor.
"""

import numpy as np
from .raw_data import AcquisitionRawData


class Analysis:
    """
    Fournit des méthodes d'analyse à partir des données brutes.

    Reçoit un AcquisitionRawData et expose des méthodes
    pour extraire et traiter les données pixel.
    """

    def __init__(self, raw_data: AcquisitionRawData):
        """
        Parameters
        ----------
        raw_data : AcquisitionRawData
            Données pixel brutes issues de SifFile.
        """
        self._raw_data = raw_data

    def image(self, frame: int = 0) -> np.ndarray:
        """
        Retourne l'image CCD brute d'une frame.

        Parameters
        ----------
        frame : int
            Indice de la frame (0-based). Par défaut 0.

        Returns
        -------
        np.ndarray
            Tableau 2D (hauteur, largeur) en counts.
        """
        return self._raw_data.frame(frame)

    def __repr__(self) -> str:
        return (
            f"Analysis("
            f"frames={self._raw_data.n_frames}, "
            f"shape={self._raw_data.shape[1:]})"
        )