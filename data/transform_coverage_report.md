# Transform coverage report

- Total canonical_long rows: 4244
- Canonical IDs in YAML: 26
- Real clinics in manifest: 245

## Coverage matrix (canonical × kjede)

| canonical_id | odontia | colosseum | oc | oris | single |
|---|---|---|---|---|---|
| annual_checkup | ✓ (40) | ✓ (91) | ✓ (18) | ✓ (94) | ✓ (31) |
| tooth_cleaning | ✓ (32) | ✓ (91) | — | — | ✓ (16) |
| composite_filling_one_surface | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (12) |
| composite_filling_two_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (12) |
| composite_filling_three_surfaces | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (12) |
| composite_filling_four_plus_surfaces | ✓ (24) | — | ✓ (1) | — | ✓ (2) |
| crown | ✓ (34) | ✓ (91) | ✓ (15) | ✓ (94) | ✓ (17) |
| root_canal_anterior | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) | ✓ (12) |
| implant_with_crown | ✓ (16) | ✓ (1) | — | ✓ (94) | ✓ (10) |
| tooth_extraction_simple | ✓ (34) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (13) |
| tooth_extraction_complex | ✓ (6) | — | — | — | ✓ (13) |
| root_canal_premolar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (94) | ✓ (9) |
| root_canal_molar | ✓ (33) | ✓ (91) | ✓ (1) | ✓ (188) | ✓ (10) |
| xray_intraoral | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (10) |
| bite_splint | ✓ (32) | — | ✓ (1) | ✓ (94) | ✓ (12) |
| denture_full | ✓ (31) | — | ✓ (1) | ✓ (94) | ✓ (9) |
| denture_partial | ✓ (1) | — | ✓ (1) | — | ✓ (7) |
| veneer | ✓ (23) | ✓ (91) | — | ✓ (94) | ✓ (6) |
| panoramic_xray | ✓ (32) | ✓ (91) | ✓ (14) | ✓ (94) | ✓ (8) |
| cbct_xray | ✓ (1) | ✓ (91) | — | ✓ (94) | ✓ (2) |
| anesthesia_per_dose | ✓ (32) | ✓ (91) | ✓ (13) | ✓ (94) | ✓ (9) |
| wisdom_tooth_surgery | ✓ (27) | ✓ (91) | ✓ (11) | ✓ (94) | ✓ (8) |
| bridge | — | — | — | — | ✓ (2) |
| whitening | — | — | — | — | ✓ (13) |
| periodontitis_treatment | — | — | — | — | ✓ (4) |
| inlay_onlay | — | — | — | — | ✓ (2) |

## Per-canonical chain coverage

- `annual_checkup`: 5/5 chains covered
- `tooth_cleaning`: 3/5 chains covered
- `composite_filling_one_surface`: 5/5 chains covered
- `composite_filling_two_surfaces`: 5/5 chains covered
- `composite_filling_three_surfaces`: 5/5 chains covered
- `composite_filling_four_plus_surfaces`: 3/5 chains covered
- `crown`: 5/5 chains covered
- `root_canal_anterior`: 5/5 chains covered
- `implant_with_crown`: 4/5 chains covered
- `tooth_extraction_simple`: 5/5 chains covered
- `tooth_extraction_complex`: 2/5 chains covered
- `root_canal_premolar`: 5/5 chains covered
- `root_canal_molar`: 5/5 chains covered
- `xray_intraoral`: 5/5 chains covered
- `bite_splint`: 4/5 chains covered
- `denture_full`: 4/5 chains covered
- `denture_partial`: 3/5 chains covered
- `veneer`: 4/5 chains covered
- `panoramic_xray`: 5/5 chains covered
- `cbct_xray`: 4/5 chains covered
- `anesthesia_per_dose`: 5/5 chains covered
- `wisdom_tooth_surgery`: 5/5 chains covered
- `bridge`: 1/5 chains covered
- `whitening`: 1/5 chains covered
- `periodontitis_treatment`: 1/5 chains covered
- `inlay_onlay`: 1/5 chains covered

## Empty cells (synonym-round TODO)

- `tooth_cleaning` × `oc`
- `tooth_cleaning` × `oris`
- `composite_filling_four_plus_surfaces` × `colosseum`
- `composite_filling_four_plus_surfaces` × `oris`
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
- `bridge` × `odontia`
- `bridge` × `colosseum`
- `bridge` × `oc`
- `bridge` × `oris`
- `whitening` × `odontia`
- `whitening` × `colosseum`
- `whitening` × `oc`
- `whitening` × `oris`
- `periodontitis_treatment` × `odontia`
- `periodontitis_treatment` × `colosseum`
- `periodontitis_treatment` × `oc`
- `periodontitis_treatment` × `oris`
- `inlay_onlay` × `odontia`
- `inlay_onlay` × `colosseum`
- `inlay_onlay` × `oc`
- `inlay_onlay` × `oris`

## Per-clinic row counts

Sentral propagation sanity: every real clinic in a sentral chain 
(Colosseum, Oris) should have an identical row count.

- **odontia**: 32 clinic(s), variable row counts [14, 15, 16, 17, 18, 19, 20, 22, 23] ⚠
- **colosseum**: 91 clinic(s), variable row counts [16, 17] ⚠
- **oc**: 14 clinic(s), variable row counts [9, 10, 11, 15] ⚠
- **oris**: 94 clinic(s), all with 19 rows ✓
- **single**: 14 clinic(s), variable row counts [3, 5, 9, 17, 18, 19, 22, 23, 25, 26, 27, 30] ⚠
