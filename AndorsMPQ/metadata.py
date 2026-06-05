
# Conteneur orienté pour les métadata (décrit les conditions d'enregistrement)


from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import math

@dataclass
class AcquisitionMetadata:
    """
    Métadonnées d'acquisition extraites d'un fichier .sif Andor iXon Ultra.

    Décrit les conditions d'enregistrement : timing, détecteur, gain,
    binning, spectromètre. Ne contient pas les données pixel brutes.
    """

    # ------------------------------------------------------------------ #
    #  Timing                                                              #
    # ------------------------------------------------------------------ #
    exposure_time: Optional[float] = None
    """Temps d'exposition en secondes."""

    cycle_time: Optional[float] = None
    """Temps de cycle entre deux acquisitions en secondes."""

    accumulated_cycle_time: Optional[float] = None
    """Temps de cycle accumulé en secondes."""

    accumulated_cycles: Optional[int] = None
    """Nombre de cycles accumulés."""

    stack_cycle_time: Optional[float] = None
    """Temps de cycle pour un stack kinétique en secondes."""

    pixel_readout_time: Optional[float] = None
    """Temps de lecture par pixel en secondes."""

    experiment_time: Optional[int] = None
    """Timestamp UNIX de l'acquisition."""

    # ------------------------------------------------------------------ #
    #  Détecteur                                                           #
    # ------------------------------------------------------------------ #
    detector_temperature: Optional[float] = None
    """Température du détecteur en °C."""

    detector_type: Optional[str] = None
    """Modèle du détecteur (ex. 'DU897_BV')."""

    detector_dimensions: Optional[Tuple[int, int]] = None
    """Dimensions physiques du capteur (largeur, hauteur) en pixels."""

    # ------------------------------------------------------------------ #
    #  Gain & obturateur                                                   #
    # ------------------------------------------------------------------ #
    em_gain_dac: Optional[float] = None
    """Valeur DAC du gain EM (valeur brute, non calibrée)."""

    shutter_time: Optional[Tuple[float, float]] = None
    """Temps d'ouverture/fermeture de l'obturateur en secondes."""

    # ------------------------------------------------------------------ #
    #  Binning                                                             #
    # ------------------------------------------------------------------ #
    xbin: Optional[int] = None
    """Binning horizontal."""

    ybin: Optional[int] = None
    """Binning vertical."""

    # ------------------------------------------------------------------ #
    #  Spectromètre / calibration                                          #
    # ------------------------------------------------------------------ #
    spectrograph: Optional[str] = None
    """Nom du spectromètre associé."""

    grating_blaze: Optional[float] = None
    """Longueur d'onde de blaze du réseau en nm."""

    raman_excitation_wavelength: Optional[float] = None
    """Longueur d'onde d'excitation Raman en nm."""

    # ------------------------------------------------------------------ #
    #  Divers                                                              #
    # ------------------------------------------------------------------ #
    original_filename: Optional[str] = None
    """Nom de fichier original au moment de l'acquisition."""

    user_text: Optional[str] = None
    """Texte libre saisi par l'utilisateur dans Solis."""

    sif_version: Optional[int] = None
    """Version interne du format SIF."""

    # ------------------------------------------------------------------ #
    #  Constructeur depuis le dict brut de sif_parser                     #
    # ------------------------------------------------------------------ #
    @classmethod
    def from_raw(cls, info: dict) -> "AcquisitionMetadata":
        """
        Construit un AcquisitionMetadata à partir du dictionnaire brut
        retourné par sif_parser.

        Parameters
        ----------
        info : dict
            Dictionnaire issu du parsing bas niveau.

        Returns
        -------
        AcquisitionMetadata
        """
        def _get(key):
            val = info.get(key)
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="replace").strip()
            if val == "":
                return None
            return val

        return cls(
            # Timing
            exposure_time=_get("ExposureTime"),
            cycle_time=_get("CycleTime"),
            accumulated_cycle_time=_get("AccumulatedCycleTime"),
            accumulated_cycles=_get("AccumulatedCycles"),
            stack_cycle_time=_get("StackCycleTime"),
            pixel_readout_time=_get("PixelReadoutTime"),
            experiment_time=_get("ExperimentTime"),
            # Détecteur
            detector_temperature=_get("DetectorTemperature"),
            detector_type=_get("DetectorType"),
            detector_dimensions=_get("DetectorDimensions"),
            # Gain & obturateur
            em_gain_dac=_get("GainDAC"),
            shutter_time=_get("ShutterTime"),
            # Binning
            xbin=_get("xbin"),
            ybin=_get("ybin"),
            # Spectromètre
            spectrograph=_get("spectrograph"),
            grating_blaze=_get("GratingBlaze"),
            raman_excitation_wavelength=(
                _get("RamanExWavelength")
                if not _is_nan(_get("RamanExWavelength"))
                else None
            ),
            # Divers
            original_filename=_get("OriginalFilename"),
            user_text=_get("user_text") or None,
            sif_version=_get("SifVersion"),
        )
    
    # ------------------------------------------------------------------ #
    #  Propriétés dérivées                                                 #
    # ------------------------------------------------------------------ #
    @property
    def acquisition_datetime(self) -> Optional[datetime]:
        """Date et heure d'acquisition comme objet datetime."""
        if self.experiment_time is None:
            return None
        return datetime.fromtimestamp(self.experiment_time)

    @property
    def binning(self) -> Optional[Tuple[int, int]]:
        """Binning sous forme (xbin, ybin)."""
        if self.xbin is None or self.ybin is None:
            return None
        return (self.xbin, self.ybin)

    # ------------------------------------------------------------------ #
    #  Affichage                                                           #
    # ------------------------------------------------------------------ #
    def summary(self) -> str:
        """Retourne un résumé lisible des métadonnées principales."""
        lines = [
            "═" * 50,
            "  Métadonnées d'acquisition — Andor iXon Ultra",
            "═" * 50,
        ]

        def _row(label, value, unit=""):
            if value is None:
                return f"  {label:<30} —"
            return f"  {label:<30} {value}  {unit}".rstrip()

        dt = self.acquisition_datetime
        lines.append(_row("Date d'acquisition", dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None))
        lines.append(_row("Fichier original", self.original_filename))
        lines.append("")
        lines.append("  [Détecteur]")
        lines.append(_row("  Modèle", self.detector_type))
        lines.append(_row("  Dimensions capteur", self.detector_dimensions, "px"))
        lines.append(_row("  Température", self.detector_temperature, "°C"))
        lines.append("")
        lines.append("  [Acquisition]")
        lines.append(_row("  Temps d'exposition", self.exposure_time, "s"))
        lines.append(_row("  Temps de cycle", self.cycle_time, "s"))
        lines.append(_row("  Cycles accumulés", self.accumulated_cycles))
        lines.append(_row("  Gain EM (DAC)", self.em_gain_dac))
        lines.append(_row("  Binning (x, y)", self.binning))
        lines.append("")
        lines.append("  [Spectromètre]")
        lines.append(_row("  Spectromètre", self.spectrograph))
        lines.append(_row("  Blaze réseau", self.grating_blaze, "nm"))
        lines.append(_row("  λ excitation Raman", self.raman_excitation_wavelength, "nm"))
        if self.user_text:
            lines.append("")
            lines.append(f"  [Note utilisateur]\n  {self.user_text}")
        lines.append("═" * 50)
        return "\n".join(lines)

    def __repr__(self) -> str:
        dt = self.acquisition_datetime
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "?"
        return (
            f"AcquisitionMetadata("
            f"date={dt_str}, "
            f"detector={self.detector_type!r}, "
            f"exposure={self.exposure_time}s)"
        )


def _is_nan(val) -> bool:
    """Teste si une valeur est NaN sans lever d'exception."""
    try:
        return math.isnan(val)
    except (TypeError, ValueError):
        return False
