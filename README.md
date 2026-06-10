# AndorsMPQ

Python object-oriented library for reading and analyzing `.sif` files produced by **Andor iXon Ultra** cameras.

---

## Installation

### From GitHub

```bash
pip install git+https://github.com/mathieuchevron/AndorsMPQ.git
```

### Update

```bash
pip install --upgrade git+https://github.com/mathieuchevron/AndorsMPQ.git
```

### Dependencies

- `numpy`
- `matplotlib`
- `scipy`
- `sif_parser`

---

## Usage

### Open a file

```python
from AndorsMPQ import SifFile

f = SifFile("acquisition.sif")
```

### Access metadata

```python
# Full summary
print(f.metadata.summary())

# Individual fields
f.metadata.exposure_time          # exposure time in s
f.metadata.detector_temperature   # sensor temperature in °C
f.metadata.em_gain_dac            # EM gain (raw DAC value)
f.metadata.binning                # (xbin, ybin)
f.metadata.detector_type          # sensor model
f.metadata.acquisition_datetime   # acquisition date and time
```

### Access raw data

```python
f.raw_data.data          # np.ndarray (n_frames, height, width)
f.raw_data.frame(n)      # np.ndarray (height, width) for frame n
```

---

## Analysis

### Wavelength axis

Computes the wavelength array λ(x) for each pixel x using the exact grating spectrograph dispersion relation.

```python
wl = f.analysis.wavelength_axis(
    x_ref      = 256,    # Reference peak position on the sensor in pixels.
    lambda_ref = 800.0,  # Reference wavelength in nm.
    f          = 150.0,  # Focusing lens focal length in mm.
    N          = 300.0,  # Grating density in lines/mm.
    m          = 1,      # Diffraction order.
    theta_0    = 0.0,    # Reference diffraction angle in degrees.
    delta      = 0.0,    # Angle between grating and lens optical axes in degrees.
    alpha      = 0.0,    # Angle between lens and camera optical axes in degrees.
    pixel_size = 0.016,  # Pixel size in mm (16 µm for iXon Ultra 897).
)
```

### Raw CCD image

```python
f.analysis.image()
f.analysis.image(wavelength_axis=wl)  # x-axis in nm if wavelength_axis is provided
```

### Spectrum integrated over all y pixels

```python
f.analysis.spectrum()
f.analysis.spectrum(wavelength_axis=wl)  # x-axis in nm if wavelength_axis is provided
```

### Spectrum with manual ROI

```python
f.analysis.spec_ROI_manual(xmin=100, xmax=400)
```

### Spectrum with automatic ROI

Automatically detects the signal band (spatial ROI) and the spectral region (spectral ROI).

```python
f.analysis.spec_ROI_auto(
    frame             = 0,      # Frame index.
    spatial_roi       = True,   # If False, integrates over all y pixels (no spatial ROI).
    spatial_half      = 10,     # Half-width of the spatial ROI in pixels. Ignored if spatial_roi=False.
    sigma             = 5.0,    # Standard deviation of the Gaussian filter for spectral smoothing.
    n_std             = 1.0,    # Number of standard deviations for the spectral threshold.
    subtract_baseline = False,  # If True, subtracts the mean of pixels outside the spectral ROI.
    photon            = False,  # If True, converts the spectrum to incident photons.
    sensitivity       = 3.6,    # Conversion factor e⁻/ADU (iXon Ultra 897, 1 MHz).
    QE                = 0.55,   # Quantum efficiency of the sensor at the signal wavelength.
    gaussian_fit      = False,  # If True, fits a Gaussian to the spectral ROI.
    plot              = True,   # If False, suppresses plot and prints. Result still returned.
    wavelength_axis   = None,   # If provided, x-axis is displayed in nm.
)
```

The method always returns a dict. If `gaussian_fit=False`, only the SNR is returned:

```python
result = f.analysis.spec_ROI_auto(plot=False)
result["snr"]           # Signal-to-noise ratio
```

If `gaussian_fit=True`, the full fit parameters are returned:

```python
result = f.analysis.spec_ROI_auto(gaussian_fit=True, plot=False)
result["center"]        # Peak position in pixels
result["center_nm"]     # Peak position in nm (None if no wavelength_axis provided)
result["fwhm"]          # Full width at half maximum in pixels
result["amplitude"]     # Peak amplitude
result["sigma_fit"]     # Gaussian standard deviation in pixels
result["offset"]        # Baseline offset from the fit
result["perr"]          # 1σ uncertainties on [amplitude, center, sigma_fit, offset]
result["snr"]           # Signal-to-noise ratio
```

Typical usage with wavelength axis:

```python
wl     = f.analysis.wavelength_axis(x_ref=256, lambda_ref=800.0, f=150.0, N=300.0,
                                     m=1, theta_0=12.5, delta=0.0, alpha=0.0, pixel_size=0.016)
result = f.analysis.spec_ROI_auto(gaussian_fit=True, wavelength_axis=wl)
print(result["center_nm"])  # Peak position in nm
```

---

## Project structure

```
AndorsMPQ/
├── AndorsMPQ/
│   ├── __init__.py       # public exports
│   ├── sif_file.py       # entry point — reads and distributes data
│   ├── metadata.py       # acquisition conditions
│   ├── raw_data.py       # raw pixel data
│   └── analysis.py       # visualization and analysis
└── pyproject.toml
```

---

## Author

Mathieu Chevron — QITE internship, MPQ laboratory, Université Paris Cité