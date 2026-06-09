"""
AndorsMPQ.analysis
==================
Classe d'analyse des données brutes d'un fichier .sif Andor.
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from .raw_data import AcquisitionRawData


class Analysis:
    """
    Fournit des méthodes d'analyse à partir des données brutes.
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
            Indice de la frame.
        """
        data = self._raw_data.frame(frame)

        fig, ax = plt.subplots()
        im = ax.imshow(data, origin="lower", cmap="inferno", aspect="auto")
        fig.colorbar(im, ax=ax, label="Counts")
        ax.set_title(f"Raw CCD image — frame {frame}")
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Pixel y")
        plt.tight_layout()
        plt.show()

    def spectrum(self, frame: int = 0) -> None:
        """
        Affiche le spectre en counts intégré sur tous les pixels y.

        Parameters
        ----------
        frame : int
            Indice de la frame.
        """
        data = self._raw_data.frame(frame)
        spectrum = data.sum(axis=0)
        pixels = np.arange(spectrum.shape[0])

        fig, ax = plt.subplots()
        ax.plot(pixels, spectrum)
        ax.set_title(f"Spectrum — frame {frame}")
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
            Indice de la frame.
        """
        data = self._raw_data.frame(frame)
        spectrum = data.sum(axis=0)
        n_pixels = spectrum.shape[0]

        if xmin < 0 or xmax >= n_pixels or xmin >= xmax:
            raise ValueError(
                f"Invalid ROI : xmin={xmin}, xmax={xmax} "
                f"(available pixels : 0 to {n_pixels - 1})"
            )

        pixels = np.arange(xmin, xmax + 1)

        _, ax = plt.subplots()
        ax.plot(pixels, spectrum[xmin:xmax + 1])
        ax.axvline(xmin, color="red", linestyle="--", linewidth=0.8, label=f"xmin={xmin}")
        ax.axvline(xmax, color="red", linestyle="--", linewidth=0.8, label=f"xmax={xmax}")
        ax.set_title(f"Manual ROI Spectrum — frame {frame} — pixels [{xmin}, {xmax}]")
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

        Parameters
        ----------
        frame : int
            Indice de la frame.
        spatial_half : int
            Demi-largeur du ROI spatial en lignes y.
        sigma : float
            Écart-type du filtre gaussien pour le lissage spectral.
        n_std : float
            Nombre d'écarts-types pour le seuil spectral.
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
                "No signal region detected."
                "Try reducing n_std or increasing sigma."
            )

        # ── 4. Tracé ──────────────────────────────────────────────────────
        pixels = np.arange(spectrum.shape[0])

        _, ax = plt.subplots()
        ax.plot(pixels, spectrum, color="steelblue", label="Raw spectrum")
        ax.plot(pixels, smoothed, color="orange", linewidth=2, linestyle="--", label="Smoothed")
        ax.axhline(threshold, color="gray", linestyle=":", linewidth=0.8, label=f"Threshold (µ + {n_std}σ)")
        ax.axvspan(xmin, xmax, alpha=0.15, color="green", label=f"Spectral ROI [{xmin}, {xmax}]")
        ax.axvline(xmin, color="green", linestyle="--", linewidth=0.8)
        ax.axvline(xmax, color="green", linestyle="--", linewidth=0.8)
        ax.set_title(
            f"Auto ROI spectrum — frame {frame}\n"
            f"Spatial ROI lines [{r0}, {r1}] around y={peak_row}"
        )
        ax.set_xlabel("Pixel x")
        ax.set_ylabel("Counts")
        ax.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()

        print(f"Spatial ROI : lines [{r0}, {r1}] — peak y={peak_row}")
        print(f"Spectral ROI : pixels [{xmin}, {xmax}]")

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