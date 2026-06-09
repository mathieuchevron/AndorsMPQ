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
f.analysis.spec_ROI_auto()

# Adjust parameters if needed
f.analysis.spec_ROI_auto(
    spatial_half=15,   # half-width of spatial ROI in y lines
    sigma=8,           # Gaussian smoothing (larger = smoother)
    n_std=0.5          # threshold (smaller = more inclusive)
)
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