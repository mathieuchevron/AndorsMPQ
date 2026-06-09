"""
AndorsMPQ.raw_data
==================
Conteneur orienté objet pour les données pixel brutes.
"""

from __future__ import annotations
from typing import Optional
import numpy as np


class AcquisitionRawData:
    """
    Contient et expose les données pixel brutes d'un fichier .sif.
    """

    def __init__(self, data: np.ndarray):
        """
        Parameters
        ----------
        data : np.ndarray
            Tableau de shape (n_frames, height, width).
        """
        if data.ndim == 2:
            data = data[np.newaxis, ...]  # normalise en (1, H, W)
        self._data = data

    # ------------------------------------------------------------------ #
    #  Propriétés                                                          #
    # ------------------------------------------------------------------ #
    @property
    def data(self) -> np.ndarray:
        """Tableau complet (n_frames, height, width)."""
        return self._data

    @property
    def n_frames(self) -> int:
        """Nombre de frames."""
        return self._data.shape[0]

    @property
    def shape(self) -> tuple:
        """Shape du tableau (n_frames, height, width)."""
        return self._data.shape

    # ------------------------------------------------------------------ #
    #  Accès aux frames                                                    #
    # ------------------------------------------------------------------ #
    def frame(self, index: int) -> np.ndarray:
        """
        Retourne la frame d'indice `index`.

        Parameters
        ----------
        index : int
            Indice 0-based.

        Returns
        -------
        np.ndarray
            Tableau 2D (height, width).
        """
        if not (0 <= index < self.n_frames):
            raise IndexError(
                f"Indice {index} hors bornes "
                f"(fichier contient {self.n_frames} frame(s))."
            )
        return self._data[index]

    # ------------------------------------------------------------------ #
    #  Représentation                                                      #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        return (
            f"AcquisitionRawData("
            f"frames={self.n_frames}, "
            f"shape={self.shape[1:]})"
        )