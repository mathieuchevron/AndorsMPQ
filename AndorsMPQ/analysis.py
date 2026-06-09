from __future__ import annotations
"""
AndorsMPQ.analysis
==================
Classe d'analyse des données brutes d'un fichier .sif Andor.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
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

    def spec_ROI_manual(self, xmin: int, xmax: int, frame: int = 0) -> None:
        """
        Affiche le spectre sur un ROI défini manuellement.

        Parameters
        ----------
        xmin : int
            Pixel x de début du ROI (inclus).
        xmax : int
            Pixel x de fin du ROI (inclus).
        frame : int
            Indice de la frame (0-based). Par défaut 0.
        """
        data = self._raw_data.frame(frame)
        spectrum = data.sum(axis=0)
        n_pixels = spectrum.shape[0]

        if xmin < 0 or xmax >= n_pixels or xmin >= xmax:
            raise ValueError(
                f"ROI invalide : xmin={xmin}, xmax={xmax} "
                f"(pixels disponibles : 0 à {n_pixels - 1})"
            )

        pixels = np.arange(xmin, xmax + 1)

        fig, ax = plt.subplots()
        ax.plot(pixels, spectrum[xmin:xmax + 1])
        ax.axvline(xmin, color="red", linestyle="--", linewidth=0.8, label=f"xmin={xmin}")
        ax.axvline(xmax, color="red", linestyle="--", linewidth=0.8, label=f"xmax={xmax}")
        ax.set_title(f"Spectre ROI manuel — frame {frame} — pixels [{xmin}, {xmax}]")
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Counts")
        ax.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()

    def spec_ROI_auto(
        self,
        frame: int = 0,
        spatial_half: int = 10,
        sigma: float = 5.0,
        n_std: float = 1.0,
    ) -> None:
        """
        Détecte automatiquement le ROI spatial et spectral, puis affiche le spectre.

        Étapes :
        1. ROI spatial  — somme selon x → profil vertical → ±spatial_half lignes
                          autour du maximum
        2. Extraction   — somme selon y uniquement sur les lignes du ROI spatial
        3. ROI spectral — lissage gaussien + seuil moyenne + n_std × écart-type
                          → région contiguë la plus large
        4. Tracé        — spectre brut limité au ROI spectral

        Parameters
        ----------
        frame : int
            Indice de la frame (0-based). Par défaut 0.
        spatial_half : int
            Demi-largeur du ROI spatial en lignes y. Par défaut 10.
        sigma : float
            Écart-type du filtre gaussien pour le lissage spectral. Par défaut 5.
        n_std : float
            Nombre d'écarts-types pour le seuil spectral. Par défaut 1.
        """
        data = self._raw_data.frame(frame)

        # ── 1. ROI spatial ────────────────────────────────────────────────
        row_profile = data.sum(axis=1).astype(float)
        peak_row = int(np.argmax(row_profile))
        r0 = max(0, peak_row - spatial_half)
        r1 = min(data.shape[0], peak_row + spatial_half + 1)

        # ── 2. Extraction spectre sur ROI spatial ─────────────────────────
        spectrum = data[r0:r1, :].sum(axis=0).astype(float)

        # ── 3. ROI spectral ───────────────────────────────────────────────
        smoothed = gaussian_filter1d(spectrum, sigma=sigma)
        threshold = smoothed.mean() + n_std * smoothed.std()
        above = smoothed > threshold
        xmin, xmax = self._largest_region(above)

        if xmin is None:
            raise RuntimeError(
                "Aucune région signal détectée. "
                "Essaie de réduire n_std ou d'augmenter sigma."
            )

        # ── 4. Tracé ──────────────────────────────────────────────────────
        pixels = np.arange(spectrum.shape[0])

        fig, ax = plt.subplots()
        ax.plot(pixels, spectrum, color="steelblue", label="Spectre brut")
        ax.plot(pixels, smoothed, color="orange", linewidth=1.5,
                linestyle="--", label="Lissé")
        ax.axhline(threshold, color="gray", linestyle=":", linewidth=0.8,
                   label=f"Seuil (µ + {n_std}σ)")
        ax.axvspan(xmin, xmax, alpha=0.15, color="green",
                   label=f"ROI spectral [{xmin}, {xmax}]")
        ax.axvline(xmin, color="green", linestyle="--", linewidth=0.8)
        ax.axvline(xmax, color="green", linestyle="--", linewidth=0.8)
        ax.set_title(
            f"Spectre ROI auto — frame {frame}\n"
            f"ROI spatial lignes [{r0}, {r1}] autour de y={peak_row}"
        )
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Counts")
        ax.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()

        print(f"ROI spatial  : lignes [{r0}, {r1}] — pic y={peak_row}")
        print(f"ROI spectral : pixels [{xmin}, {xmax}]")

    @staticmethod
    def _largest_region(mask: np.ndarray):
        """
        Retourne (xmin, xmax) de la région contiguë True la plus large.

        Parameters
        ----------
        mask : np.ndarray
            Tableau booléen 1D.

        Returns
        -------
        tuple (xmin, xmax) ou (None, None) si aucune région trouvée.
        """
        best_start, best_len = None, 0
        current_start, current_len = None, 0

        for i, val in enumerate(mask):
            if val:
                if current_start is None:
                    current_start = i
                current_len += 1
                if current_len > best_len:
                    best_len = current_len
                    best_start = current_start
            else:
                current_start = None
                current_len = 0

        if best_start is None:
            return None, None
        return best_start, best_start + best_len - 1

    def __repr__(self) -> str:
        return (
            f"Analysis("
            f"frames={self._raw_data.n_frames}, "
            f"shape={self._raw_data.shape[1:]})"
        )