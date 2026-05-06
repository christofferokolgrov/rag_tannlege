# Transform coverage report

- Total canonical_long rows: 3982
- Canonical IDs in YAML: 22
- Real clinics in manifest: 231

## Coverage matrix (canonical × kjede)

| canonical_id | odontia | colosseum | oc | oris |
|---|---|---|---|---|
| annual_checkup | ✓ (40) | ✓ (91) | ✓ (18) | ✓ (94) |
| tooth_cleaning | ✓ (32) | ✓ (91) | — | — |
| composite_filling_one_surface | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) |
| composite_filling_two_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) |
| composite_filling_three_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) |
| composite_filling_four_plus_surfaces | ✓ (24) | — | ✓ (1) | — |
| crown | ✓ (34) | ✓ (91) | ✓ (15) | ✓ (94) |
| root_canal_anterior | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) |
| implant_with_crown | ✓ (16) | — | — | ✓ (94) |
| tooth_extraction_simple | ✓ (34) | ✓ (91) | ✓ (14) | ✓ (94) |
| tooth_extraction_complex | ✓ (6) | — | — | — |
| root_canal_premolar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) |
| root_canal_molar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (188) |
| xray_intraoral | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) |
| bite_splint | ✓ (32) | — | ✓ (1) | ✓ (94) |
| denture_full | ✓ (31) | — | ✓ (1) | ✓ (94) |
| denture_partial | ✓ (1) | — | ✓ (1) | — |
| veneer | ✓ (23) | ✓ (91) | — | ✓ (94) |
| panoramic_xray | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) |
| cbct_xray | ✓ (1) | ✓ (91) | — | ✓ (94) |
| anesthesia_per_dose | ✓ (32) | ✓ (91) | ✓ (13) | ✓ (94) |
| wisdom_tooth_surgery | ✓ (27) | ✓ (91) | ✓ (11) | ✓ (94) |

## Per-canonical chain coverage

- `annual_checkup`: 4/4 chains covered
- `tooth_cleaning`: 2/4 chains covered
- `composite_filling_one_surface`: 4/4 chains covered
- `composite_filling_two_surfaces`: 4/4 chains covered
- `composite_filling_three_surfaces`: 4/4 chains covered
- `composite_filling_four_plus_surfaces`: 2/4 chains covered
- `crown`: 4/4 chains covered
- `root_canal_anterior`: 4/4 chains covered
- `implant_with_crown`: 2/4 chains covered
- `tooth_extraction_simple`: 4/4 chains covered
- `tooth_extraction_complex`: 1/4 chains covered
- `root_canal_premolar`: 4/4 chains covered
- `root_canal_molar`: 4/4 chains covered
- `xray_intraoral`: 4/4 chains covered
- `bite_splint`: 3/4 chains covered
- `denture_full`: 3/4 chains covered
- `denture_partial`: 2/4 chains covered
- `veneer`: 3/4 chains covered
- `panoramic_xray`: 4/4 chains covered
- `cbct_xray`: 3/4 chains covered
- `anesthesia_per_dose`: 4/4 chains covered
- `wisdom_tooth_surgery`: 4/4 chains covered

## Empty cells (synonym-round TODO)

- `tooth_cleaning` × `oc`
- `tooth_cleaning` × `oris`
- `composite_filling_four_plus_surfaces` × `colosseum`
- `composite_filling_four_plus_surfaces` × `oris`
- `implant_with_crown` × `colosseum`
- `implant_with_crown` × `oc`
- `tooth_extraction_complex` × `colosseum`
- `tooth_extraction_complex` × `oc`
- `tooth_extraction_complex` × `oris`
- `bite_splint` × `colosseum`
- `denture_full` × `colosseum`
- `denture_partial` × `colosseum`
- `denture_partial` × `oris`
- `veneer` × `oc`
- `cbct_xray` × `oc`

## Per-clinic row counts

Sentral propagation sanity: every real clinic in a sentral chain 
(Colosseum, Oris) should have an identical row count.

- **odontia**: 32 clinic(s), variable row counts [14, 15, 16, 17, 18, 19, 20, 22, 23] ⚠
- **colosseum**: 91 clinic(s), all with 16 rows ✓
- **oc**: 14 clinic(s), variable row counts [9, 10, 11, 15] ⚠
- **oris**: 94 clinic(s), all with 19 rows ✓
