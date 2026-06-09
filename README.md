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
print(...)

f.metadata.exposure_time          # exposure time in s
f.metadata.detector_temperature   # sensor temperature in °C
f.metadata.em_gain_dac            # EM gain (raw DAC value)
f.metadata.binning                # (xbin, ybin)
f.metadata.detector_type          # sensor model
f.metadata.acquisition_datetime   # acquisition date and time
...
```

### Access raw data

```python
tab = f.raw_data.data          # np.ndarray (n_frames, height, width)

tab = f.raw_data.frame(n)      # np.ndarray (height, width) for frame n
```

---

## Analysis

### Raw CCD image

```python
f.analysis.image()
```

### Spectrum integrated over all y pixels

```python
f.analysis.spectrum()
```

### Spectrum with manual ROI

```python
f.analysis.spec_ROI_manual(xmin=100, xmax=400)
```

### Spectrum with automatic ROI

Automatically detects the signal band (spatial ROI) and the spectral region (spectral ROI).

```python
f.analysis.spec_ROI_auto(
    frame = 0,                  # Frame index.
    spatial_half = 10,          # Half-width of the spatial ROI in y-lines.
    sigma = 5.0,                # Standard deviation of the Gaussian filter for spectral smoothing.
    n_std = 1.0,                # Number of standard deviations for the spectral threshold.
    subtract_baseline = False,  # If True, subtracts the mean of pixels outside the spectral ROI.
    photon = False,             # If True, converts the spectrum to incident photons.
    sensitivity = 3.6,          # Conversion factor e⁻/ADU (iXon Ultra 897, 1 MHz).
    QE = 0.55,                  # Quantum efficiency of the sensor at the signal wavelength.
    gaussian_fit = False,       # If True, fits a Gaussian to the spectral ROI.
    plot = True,                # If False, suppresses plot and prints. Result still returned.
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
result["fwhm"]          # Full width at half maximum in pixels
result["amplitude"]     # Peak amplitude
result["sigma_fit"]     # Gaussian standard deviation in pixels
result["offset"]        # Baseline offset from the fit
result["perr"]          # 1σ uncertainties on [amplitude, center, sigma_fit, offset]
result["snr"]           # Signal-to-noise ratio
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