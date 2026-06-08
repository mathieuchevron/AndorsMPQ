from __future__ import annotations
"""
AndorsMPQ.analysis
==================
Classe d'analyse des données brutes d'un fichier .sif Andor.
"""

import numpy as np
import matplotlib.pyplot as plt
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

    def image(self, frame: int = 0) -> None:
        """
        Affiche l'image CCD brute d'une frame.

        Parameters
        ----------
        frame : int
            Indice de la frame (0-based). Par défaut 0.
        """
        data = self._raw_data.frame(frame)

        fig, ax = plt.subplots()
        im = ax.imshow(data, origin="lower", cmap="inferno", aspect="auto")
        fig.colorbar(im, ax=ax, label="Counts")
        ax.set_title(f"Image CCD brute — frame {frame}")
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Pixel y")
        plt.tight_layout()
        plt.show()

    def spectrum(self, frame: int = 0) -> None:
        """
        Affiche le spectre en counts intégré sur tous les pixels y.
 
        Pour chaque pixel x, somme les counts sur l'ensemble des lignes y.
 
        Parameters
        ----------
        frame : int
            Indice de la frame (0-based). Par défaut 0.
        """
        data = self._raw_data.frame(frame)
        spectrum = data.sum(axis=0)
        pixels = np.arange(spectrum.shape[0])
 
        fig, ax = plt.subplots()
        ax.plot(pixels, spectrum)
        ax.set_title(f"Spectre — frame {frame}")
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Counts")
        plt.grid()
        plt.tight_layout()
        plt.show()

    def __repr__(self) -> str:
        return (
            f"Analysis("
            f"frames={self._raw_data.n_frames}, "
            f"shape={self._raw_data.shape[1:]})"
        )