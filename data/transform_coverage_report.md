# Transform coverage report

- Total canonical_long rows: 3983
- Canonical IDs in YAML: 22
- Real clinics in manifest: 267

## Coverage matrix (canonical × kjede)

| canonical_id | odontia | colosseum | oc | oris | single |
|---|---|---|---|---|---|
| annual_checkup | ✓ (40) | ✓ (91) | ✓ (18) | ✓ (94) | — |
| tooth_cleaning | ✓ (32) | ✓ (91) | — | — | — |
| composite_filling_one_surface | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| composite_filling_two_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| composite_filling_three_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| composite_filling_four_plus_surfaces | ✓ (24) | — | ✓ (1) | — | — |
| crown | ✓ (34) | ✓ (91) | ✓ (15) | ✓ (94) | — |
| root_canal_anterior | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) | — |
| implant_with_crown | ✓ (16) | ✓ (1) | — | ✓ (94) | — |
| tooth_extraction_simple | ✓ (34) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| tooth_extraction_complex | ✓ (6) | — | — | — | — |
| root_canal_premolar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) | — |
| root_canal_molar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (188) | — |
| xray_intraoral | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| bite_splint | ✓ (32) | — | ✓ (1) | ✓ (94) | — |
| denture_full | ✓ (31) | — | ✓ (1) | ✓ (94) | — |
| denture_partial | ✓ (1) | — | ✓ (1) | — | — |
| veneer | ✓ (23) | ✓ (91) | — | ✓ (94) | — |
| panoramic_xray | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | — |
| cbct_xray | ✓ (1) | ✓ (91) | — | ✓ (94) | — |
| anesthesia_per_dose | ✓ (32) | ✓ (91) | ✓ (13) | ✓ (94) | — |
| wisdom_tooth_surgery | ✓ (27) | ✓ (91) | ✓ (11) | ✓ (94) | — |

## Per-canonical chain coverage

- `annual_checkup`: 4/5 chains covered
- `tooth_cleaning`: 2/5 chains covered
- `composite_filling_one_surface`: 4/5 chains covered
- `composite_filling_two_surfaces`: 4/5 chains covered
- `composite_filling_three_surfaces`: 4/5 chains covered
- `composite_filling_four_plus_surfaces`: 2/5 chains covered
- `crown`: 4/5 chains covered
- `root_canal_anterior`: 4/5 chains covered
- `implant_with_crown`: 3/5 chains covered
- `tooth_extraction_simple`: 4/5 chains covered
- `tooth_extraction_complex`: 1/5 chains covered
- `root_canal_premolar`: 4/5 chains covered
- `root_canal_molar`: 4/5 chains covered
- `xray_intraoral`: 4/5 chains covered
- `bite_splint`: 3/5 chains covered
- `denture_full`: 3/5 chains covered
- `denture_partial`: 2/5 chains covered
- `veneer`: 3/5 chains covered
- `panoramic_xray`: 4/5 chains covered
- `cbct_xray`: 3/5 chains covered
- `anesthesia_per_dose`: 4/5 chains covered
- `wisdom_tooth_surgery`: 4/5 chains covered

## Empty cells (synonym-round TODO)

- `annual_checkup` × `single`
- `tooth_cleaning` × `oc`
- `tooth_cleaning` × `oris`
- `tooth_cleaning` × `single`
- `composite_filling_one_surface` × `single`
- `composite_filling_two_surfaces` × `single`
- `composite_filling_three_surfaces` × `single`
- `composite_filling_four_plus_surfaces` × `colosseum`
- `composite_filling_four_plus_surfaces` × `oris`
- `composite_filling_four_plus_surfaces` × `single`
- `crown` × `single`
- `root_canal_anterior` × `single`
- `implant_with_crown` × `oc`
- `implant_with_crown` × `single`
- `tooth_extraction_simple` × `single`
- `tooth_extraction_complex` × `colosseum`
- `tooth_extraction_complex` × `oc`
- `tooth_extraction_complex` × `oris`
- `tooth_extraction_complex` × `single`
- `root_canal_premolar` × `single`
- `root_canal_molar` × `single`
- `xray_intraoral` × `single`
- `bite_splint` × `colosseum`
- `bite_splint` × `single`
- `denture_full` × `colosseum`
- `denture_full` × `single`
- `denture_partial` × `colosseum`
- `denture_partial` × `oris`
- `denture_partial` × `single`
- `veneer` × `oc`
- `veneer` × `single`
- `panoramic_xray` × `single`
- `cbct_xray` × `oc`
- `cbct_xray` × `single`
- `anesthesia_per_dose` × `single`
- `wisdom_tooth_surgery` × `single`

## Per-clinic row counts

Sentral propagation sanity: every real clinic in a sentral chain 
(Colosseum, Oris) should have an identical row count.

- **odontia**: 32 clinic(s), variable row counts [14, 15, 16, 17, 18, 19, 20, 22, 23] ⚠
- **colosseum**: 91 clinic(s), variable row counts [16, 17] ⚠
- **oc**: 14 clinic(s), variable row counts [9, 10, 11, 15] ⚠
- **oris**: 94 clinic(s), all with 19 rows ✓
- **single**: 0 clinics with data
