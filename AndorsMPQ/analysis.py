"""
AndorsMPQ.analysis
==================
Classe d'analyse des données brutes d'un fichier .sif Andor.
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import curve_fit
from .raw_data import AcquisitionRawData
from .metadata import AcquisitionMetadata

class Analysis:
    """
    Fournit des méthodes d'analyse à partir des données brutes.
    """

    def __init__(self, raw_data: AcquisitionRawData, metadata: AcquisitionMetadata):
        self._raw_data = raw_data
        self._metadata = metadata

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
        subtract_baseline: bool = False,
        photon: bool = False,
        sensitivity: float = 3.6,
        QE: float = 0.55,
        gaussian_fit: bool = False,
        plot: bool = True,
    ) -> dict:
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
        subtract_baseline : bool
            Si True, soustrait la moyenne des pixels hors ROI spectral.
        photon : bool
            Si True, convertit le spectre en photons incidents.
        sensitivity : float
            Facteur de conversion e⁻/ADU (iXon Ultra 897, 1 MHz).
        QE : float
            Efficacité quantique du capteur à la longueur d'onde du signal.
        gaussian_fit : bool
            Si True, ajuste une gaussienne sur le ROI spectral et retourne
            les paramètres du fit.
        

        Returns
        ------
            Dict avec amplitude, center, sigma_fit, fwhm, offset, perr , snr si gaussian_fit=True.
            snr sinon
        """

        data = self._raw_data.frame(frame)

        # ── 1. ROI spatial ────────────────────────────────────────────────
        row_profile = data.sum(axis=1).astype(float)
        peak_row = int(np.argmax(row_profile))
        r0 = max(0, peak_row - spatial_half)
        r1 = min(data.shape[0], peak_row + spatial_half + 1)

        # ── 2. Extraction spectre sur ROI spatial ─────────────────────────
        spectrum = data[r0:r1, :].sum(axis=0).astype(float)

        # ── 2.5 Conversion en photons ─────────────────────────────────────
        if photon:
            dt = (self._metadata.data_type or "").strip().lower()

            if dt == "counts":
                spectrum = spectrum * sensitivity / QE
            elif dt == "electrons":
                spectrum = spectrum / QE
            elif dt == "photons":
                pass
            else:
                print(f"Warning: unknown DataType '{self._metadata.data_type}', no conversion applied.")

        # ── 3. ROI spectral ───────────────────────────────────────────────
        smoothed = gaussian_filter1d(spectrum, sigma=sigma)
        threshold = smoothed.mean() + n_std * smoothed.std()
        above = smoothed > threshold
        xmin, xmax = self._largest_region(above)

        if xmin is None:
            raise RuntimeError(
                "No signal region detected. "
                "Try reducing n_std or increasing sigma."
            )

        # ── 4. Soustraction de baseline ───────────────────────────────────
        outside = np.concatenate([spectrum[:xmin], spectrum[xmax + 1:]])
        baseline = outside.mean()

        if subtract_baseline:
            spectrum_plot = spectrum - baseline
        else:
            spectrum_plot = spectrum

        # ── 5. Unité ──────────────────────────────────────────────────────
        if photon:
            unit_str = "photons"
        else:
            unit_str = (self._metadata.data_type or "counts").strip().lower()

        ylabel = unit_str + (" (baseline subtracted)" if subtract_baseline else "")

        # ── 6. SNR ────────────────────────────────────────────────────────
        noise     = outside.std()
        signal    = spectrum[xmin:xmax + 1].max() - baseline
        snr_value = signal / noise if noise > 0 else None

        # ── 7. Fit gaussien ───────────────────────────────────
        fit_result = None
        if gaussian_fit:
            pixels_roi   = np.arange(xmin, xmax + 1)
            spectrum_roi = spectrum_plot[xmin:xmax + 1]

            def _gaussian(x, amplitude, center, sigma_g, offset):
                return amplitude * np.exp(-0.5 * ((x - center) / sigma_g) ** 2) + offset

            offset_0    = spectrum_roi.min()
            amplitude_0 = spectrum_roi.max() - offset_0
            center_0    = pixels_roi[np.argmax(spectrum_roi)]
            sigma_0     = (xmax - xmin) / 4

            try:
                popt, pcov = curve_fit(
                    _gaussian, pixels_roi, spectrum_roi,
                    p0=[amplitude_0, center_0, sigma_0, offset_0]
                )
                amplitude, center, sigma_g, offset_fit = popt
                fwhm = 2 * np.sqrt(2 * np.log(2)) * abs(sigma_g)
                perr = np.sqrt(np.diag(pcov))

                fit_result = {
                    "amplitude" : amplitude,
                    "center"    : center,
                    "sigma_fit" : abs(sigma_g),
                    "fwhm"      : fwhm,
                    "offset"    : offset_fit,
                    "perr"      : perr,
                    "snr"       : snr_value,
                }
            except RuntimeError:
                print("Warning: Gaussian fit failed.")
        
        # ── 8. Tracé ──────────────────────────────────────────────────────
        if plot:
            pixels = np.arange(spectrum.shape[0])

            _, ax = plt.subplots()
            ax.plot(pixels, spectrum_plot, color="steelblue", label="Raw spectrum")
            ax.plot(pixels, smoothed - baseline if subtract_baseline else smoothed, color="orange", linewidth=2, linestyle="--", label="Smoothed")
            ax.axhline(threshold - baseline if subtract_baseline else threshold, color="gray", linestyle=":", linewidth=0.8, label=f"Threshold (µ + {n_std}σ)")
            ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
            ax.axvspan(xmin, xmax, alpha=0.15, color="green", label=f"Spectral ROI [{xmin}, {xmax}]")
            ax.axvline(xmin, color="green", linestyle="--", linewidth=0.8)
            ax.axvline(xmax, color="green", linestyle="--", linewidth=0.8)

            if gaussian_fit and fit_result is not None:
                x_fit = np.linspace(xmin, xmax, 500)
                ax.plot(x_fit, _gaussian(x_fit, *popt),
                        color="red", linewidth=1.5,
                        label=f"Gaussian fit (FWHM={fit_result['fwhm']:.1f} px)")

            ax.set_title(
                f"Auto ROI spectrum — frame {frame}\n"
                f"Spatial ROI lines [{r0}, {r1}] around y={peak_row}"
            )
            ax.set_xlabel("Pixel x")
            ax.set_ylabel(ylabel)
            ax.legend()
            plt.grid()
            plt.tight_layout()
            roi_signal = spectrum_plot[xmin:xmax + 1]
            y_min = spectrum_plot.min()
            y_max = roi_signal.max()
            margin = 0.1 * (y_max - y_min)
            ax.set_ylim(y_min - margin, y_max + margin)
            plt.show()

            print(f"Spatial ROI  : lines [{r0}, {r1}] — peak y={peak_row}")
            print(f"Spectral ROI : pixels [{xmin}, {xmax}]")
            if snr_value is not None:
                print(f"SNR          : {snr_value:.2f}  (signal={signal:.2f}, noise={noise:.2f})")
            else:
                print("SNR          : undefined (noise = 0)")
            if subtract_baseline:
                print(f"Baseline     : {baseline:.2f} {unit_str}")
            if gaussian_fit and fit_result is not None:
                print(f"Gaussian fit :")
                print(f"  Center    : {fit_result['center']:.2f} px  ± {fit_result['perr'][1]:.2f}")
                print(f"  FWHM      : {fit_result['fwhm']:.2f} px  ± {2 * np.sqrt(2 * np.log(2)) * fit_result['perr'][2]:.2f}")
                print(f"  Amplitude : {fit_result['amplitude']:.2f}  ± {fit_result['perr'][0]:.2f}")

        return fit_result if fit_result is not None else {"snr": snr_value}

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