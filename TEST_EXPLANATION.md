# LTB Evidence Brief Generator — Test Suite Explanation

## What This Test Suite Does

This test suite automatically checks that the LTB Evidence Brief Generator works correctly. It creates fake but realistic evidence files — photos of apartment damage in every supported image format (PNG, JPEG, WEBP, GIF, BMP, TIFF, HEIC), rent payment records, demand letters, inspection reports, communication logs — uploads them through the app the same way a real user would, generates PDF briefs, and checks that everything comes back without errors.

Every test run produces a timestamped log (both a JSON file for machines and a plain text file for humans) so you have a paper trail of what was tested and what passed or failed.

---

## How to Run It

From the `ltb_tool` folder:

```bash
# Quick run — about 3 seconds, covers everything except the AI model:
python3 test_ltb_tool.py

# Full run — about 17 seconds, also tests the semantic evidence analyzer:
python3 test_ltb_tool.py --include-slow
```

---

## Folder Structure

Everything the test suite uses and produces is saved in `test_samples/` so you can inspect it:

```
test_samples/
├── uploaded_files/          52 files — every fake evidence file fed into the app
├── generated_briefs/        15 files — every PDF brief the app produced
└── test_logs/                2 files — structured + human-readable logs
```

---

## test_samples/uploaded_files/ — Every File the Tests Upload (52 files)

Each file is named with its test ID prefix so you can match it to the test that uses it. You can open every one of them.

### Upload test files (UP-001 through UP-016) — 17 files

| File | Test | What is inside | Size |
|------|------|---------------|------|
| `UP001_unit_hallway_photo.png` | UP-001 | A 400x300 hallway scene — brown door with gold handle, window with crossbars, beige walls, tan floor. Labeled "Unit 4B — Hallway" with date 2026-01-15. | 3,619 B |
| `UP002_kitchen_water_damage.jpg` | UP-002 | An 800x600 kitchen — three wooden cabinets, ceiling with large brownish water stain. Labeled "Kitchen ceiling — water damage" with address and date 2026-02-10. | 31,860 B |
| `UP003_broken_window_latch.webp` | UP-003 | A 100x100 window frame with crossbars. Red X drawn where the latch should be. | 664 B |
| `UP004_high_res_unit_photo.png` | UP-004 | Same hallway scene at 2000x2000 resolution. Tests thumbnail resizing to 300px max. | 19,055 B |
| `UP005_unit_photo_transparent.png` | UP-005 | Same hallway at 400x300 with transparency channel (RGBA). Tests transparent PNGs are still recognized. | 3,953 B |
| `UP006a_hallway_photo_1.png` | UP-006 | A 300x250 hallway photo. First of 3 files in multi-upload test. | 3,229 B |
| `UP006b_bathroom_damage.jpg` | UP-006 | A 600x400 damage photo. Second of multi-upload batch. | 27,926 B |
| `UP006c_bedroom_window.webp` | UP-006 | A 200x200 window photo. Third of multi-upload batch. | 1,112 B |
| `UP007_rent_payment_record.pdf` | UP-007 | One-page PDF "Rent Payment Record." Tenant Jane Doe, Unit 4B. 6-column table: Jan–May 2026 payments. Jan/Feb paid. March short. Apr/May unpaid. Balance $4,650. | 2,565 B |
| `UP008_maintenance_inspection_report.pdf` | UP-008 | One-page PDF "Maintenance Inspection Report." Inspector Mike Chen. Three issues: ceiling water stain, broken window latch, dead exhaust fan. Embedded photo placeholder. | 8,473 B |
| `UP009_demand_letter_rent_arrears.docx` | UP-009 | Word document. Formal demand letter from Robert Smith, ABC Property Management to Jane Doe. $2,800 in arrears. Cites Residential Tenancies Act, gives 14 days to pay. | 37,143 B |
| `UP010_tenant_communication_log.md` | UP-010 | Markdown timeline. Five entries: Jan 15 ceiling leak, Feb 3 late rent, Mar 1 partial rent, Mar 5 N4 served, Mar 10 LTB filed. | 780 B |
| `UP012_corrupt_file.jpg` | UP-012 | 14 bytes of garbage with JPEG header. Tests crash resistance on invalid files. | 14 B |
| `UP013_front_door_damage.gif` | UP-013 | A 400x300 GIF of a front door with red scratch marks across it. Gold door knob. Labeled "Front door — scratch damage" with date 2026-02-20. | 4,714 B |
| `UP014_bathroom_tile_cracked.bmp` | UP-014 | A 400x300 BMP of bathroom tiles in a grid pattern with a jagged crack running diagonally through the center, including branching cracks. Labeled "Bathroom tile — cracked" with date 2026-01-28. | 360,054 B |
| `UP015_bedroom_mold_growth.tiff` | UP-015 | A 400x300 TIFF of a bedroom wall with a baseboard at the bottom and about 20 dark greenish-brown mold splotches scattered across the wall. Labeled "Bedroom wall — mold growth" with date 2026-03-01. | 360,140 B |
| `UP016_carpet_stain.heic` | UP-016 | A 400x300 HEIC photo of a carpet with horizontal texture lines and a large dark stain in the center. Labeled "Living room — carpet stain" with date 2026-02-14. The app converts this to JPEG on upload. | 4,846 B |

Note: UP-011 sends an empty POST with no file, so there is no file to save.

### Generation test upload files (GEN-002 through GEN-015) — 35 files

Each generation test uploads its own files before asking the app to build a brief.

| File | Test | What is inside | Size |
|------|------|---------------|------|
| `GEN002_kitchen_water_damage.jpg` | GEN-002 | 800x600 kitchen water damage photo. Single photo in a one-tab brief. | 31,860 B |
| `GEN003a_kitchen_ceiling.jpg` | GEN-003 | 400x300 damage photo. First of 3 in multi-photo test. | 20,988 B |
| `GEN003b_bathroom_mold.jpg` | GEN-003 | 500x350 damage photo. Second of 3. | 23,457 B |
| `GEN003c_bedroom_window.jpg` | GEN-003 | 600x400 damage photo. Third of 3. | 27,926 B |
| `GEN004a_evidence_n4_notice.png` | GEN-004 | 300x250 evidence photo for "N4 Notice" tab. | 3,229 B |
| `GEN004b_evidence_financial.png` | GEN-004 | 300x250 evidence photo for "Financial Records" tab. | 3,229 B |
| `GEN004c_evidence_communication.png` | GEN-004 | 300x250 evidence photo for "Communication" tab. | 3,229 B |
| `GEN005a_n4_notice_page1.png` | GEN-005 | 300x400 evidence image. Tab 1, page 1 of 2. | 3,747 B |
| `GEN005b_n4_notice_page2.png` | GEN-005 | 350x430 evidence image. Tab 1, page 2 of 2. | 3,917 B |
| `GEN005c_rent_ledger_jan.png` | GEN-005 | 300x400. Tab 2, page 1. | 3,747 B |
| `GEN005d_rent_ledger_feb.png` | GEN-005 | 350x430. Tab 2, page 2. | 3,917 B |
| `GEN005e_lease_page1.png` | GEN-005 | 300x400. Tab 3, page 1. | 3,747 B |
| `GEN005f_lease_page2.png` | GEN-005 | 350x430. Tab 3, page 2. | 3,917 B |
| `GEN005g_email_screenshot1.png` | GEN-005 | 300x400. Tab 4, page 1. | 3,747 B |
| `GEN005h_text_messages.png` | GEN-005 | 350x430. Tab 4, page 2. | 3,917 B |
| `GEN005i_kitchen_damage.png` | GEN-005 | 300x400. Tab 5, page 1. | 3,747 B |
| `GEN005j_hallway_photo.png` | GEN-005 | 350x430. Tab 5, page 2. | 3,917 B |
| `GEN006_maintenance_issue_photo.jpg` | GEN-006 | 800x600 damage photo for N5 maintenance brief. | 31,860 B |
| `GEN007_demand_letter.docx` | GEN-007 | Demand letter DOCX. App converts to PDF and embeds. | 37,143 B |
| `GEN008_rent_payment_record.pdf` | GEN-008 | Rent ledger PDF. App renders and embeds. | 2,565 B |
| `GEN010_front_door_damage.gif` | GEN-010 | 400x300 GIF door damage photo for GIF-in-brief test. | 4,714 B |
| `GEN011_bathroom_tile_cracked.bmp` | GEN-011 | 400x300 BMP cracked tile for BMP-in-brief test. | 360,054 B |
| `GEN012_bedroom_mold_growth.tiff` | GEN-012 | 400x300 TIFF mold photo for TIFF-in-brief test. | 360,140 B |
| `GEN013_communication_log.md` | GEN-013 | Markdown timeline for Markdown-in-brief test. | 780 B |
| `GEN014_carpet_stain.heic` | GEN-014 | 400x300 HEIC carpet stain for HEIC-in-brief test. | 4,846 B |
| `GEN015a_kitchen_damage.jpg` | GEN-015 | 500x400 JPEG for all-formats mixed brief. | 26,240 B |
| `GEN015b_hallway_evidence.png` | GEN-015 | 300x250 PNG for all-formats mixed brief. | 3,229 B |
| `GEN015c_window_latch.webp` | GEN-015 | 200x200 WEBP for all-formats mixed brief. | 1,112 B |
| `GEN015d_door_scratches.gif` | GEN-015 | 300x250 GIF for all-formats mixed brief. | 4,275 B |
| `GEN015e_tile_crack.bmp` | GEN-015 | 300x250 BMP for all-formats mixed brief. | 225,054 B |
| `GEN015f_wall_mold.tiff` | GEN-015 | 300x250 TIFF for all-formats mixed brief. | 225,140 B |
| `GEN015g_rent_record.pdf` | GEN-015 | Rent payment PDF for all-formats mixed brief. | 2,565 B |
| `GEN015h_comm_log.md` | GEN-015 | Markdown log for all-formats mixed brief. | 780 B |
| `GEN015i_demand_letter.docx` | GEN-015 | Demand letter DOCX for all-formats mixed brief. | 37,143 B |
| `GEN015j_carpet_photo.heic` | GEN-015 | HEIC carpet stain for all-formats mixed brief. | 4,846 B |

---

## test_samples/generated_briefs/ — Every PDF Brief the Tests Produce (15 files)

These are the actual output PDFs that the LTB tool generated. You can open each one in any PDF reader.

| File | Test | What it contains | Size |
|------|------|-----------------|------|
| `GEN001_minimal_brief_empty_tab.pdf` | GEN-001 | Title page (ABC Property Management vs. Jane Doe, TSL-99999-26), table of contents, one tab divider ("Empty Tab") showing "No files uploaded for this tab." Smallest possible brief. | 4,442 B |
| `GEN002_single_photo_brief.pdf` | GEN-002 | Title page, TOC, one tab ("Unit Condition Photos") with kitchen water damage JPEG embedded full-page. | 25,031 B |
| `GEN003_multi_photo_brief.pdf` | GEN-003 | Title page, TOC, one tab ("Unit Damage Photos") with 3 JPEG damage photos each on its own page. | 59,475 B |
| `GEN004_three_tabs_brief.pdf` | GEN-004 | Title page, TOC, three tabs: "N4 Notice," "Financial Records," "Communication" — each with one PNG evidence photo. | 11,831 B |
| `GEN005_five_tabs_stress_brief.pdf` | GEN-005 | Title page, TOC, five tabs with 2 PNG images each (10 total): N4 Notice, Rent Ledger, Lease Agreement, Communication, Unit Photos. | 24,735 B |
| `GEN006_n5_maintenance_brief.pdf` | GEN-006 | N5 case (SOL-55555-26), TOC, two tabs: "Maintenance Issues" (1 JPEG) and "Landlord Communication" (empty). | 26,375 B |
| `GEN007_docx_demand_letter_brief.pdf` | GEN-007 | Title page, TOC, one tab ("Demand Letter"). DOCX demand letter converted and embedded as formatted text. | 80,326 B |
| `GEN008_rent_payment_pdf_brief.pdf` | GEN-008 | Title page, TOC, one tab ("Payment Records"). Rent payment PDF rendered as page images inside the brief. | 72,966 B |
| `GEN009_bad_file_ids_brief.pdf` | GEN-009 | Title page, TOC, one tab ("Bad Refs") with nonexistent file IDs. App handled gracefully — valid PDF, no crash. | 4,439 B |
| `GEN010_gif_door_damage_brief.pdf` | GEN-010 | Title page, TOC, one tab ("Door Damage Photos") with a GIF photo of a scratched front door embedded. | 10,782 B |
| `GEN011_bmp_cracked_tile_brief.pdf` | GEN-011 | Title page, TOC, one tab ("Tile Damage") with a BMP photo of cracked bathroom tiles embedded. | 14,473 B |
| `GEN012_tiff_mold_growth_brief.pdf` | GEN-012 | Title page, TOC, one tab ("Mold Evidence") with a TIFF photo of bedroom wall mold embedded. | 14,436 B |
| `GEN013_markdown_comm_log_brief.pdf` | GEN-013 | Title page, TOC, one tab ("Communication Log") with the Markdown timeline rendered as text in the brief. | 55,780 B |
| `GEN014_heic_carpet_stain_brief.pdf` | GEN-014 | Title page, TOC, one tab ("Carpet Stain") with a HEIC photo (auto-converted to JPEG by the app) embedded. | 15,311 B |
| `GEN015_all_formats_mixed_brief.pdf` | GEN-015 | Title page, TOC, five tabs containing every supported format: Tab 1 has JPEG + PNG + WEBP, Tab 2 has GIF + BMP + TIFF + HEIC, Tab 3 has a PDF rent record, Tab 4 has a Markdown log, Tab 5 has a DOCX demand letter. This is the most comprehensive brief — 10 files across all formats. | 271,199 B |

### Format coverage in generated briefs

Every file format the app supports has at least one brief where it is the primary evidence:

| Format | Brief where it appears | Tab it is in |
|--------|----------------------|--------------|
| JPEG | GEN-002, GEN-003, GEN-006, GEN-015 | Unit Condition Photos, Unit Photos |
| PNG | GEN-004, GEN-005, GEN-015 | N4 Notice, Financial Records, etc. |
| WEBP | GEN-015 | Unit Photos (JPEG + PNG + WEBP) |
| GIF | GEN-010, GEN-015 | Door Damage Photos |
| BMP | GEN-011, GEN-015 | Tile Damage |
| TIFF | GEN-012, GEN-015 | Mold Evidence |
| HEIC | GEN-014, GEN-015 | Carpet Stain |
| PDF | GEN-008, GEN-015 | Payment Records |
| DOCX | GEN-007, GEN-015 | Demand Letter |
| Markdown | GEN-013, GEN-015 | Communication Log |

---

## test_samples/test_logs/ — Test Run Logs

| File | What it contains |
|------|-----------------|
| `test_run_20260307_101132.json` | Machine-readable log: run metadata, summary counts, and one detailed entry per test with timestamps, durations, and status. |
| `test_run_20260307_101132.txt` | Human-readable copy of the console output. |

---

## Latest Test Results

**Run date:** March 7, 2026, 3:11 PM UTC
**Python:** 3.9.10 on macOS (Darwin 25.3.0)
**Duration:** 16.8 seconds (including semantic model tests)
**Result: 49 passed, 0 failed, 0 skipped**

### Console Output

```
=== LTB Tool Test Run 20260307_101132 ===
Python 3.9.10 on Darwin 25.3.0
Started: 2026-03-07T15:11:32.622129Z

--- Category 1: Smoke Tests ---
  [OK  ] SM-001   GET index page (12ms)
  [OK  ] SM-002   GET evidence-stats (1ms)
  [OK  ] SM-003   GET evidence-stats fallback (0ms)
  [OK  ] SM-004   GET thumbnail 404 (0ms)
  [OK  ] SM-005   POST generate no JSON body (0ms)

--- Category 2: Upload Tests ---
  [OK  ] UP-001   Upload PNG — unit hallway photo (46ms)
  [OK  ] UP-002   Upload JPEG — water damage photo (26ms)
  [OK  ] UP-003   Upload WEBP — broken latch photo (48ms)
  [OK  ] UP-004   Upload large PNG (2000x2000 unit photo) (201ms)
  [OK  ] UP-005   Upload PNG RGBA — transparent overlay (18ms)
  [OK  ] UP-006   Multi-file upload (3 room photos) (31ms)
  [OK  ] UP-007   Upload PDF — rent payment record (8ms)
  [OK  ] UP-008   Upload PDF — inspection report with photo (11ms)
  [OK  ] UP-009   Upload DOCX — demand letter (30ms)
  [OK  ] UP-010   Upload Markdown — communication log (1ms)
  [OK  ] UP-011   No files field (1ms)
  [OK  ] UP-012   Corrupted JPEG upload (1ms)
  [OK  ] UP-013   Upload GIF — door damage photo (18ms)
  [OK  ] UP-014   Upload BMP — cracked tile photo (8ms)
  [OK  ] UP-015   Upload TIFF — mold growth photo (9ms)
  [OK  ] UP-016   Upload HEIC — carpet stain photo (104ms)

--- Category 3: PDF Generation Tests ---
  [OK  ] GEN-001  Minimal brief (empty tab) (16ms)
  [OK  ] GEN-002  Single photo N4 brief (75ms)
  [OK  ] GEN-003  Multi-photo tab (3 damage photos) (135ms)
  [OK  ] GEN-004  Three evidence tabs N4 (74ms)
  [OK  ] GEN-005  Five tabs stress (full evidence brief) (288ms)
  [OK  ] GEN-006  N5 application brief (77ms)
  [OK  ] GEN-007  DOCX demand letter in tab (381ms)
  [OK  ] GEN-008  Rent payment PDF in tab (241ms)
  [OK  ] GEN-009  Bad file IDs in tab (15ms)
  [OK  ] GEN-010  GIF image in brief (44ms)
  [OK  ] GEN-011  BMP image in brief (38ms)
  [OK  ] GEN-012  TIFF image in brief (40ms)
  [OK  ] GEN-013  Markdown file in brief (229ms)
  [OK  ] GEN-014  HEIC image in brief (118ms)
  [OK  ] GEN-015  All-formats mixed brief (975ms)

--- Category 4: Evidence Analyzer — Case Splitting ---
  [OK  ] EA-001   No case numbers (0ms)
  [OK  ] EA-002   Single case number (0ms)
  [OK  ] EA-003   Two case numbers (0ms)
  [OK  ] EA-004   Block too small (< 50 chars) (0ms)
  [OK  ] EA-005   Duplicate case IDs (0ms)
  [OK  ] EA-006   AI-generated case ID (0ms)
  [OK  ] EA-007   Normal chunking (0ms)
  [OK  ] EA-008   Empty string chunking (0ms)

--- Category 5: Evidence Analyzer — Aggregation ---
  [OK  ] EA-009   Aggregate empty list (0ms)
  [OK  ] EA-010   Aggregate normal (3 cases) (0ms)
  [OK  ] EA-011   Aggregate uniform (5 identical) (0ms)

--- Category 6: Semantic Tests (slow) ---
  [OK  ] EA-012   Similarity hit (N4 text) (11559ms)
  [OK  ] EA-013   Similarity miss (cooking recipe) (1449ms)

============================================================
TOTAL: 49  |  PASSED: 49  |  FAILED: 0  |  SKIPPED: 0
Duration: 16.8s
============================================================
```

### Detailed Results — Every Test Explained

| ID | Test Name | What Happened | Time | Result |
|----|-----------|--------------|------|--------|
| SM-001 | GET index page | Loaded home page, got 54,209 bytes of HTML. | 12ms | PASS |
| SM-002 | GET evidence-stats | Got JSON response with N4 key. | 1ms | PASS |
| SM-003 | GET evidence-stats fallback | Removed evidence_stats.json, app returned built-in defaults. File restored. | 0ms | PASS |
| SM-004 | GET thumbnail 404 | Asked for nonexistent thumbnail, got 404. | 0ms | PASS |
| SM-005 | POST generate no JSON body | Sent plain text, app rejected with 415. | 0ms | PASS |
| UP-001 | Upload PNG — hallway photo | Uploaded hallway PNG (3,619 B). Recognized as image, thumbnail created. | 46ms | PASS |
| UP-002 | Upload JPEG — water damage | Uploaded kitchen damage JPEG (31,860 B). Image recognized, thumb created. | 26ms | PASS |
| UP-003 | Upload WEBP — broken latch | Uploaded window latch WEBP (664 B). Image recognized, thumb created. | 48ms | PASS |
| UP-004 | Upload large PNG 2000x2000 | Uploaded 19 KB high-res photo. Thumbnail correctly resized to 300x300. | 201ms | PASS |
| UP-005 | Upload PNG RGBA | Uploaded transparent PNG. Still recognized as image. | 18ms | PASS |
| UP-006 | Multi-file upload (3 photos) | Uploaded hallway PNG + bathroom JPEG + bedroom WEBP in one request. All 3 saved. | 31ms | PASS |
| UP-007 | Upload PDF — rent record | Uploaded rent ledger PDF (2,565 B). Classified as document (is_image=False). | 8ms | PASS |
| UP-008 | Upload PDF — inspection report | Uploaded inspection report with photo (8,473 B). Classified as document. | 11ms | PASS |
| UP-009 | Upload DOCX — demand letter | Uploaded demand letter DOCX (37,143 B). Classified as document. | 30ms | PASS |
| UP-010 | Upload Markdown — comm log | Uploaded communication log MD (780 B). Classified as document. | 1ms | PASS |
| UP-011 | No files field | Empty POST with no file. App returned 400 error. | 1ms | PASS |
| UP-012 | Corrupted JPEG | Uploaded 14 bytes of garbage as .jpg. App survived, said is_image=False. | 1ms | PASS |
| UP-013 | Upload GIF — door damage | Uploaded scratched door GIF (4,714 B). Recognized as image, thumb created. | 18ms | PASS |
| UP-014 | Upload BMP — cracked tile | Uploaded cracked tile BMP (360,054 B). Recognized as image, thumb created. | 8ms | PASS |
| UP-015 | Upload TIFF — mold growth | Uploaded mold photo TIFF (360,140 B). Recognized as image, thumb created. | 9ms | PASS |
| UP-016 | Upload HEIC — carpet stain | Uploaded carpet stain HEIC (4,846 B). App auto-converted to JPEG. Image recognized. | 104ms | PASS |
| GEN-001 | Minimal brief (empty tab) | Generated 4,442 B PDF with title page, TOC, empty tab. | 16ms | PASS |
| GEN-002 | Single photo N4 brief | Embedded kitchen JPEG in brief → 25,031 B PDF with download headers. | 75ms | PASS |
| GEN-003 | Multi-photo tab (3 photos) | Embedded 3 damage JPEGs → 59,475 B PDF. | 135ms | PASS |
| GEN-004 | Three evidence tabs | 3 tabs (N4 Notice, Financial, Communication) with PNGs → 11,831 B PDF. | 74ms | PASS |
| GEN-005 | Five tabs stress (10 files) | 5 tabs, 10 PNG images → 24,735 B PDF. | 288ms | PASS |
| GEN-006 | N5 application brief | N5 case SOL-55555-26 with maintenance photo → 26,375 B PDF. | 77ms | PASS |
| GEN-007 | DOCX demand letter in brief | DOCX converted and embedded → 80,326 B PDF. | 381ms | PASS |
| GEN-008 | Rent payment PDF in brief | PDF rent record rendered and embedded → 72,966 B PDF. | 241ms | PASS |
| GEN-009 | Bad file IDs in brief | Nonexistent IDs → 4,439 B valid PDF, no crash. | 15ms | PASS |
| GEN-010 | GIF image in brief | Door damage GIF embedded → 10,782 B PDF. | 44ms | PASS |
| GEN-011 | BMP image in brief | Cracked tile BMP embedded → 14,473 B PDF. | 38ms | PASS |
| GEN-012 | TIFF image in brief | Mold growth TIFF embedded → 14,436 B PDF. | 40ms | PASS |
| GEN-013 | Markdown in brief | Communication log MD rendered as text → 55,780 B PDF. | 229ms | PASS |
| GEN-014 | HEIC image in brief | Carpet stain HEIC (converted to JPEG) embedded → 15,311 B PDF. | 118ms | PASS |
| GEN-015 | All-formats mixed brief | Every format (JPEG+PNG+WEBP+GIF+BMP+TIFF+HEIC+PDF+MD+DOCX) in 5 tabs → 271,199 B PDF. | 975ms | PASS |
| EA-001 | No case numbers | Plain text → 1 block labeled "FULL_DOC." | 0ms | PASS |
| EA-002 | Single case number | Found TSL-12345-22 → 1 case. | 0ms | PASS |
| EA-003 | Two case numbers | Found TSL-12345-22 and SOL-98765-23 → 2 cases. | 0ms | PASS |
| EA-004 | Block too small | Case block under 50 chars → dropped. | 0ms | PASS |
| EA-005 | Duplicate case IDs | Same number twice → kept only first. | 0ms | PASS |
| EA-006 | AI-generated case ID | LTB-L-30001-25 format → recognized. | 0ms | PASS |
| EA-007 | Normal chunking | Paragraph → 1 chunk of 198 chars (under 200 target). | 0ms | PASS |
| EA-008 | Empty string chunking | Empty → empty list. | 0ms | PASS |
| EA-009 | Aggregate empty list | Zero cases → total=0, empty types. | 0ms | PASS |
| EA-010 | Aggregate normal (3 cases) | 3 cases → 67% for N4 Notice, 67% for Lease. | 0ms | PASS |
| EA-011 | Aggregate uniform | 5 identical → 100% for Witness testimony. | 0ms | PASS |
| EA-012 | Similarity hit (N4 text) | AI model detected 8 categories in N4 decision text. | 11,559ms | PASS |
| EA-013 | Similarity miss (recipe) | AI model detected 0 categories in pasta recipe. No false positives. | 1,449ms | PASS |

---

## Plain English Summary by Group

### Group 1: Smoke Tests (5 tests)
Basic "is the app alive?" checks. Can the home page load? Does the stats endpoint work? Does the app fall back to defaults when the stats file is missing? Does it 404 for nonexistent thumbnails? Does it reject garbage input? All passed instantly.

### Group 2: Upload Tests (16 tests)
Every supported file format is tested. The app correctly handled all 7 image formats (PNG, JPEG, WEBP, GIF, BMP, TIFF, HEIC) — each was recognized as an image with a thumbnail created. HEIC was auto-converted to JPEG (took 104ms for the conversion). All 3 document formats (PDF, DOCX, Markdown) were correctly classified as documents. Multi-file upload worked. Empty uploads were rejected. A corrupted JPEG did not crash the server. The high-res 2000x2000 photo got its thumbnail correctly resized to 300x300.

### Group 3: PDF Generation Tests (15 tests)
Every supported format now has its own brief. The app successfully generated briefs with JPEG, PNG, WEBP, GIF, BMP, TIFF, and HEIC images. It converted and embedded DOCX demand letters, rendered PDF rent records, and rendered Markdown communication logs as text. The all-formats mixed brief (GEN-015) combined all 10 supported formats into one 271 KB PDF with 5 tabs — the most comprehensive integration test. Sizes ranged from 4 KB (empty brief) to 271 KB (all-formats brief). The slowest single-format test was GEN-007 (DOCX conversion) at 381ms. The all-formats brief took 975ms.

### Group 4: Case Splitting (8 tests)
The function that splits LTB decisions by file number handled all edge cases correctly: no numbers, one or two numbers, short blocks, duplicates, and AI-generated format.

### Group 5: Aggregation (3 tests)
The percentage calculator correctly computed 67% for 2-out-of-3, 100% for 5-out-of-5, and 0% for empty input.

### Group 6: Semantic Model (2 tests)
The AI model correctly identified 8 evidence categories in N4 decision text and zero categories in a cooking recipe.

---

## How Test Isolation Works

The tests never touch the real `uploads/` folder:

1. A temporary folder is created (like `/tmp/ltb_test_abc123/`).
2. The app's upload folder setting is redirected to that temp folder.
3. All uploads and generated PDFs go into the temp folder.
4. After tests finish, the temp folder is deleted.

You can run the tests while the app is serving real users with no interference.

---

## Reading the JSON Log

| Field | Meaning |
|---|---|
| `id` | Test identifier (e.g., UP-001, GEN-015) |
| `category` | Group: smoke, upload, generation, evidence-split, evidence-agg, evidence-semantic |
| `name` | Short human-readable name |
| `description` | What the test does and checks |
| `action` | The exact HTTP request or function call |
| `started` / `finished` | UTC timestamps |
| `duration_ms` | Time in milliseconds |
| `status` | PASS, FAIL, or SKIP |
| `detail` | File IDs, PDF sizes, AI model detections |
| `files_generated` | Files created with names and sizes in bytes |
