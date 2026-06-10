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

    def image(self, frame: int = 0, wavelength_axis: np.ndarray | None = None) -> None:
        """
        Affiche l'image CCD brute d'une frame.

        Convention des axes :
            axis=0 (vertical, y)   →  axe spectral  (λ)
            axis=1 (horizontal, x) →  axe spatial

        Parameters
        ----------
        frame : int
            Indice de la frame.
        wavelength_axis : np.ndarray | None
            Si fourni, l'axe y est affiché en nm.
        """
        data = self._raw_data.frame(frame)

        _, ax = plt.subplots()

        if wavelength_axis is not None:
            # x : spatial [0, shape[1]], y : spectral [lambda_min, lambda_max]
            extent = [0, data.shape[1], wavelength_axis[0], wavelength_axis[-1]]
            im = ax.imshow(data, origin="lower", cmap="inferno",
                        aspect="auto", extent=extent)
            ax.set_ylabel("Wavelength (nm)")
        else:
            im = ax.imshow(data, origin="lower", cmap="inferno", aspect="auto")
            ax.set_ylabel("Pixel y (spectral)")

        fig = ax.get_figure()
        fig.colorbar(im, ax=ax, label="Counts")
        ax.set_title(f"Raw CCD image — frame {frame}")
        ax.set_xlabel("Pixel x (spatial)")
        plt.tight_layout()
        plt.show()

    def spectrum(self, frame: int = 0, wavelength_axis: np.ndarray | None = None,) -> None:
        """
        Affiche le spectre en counts intégré sur tous les pixels y.

        Parameters
        ----------
        frame : int
            Indice de la frame.
        """
        data = self._raw_data.frame(frame)
        spectrum = data.sum(axis=1)

        if wavelength_axis is not None:
            x_axis = wavelength_axis
            xlabel = "Wavelength (nm)"
        else:
            x_axis = np.arange(spectrum.shape[0])
            xlabel = "Pixel y"

        _, ax = plt.subplots()
        ax.plot(x_axis, spectrum)
        ax.set_title(f"Spectrum — frame {frame}")
        ax.set_xlabel(xlabel)
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
        spectrum = data.sum(axis=1)
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
        ax.set_xlabel("Pixel y")
        ax.set_ylabel("Counts")
        ax.legend()
        plt.grid()
        plt.tight_layout()
        plt.show()

    def spec_ROI_auto(
        self,
        frame: int = 0,
        spatial_roi: bool = True,
        spatial_half: int = 10,
        sigma: float = 5.0,
        n_std: float = 1.0,
        subtract_baseline: bool = False,
        photon: bool = False,
        sensitivity: float = 3.6,
        QE: float = 0.55,
        gaussian_fit: bool = False,
        plot: bool = True,
        wavelength_axis: np.ndarray | None = None,
    ) -> dict:
        """
        Détecte automatiquement le ROI spatial et spectral, puis affiche le spectre.

        Parameters
        ----------
        frame : int
            Indice de la frame.
        spatial_roi : bool
            Si False, intègre sur toutes les lignes y sans détection de ROI spatial.
        spatial_half : int
            Demi-largeur du ROI spatial en pixels y. Ignoré si spatial_roi=False.
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
            Si True, ajuste une gaussienne sur le ROI spectral.
        plot : bool
            Si False, supprime le tracé et les prints. Le dict est toujours retourné.
        wavelength_axis : np.ndarray | None
            Si fourni, l'axe x est affiché en nm. Obtenu via wavelength_axis().

        Returns
        -------
        dict
            Contient toujours 'snr'. Si gaussian_fit=True, contient également
            amplitude, center, sigma_fit, fwhm, offset, perr, center_nm.
        """

        data = self._raw_data.frame(frame)

        # ── 1. ROI spatial ────────────────────────────────────────────────
        if spatial_roi:
            col_profile = data.sum(axis=0).astype(float)
            peak_col    = int(np.argmax(col_profile))
            r0          = max(0, peak_col - spatial_half)
            r1          = min(data.shape[1], peak_col + spatial_half + 1)
        else:
            peak_col = None
            r0       = 0
            r1       = data.shape[1]

        # ── 2. Extraction spectre sur ROI spatial ─────────────────────────
        spectrum = data[:, r0:r1].sum(axis=1).astype(float)

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
        smoothed  = gaussian_filter1d(spectrum, sigma=sigma)
        threshold = smoothed.mean() + n_std * smoothed.std()
        above     = smoothed > threshold
        xmin, xmax = self._largest_region(above)

        if xmin is None:
            raise RuntimeError(
                "No signal region detected. "
                "Try reducing n_std or increasing sigma."
            )

        # ── 4. Soustraction de baseline ───────────────────────────────────
        outside  = np.concatenate([spectrum[:xmin], spectrum[xmax + 1:]])
        baseline = outside.mean()

        if subtract_baseline:
            spectrum_plot = spectrum - baseline
        else:
            spectrum_plot = spectrum

        # ── 5. Unité et axe x ─────────────────────────────────────────────
        if photon:
            unit_str = "photons"
        else:
            unit_str = (self._metadata.data_type or "counts").strip().lower()

        ylabel = unit_str + (" (baseline subtracted)" if subtract_baseline else "")

        if wavelength_axis is not None:
            x_axis = wavelength_axis
            xlabel = "Wavelength (nm)"
        else:
            x_axis = np.arange(spectrum.shape[0])
            xlabel = "Pixel x"

        # ── 6. SNR ────────────────────────────────────────────────────────
        noise     = outside.std()
        signal    = spectrum[xmin:xmax + 1].max() - baseline
        snr_value = signal / noise if noise > 0 else None

        # ── 7. Fit gaussien ───────────────────────────────────────────────
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
                    "center_nm" : float(np.interp(center, np.arange(len(wavelength_axis)), wavelength_axis))
                                  if wavelength_axis is not None else None,
                }
            except RuntimeError:
                print("Warning: Gaussian fit failed.")

        # ── 8. Tracé ──────────────────────────────────────────────────────
        if plot:
            _, ax = plt.subplots()
            ax.plot(x_axis, spectrum_plot, color="steelblue", label="Raw spectrum")
            ax.plot(x_axis, smoothed - baseline if subtract_baseline else smoothed,
                    color="orange", linewidth=2, linestyle="--", label="Smoothed")
            ax.axhline(
                threshold - baseline if subtract_baseline else threshold,
                color="gray", linestyle=":", linewidth=0.8,
                label=f"Threshold (µ + {n_std}σ)"
            )
            ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
            ax.axvspan(x_axis[xmin], x_axis[xmax], alpha=0.15, color="green",
                       label=f"Spectral ROI [{xmin}, {xmax}]")
            ax.axvline(x_axis[xmin], color="green", linestyle="--", linewidth=0.8)
            ax.axvline(x_axis[xmax], color="green", linestyle="--", linewidth=0.8)

            if gaussian_fit and fit_result is not None:
                x_fit_idx = np.linspace(xmin, xmax, 500)
                x_fit     = np.interp(x_fit_idx, np.arange(len(x_axis)), x_axis)
                if wavelength_axis is not None:
                    fwhm_label = f"FWHM={fit_result['fwhm'] * np.mean(np.diff(wavelength_axis)):.2f} nm"
                else:
                    fwhm_label = f"FWHM={fit_result['fwhm']:.1f} px"
                ax.plot(x_fit, _gaussian(x_fit_idx, *popt),
                        color="red", linewidth=1.5,
                        label=f"Gaussian fit ({fwhm_label})")

            spatial_title = (f"Spatial ROI columns [{r0}, {r1}] around x={peak_col}"
                             if spatial_roi else "No spatial ROI — full sensor integration")
            ax.set_title(f"Auto ROI spectrum — frame {frame}\n{spatial_title}")
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.legend()
            plt.grid()
            plt.tight_layout()
            roi_signal = spectrum_plot[xmin:xmax + 1]
            y_min      = spectrum_plot.min()
            y_max      = roi_signal.max()
            margin     = 0.1 * (y_max - y_min)
            ax.set_ylim(y_min - margin, y_max + margin)
            plt.show()

            spatial_print = (f"columns [{r0}, {r1}] — peak x={peak_col}"
                             if spatial_roi else "disabled (full integration)")
            print(f"Spatial ROI  : {spatial_print}")
            print(f"Spectral ROI : pixels [{xmin}, {xmax}]")
            if snr_value is not None:
                print(f"SNR          : {snr_value:.2f}  (signal={signal:.2f}, noise={noise:.2f})")
            else:
                print("SNR          : undefined (noise = 0)")
            if subtract_baseline:
                print(f"Baseline     : {baseline:.2f} {unit_str}")
            if gaussian_fit and fit_result is not None:
                print(f"Gaussian fit :")
                center_str = f"{fit_result['center']:.2f} px"
                if fit_result["center_nm"] is not None:
                    center_str += f"  ({fit_result['center_nm']:.2f} nm)"
                print(f"  Center    : {center_str}  ± {fit_result['perr'][1]:.2f}")
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
    

    def wavelength_axis(
        self,
        x_ref: float,               # Postion de la reference sur le capteur en pixel
        lambda_ref: float,          # Longueur d'onde de la reference en nm
        f: float,                   # Focale de la lentille en mm
        N: float,                   # Densité du réseau en traits/mm
        m: int,                     # Ordre de diffraction
        theta_0: float,             # Angle de diffraction de la référence en degrés
        delta: float,               # Angle entre axe optique réseau - lentille en degrés
        alpha: float,               # Angle entre axe optique lentille - caméra en degrés
        pixel_size: float,          # Taille d'un pixel en mm
    ) -> np.ndarray:

        n_pixels = self._raw_data.shape[1]
        x = np.arange(n_pixels)

        theta_r0_rad = np.deg2rad(theta_0)
        theta_l0_rad = np.deg2rad(theta_0 - delta)
        alpha_rad = np.deg2rad(alpha)
        delta_rad = np.deg2rad(delta)

        # Position physique sur le capteur
        X = (x - x_ref) * pixel_size

        # Intermédiaire B
        B = X / f + np.sin(theta_l0_rad) / np.cos(alpha_rad + theta_l0_rad)

        # Theta_s
        theta_s = np.arctan(B * np.cos(alpha_rad) / (1 + B * np.sin(alpha_rad)))

        # Relation de dispersion exacte
        wavelength = lambda_ref + (np.sin(delta_rad + theta_s) - np.sin(theta_r0_rad)) / (m * N) * 1e6

        return wavelength

    def __repr__(self) -> str:
        return (
            f"Analysis("
            f"frames={self._raw_data.n_frames}, "
            f"shape={self._raw_data.shape[1:]})"
        )