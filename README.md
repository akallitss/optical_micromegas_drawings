# OMNIS optical micromegas — drawings and insulation masks

Two-film bulk masks (M1 insulation, M2 Dynamask) for the OMNIS detector on 95 × 95 mm glass,
following the overlap scheme of the P2 basket films (`Detector_Drawings/Version_Apr26/Insulation_masks/V1`).

- `Insulation_Mask/V2/` — current films `OMNIS-Mask_M1_V2.gbr`, `OMNIS-Mask_M2_V2.gbr` and QC images
- `Insulation_Mask/V1/`, `Omnis_mask_2020.gbr` — superseded / original single mask
- `Fw__CAD_for_3D_Printer/` — holder frames (STL, inches)
- `tools/make_masks.py` — generates the films; all layout parameters at the top
- `tools/qc.py` — reads the films back, edge profiles, overlap and gap checks, QC figures
- `tools/build_viewer.py` — builds the 3D process viewers `viewer/OMNIS_V2_3D.html` and `viewer/P2_V1_3D.html`

```
python3 tools/make_masks.py && python3 tools/qc.py && python3 tools/build_viewer.py
```
Needs shapely, matplotlib, numpy, Pillow, scipy.
