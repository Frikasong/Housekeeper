# LTB Evidence Brief Generator — Development Report

> **Project:** LTB Evidence Brief Generator
> **Date:** March 2, 2026
> **Group Members:** Fukun Yang, Angel Xing 

A detailed explanation of every module, why each design choice was made, and a version history of all changes.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [How the Backend Works (app.py)](#how-the-backend-works)
3. [How the Frontend Works (index.html)](#how-the-frontend-works)
4. [How the Jupyter Notebook Works](#how-the-jupyter-notebook-works)
5. [How Everything Connects](#how-everything-connects)
6. [Version History](#version-history)

---

## What This Project Does

This is a web app that helps tenants (or their paralegals/lawyers) prepare professional evidence briefs for Ontario Landlord and Tenant Board hearings. You upload your evidence files — photos, PDFs, Word documents, spreadsheets, even iPhone HEIC images — organize them into numbered tabs, and the app generates a court-ready PDF with a title page, table of contents, tab dividers, and properly numbered pages.

The app runs two ways:
- **Locally** via `python3 app.py` on port 5050
- **In Google Colab** via the Jupyter notebook (great for users without Python installed)

---

## How the Backend Works

### File: `app.py` (~920 lines)

### Module 1: Smart Dependency Loading (Lines 1–67)

**What it does:** Imports everything the app needs, but wraps optional libraries in `try/except` blocks so the app still runs even if some aren't installed.

**Why this approach:** Not every user will have LibreOffice, PyMuPDF, or pillow-heif installed. Rather than crashing, the app gracefully degrades — it just can't do that specific conversion. For example, if `pdfplumber` isn't installed, PDF text extraction returns "not available" instead of throwing an error.

**Key constants:**
- `IMAGE_EXTS` — file extensions we treat as images (png, jpg, etc.)
- `OFFICE_EXTS` — file extensions that need LibreOffice conversion (docx, xlsx, pptx, etc.)
- `HEIC_EXTS` — iPhone photo formats (heic, heif)
- `PLAIN_TEXT_EXTS` — anything we can read as plain text (txt, csv, json, py, etc.)

---

### Module 2: Text Extraction (Lines 69–118)

**What it does:** Reads the text content out of uploaded files so we can display it in the PDF if we can't render the file as an image.

**How it works:**
- **Plain text files** → read directly with UTF-8
- **PDFs** → pdfplumber extracts text from each page
- **Word docs** → python-docx reads all paragraphs
- **Excel files** → openpyxl reads all sheets, tab-separates cell values

**Why this exists:** If someone uploads a DOCX but LibreOffice isn't installed and PyMuPDF can't render it, we still want to show _something_ in the PDF. This is the last-resort fallback — we extract the raw text and display it as paragraphs.

---

### Module 3: Document-to-PDF Conversion Pipeline (Lines 120–390)

This is the most complex module. It handles converting _any_ non-image file into something we can embed in the final PDF.

#### 3a. LibreOffice Conversion
- Searches for LibreOffice on the system (checks standard macOS and Linux paths)
- Runs it in headless mode to convert DOCX/XLSX/PPTX to PDF
- Caches the search result so we only look once

#### 3b. HEIC to JPEG Conversion
- iPhone photos use HEIC format, which most libraries can't read
- First tries `pillow-heif` (Python library)
- Falls back to `sips` (macOS built-in command)
- Converts to JPEG at quality 95 so we don't lose detail

**Why two approaches:** pillow-heif works on Linux (Colab), sips works on macOS. Between them, we cover both deployment environments.

#### 3c. Text-to-PDF Conversion
- For `.txt`, `.csv`, `.py`, etc. — renders as monospace text in a PDF
- Uses ReportLab with Courier font, 8pt, line-by-line
- This intermediate PDF then gets rendered to images by PyMuPDF

#### 3d. DOCX-to-PDF via ReportLab (the deep parser)
- When LibreOffice isn't available, this function walks the raw XML inside a .docx file
- Extracts paragraphs with heading styles (maps to H1/H2)
- Finds embedded images by looking for `<a:blip>` elements in the DrawingML namespace
- Extracts image blobs, normalizes color modes (RGBA/palette to RGB), scales to fit
- Preserves document order (text and images interleaved correctly)

**Why so complex:** Word documents are actually ZIP files containing XML. We need to walk the XML tree to find both text paragraphs and embedded images in the correct order. This is the only way to get images out of a DOCX without LibreOffice.

#### 3e. Master Pipeline (`convert_document_to_images`)
Orchestrates everything with a fallback cascade:
1. Try LibreOffice (best quality — handles all office formats)
2. Try text-to-PDF (for plain text files)
3. Try DOCX ReportLab parser (for Word docs when LO is missing)
4. Give up and return empty list

Then renders the resulting PDF to JPEG images at 150 DPI using PyMuPDF. Each page becomes one image that gets embedded in the final brief.

---

### Module 4: Two-Pass PDF Rendering (Lines 392–421)

**What it does:** The `NumberedCanvas` class handles page numbering, but with a twist — it needs two rendering passes.

**Why two passes:** The Table of Contents needs to show "Tab 1 starts on page 5" — but we don't know page 5 until we've laid out the entire document. So:
- **Pass 1:** Render everything to a throwaway BytesIO buffer. As each `TabDivider` draws itself, it records its page number in a shared dictionary.
- **Pass 2:** Render again to the real output file, this time the TOC has the correct page numbers from Pass 1.

**How `NumberedCanvas` works:**
- Overrides `showPage()` to save page state instead of rendering immediately
- On `save()`, replays all pages, drawing the footer (page number + "Evidence Brief" + separator line) on each one
- Page numbers are Times-Bold 14pt, "Evidence Brief" is Times-Roman 11pt

---

### Module 5: Tab Divider Pages (Lines 423–469)

**What it does:** Creates the full-page separator between evidence sections. Each tab gets a clean white page with "TAB N" and the tab title centered between decorative rules.

**Design choice:** We originally had navy blue full-page dividers with gold text, but the user wanted minimal, professional pages matching the LTB template style. Now it's:
- White background
- Two thin horizontal rules framing the text
- "TAB N" in Times-Bold 28pt
- Tab title in Times-Roman 18pt

The `TabDivider` is a custom ReportLab `Flowable` — it draws directly on the canvas, which gives us precise positioning control.

---

### Module 6: Image Compression (Lines 469–497)

**What it does:** Optimizes every image before embedding it in the PDF to keep file sizes under control.

**How:** Takes any image, calculates what pixel dimensions it needs at 150 DPI for its display size, downscales (never upscales), converts to RGB JPEG at quality 72, and returns a centered ReportLab image object.

**Why 150 DPI / quality 72:** This is the sweet spot — images look sharp on screen and in print, but a 20-photo brief stays well under 35MB. Higher DPI or quality would balloon file sizes without visible improvement at typical viewing distances.

---

### Module 7: Story Builder (Lines 499–748)

This is the heart of the PDF generation — a ~250-line function that assembles every page of the evidence brief.

#### Title Page
Matches the official LTB "Tenant Evidence Brief Title Page" template:
- File number top-right
- "LANDLORD AND TENANT BOARD / TRIBUNALS ONTARIO" centered
- Horizontal rule
- "In the matter of: [rental unit address]"
- "Between:" section with applicant and respondent in a two-column table
- "TENANT'S EVIDENCE BRIEF" between horizontal rules
- All in Times New Roman (matching the court's typography)

#### Table of Contents
- Three-column table: Tab number, Description, Page number
- Page numbers come from the two-pass rendering system
- Shows "—" on Pass 1 (numbers unknown), real numbers on Pass 2

#### Tab Sections
For each tab:
1. Full-page tab divider
2. **Images: one per page** — each photo gets the full page width, with a caption below ("Tab N - Title | Photo M")
3. **Documents:** If we could convert them to page images, embed those. Otherwise, show the extracted text as paragraphs.

---

### Module 8: Flask Routes (Lines 797–923)

Five routes, each with a simple job:

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serves the frontend HTML |
| `/upload` | POST | Receives files, saves with UUID names, generates thumbnails, converts HEIC |
| `/thumbnail/<name>` | GET | Serves 300x300 thumbnail images |
| `/evidence-stats` | GET | Returns evidence type statistics (from file or defaults) |
| `/generate` | POST | Receives case info + tab structure, generates and streams PDF |

**Why UUID filenames:** Prevents filename collisions and path traversal attacks. The original filename is stored in the JSON response for display purposes.

**Why stream the PDF:** The generated PDF lives in a temp file. We stream it directly to the browser as a download rather than storing it permanently — keeps the server clean.

---

## How the Frontend Works

### File: `templates/index.html` (~1520 lines)

### Layout: 4-Step Wizard

The app is a single-page wizard with 4 steps. Only one panel is visible at a time (CSS `.panel.active`). The step bar at the top shows progress with numbered circles and checkmarks.

### Step 1: Case Information (Panel 0)
- **Alex the Mouse** — SVG mascot with speech bubble giving instructions
- Form fields: file number, hearing date, applicant/respondent names, addresses
- **Case Type dropdown** — N4 (shows evidence stats) or N5 (Alex says "coming soon")
- Evidence stats panel with percentage bars (fetched from `/evidence-stats`)

### Step 2: Upload Files (Panel 1)
- Alex gives upload instructions
- Drag-and-drop zone (also click-to-browse)
- Upload progress bar
- Grid of uploaded files (thumbnails for images, file-type badges for documents)
- Delete button on hover

### Step 3: Arrange Tabs (Panel 2)
- Alex explains drag-and-drop
- Two-column layout:
  - **Left sidebar:** List of tabs (add, delete, select)
  - **Right detail:** Selected tab's title input + drop zone + assigned files
- **Bottom pool:** Unassigned files ready to be dragged into tabs
- Click a file in the pool to add to selected tab. Click X in tab to remove.

### Step 4: Review & Generate (Panel 3)
- Alex says "Almost there!"
- Summary of all case info fields
- List of tabs with file counts
- Big gold "Generate PDF" button
- Loading spinner during generation
- Success/error status messages

### Alex the Mouse (Mascot System)

Alex is an inline SVG character (~72x72px) rendered with basic shapes:
- Big round head (chibi proportions), round pink-inner ears
- Soft grey eye mask patches, large shiny eyes with highlight dots
- Chubby round body with light belly, stubby paws
- Fluffy striped tail curling behind
- Rosy blush cheeks, cute "w" shaped mouth

He appears on every panel with a speech bubble containing contextual instructions. On Step 1, his message changes dynamically:
- Default: "Hi, I'm Alex the Mouse!" greeting
- N4 selected: evidence guidance message + stats panel
- N5 selected: "We're still working on N5 stats — stay tuned!"

**Why a mascot:** Makes a legal tool feel friendlier and less intimidating. The speech bubble replaces plain info-box text with personality.

**Why inline SVG:** No external file to load, resolution-independent, instant rendering, and we can use smooth curves and gradients for a hand-drawn look.

### JavaScript Architecture

All state lives in 4 global variables:
- `uploadedImages[]` — all uploaded files with metadata
- `tabs[]` — tab definitions with ordered file ID lists
- `selectedTabId` — which tab is currently being edited
- `currentStep` — which panel is visible (0-3)

**Key design:** The server is stateless — all organization (which files go in which tabs, tab order, tab names) is managed client-side. The `/generate` endpoint receives the complete structure as JSON.

The drag-and-drop system uses native HTML5 drag events with `dataTransfer` to pass file IDs between the pool and tab drop zones.

---

## How the Jupyter Notebook Works

### File: `LTB_Evidence_Brief_Generator.ipynb` (11 cells)

The notebook is designed for Google Colab — it installs dependencies, optionally runs the evidence extraction pipeline, writes the app files to disk, and starts the server.

| Cell | Type | Purpose |
|------|------|---------|
| 0 | Markdown | Title and usage instructions |
| 1 | Code | `pip install` all dependencies + install LibreOffice via `apt-get` |
| 2 | Code | Create `/content/templates/` and `/content/uploads/` directories |
| 3 | Markdown | "Evidence Extraction Pipeline (Optional)" — keyword analysis, no APIs |
| 4 | Code | Upload PDF of LTB decisions + extract text with pdfplumber. **Skips if `evidence_stats.json` exists.** |
| 5 | Code | Keyword-based evidence analysis — regex pattern matching against 10 evidence categories. **Fully local, no network calls.** |
| 6 | Code | Aggregates results, computes percentages, writes `evidence_stats.json` |
| 7 | Code | `%%writefile` — writes `index.html` to `/content/templates/` |
| 8 | Code | Inline app code (same as `app.py` but with Colab paths) |
| 9 | Code | Starts Flask server in background thread, prints access URL |

### Evidence Extraction Pipeline (Cells 4-6)

This analyzes real LTB decisions to figure out what types of evidence are most commonly submitted in N4 cases. **All processing is local — no AI, no API calls, no data leaves your machine.**

**How it works:**
1. User uploads a PDF that concatenates many LTB N4 decisions
2. pdfplumber extracts all text locally
3. Python splits text into individual cases by detecting LTB file number patterns (e.g. TSL-12345-22, SOL-98765-23)
4. For each case block, regex patterns scan for 10 evidence categories (N4 notice, financial records, lease, payment history, communications, legal docs, witness testimony, government records, photos, maintenance records)
5. Results are aggregated: for each evidence category, we count what percentage of cases included it
6. Final stats are saved as `evidence_stats.json`

**Why keyword/regex instead of AI:** Data privacy. LTB decisions contain sensitive personal information — sending them to external APIs is a privacy risk. Regex-based classification runs entirely on the local machine and produces the same output format.

**Why skip if file exists:** Once you've generated the stats, there's no reason to redo it. The cells check for `evidence_stats.json` before doing anything — no upload prompt, no processing. Delete the file to re-run.

### Server Startup (Cell 10)

**The port conflict fix:** When you re-run cells in Colab, the previous Flask server might still be running on port 5050. Cell 10 now:
1. Checks if port 5050 is already in use (via `socket.connect_ex`)
2. If so, kills the process with `fuser -k 5050/tcp`
3. Waits 1 second for cleanup
4. Starts Flask in a daemon thread (so it dies when the notebook closes)
5. Detects Colab environment and prints the proxy URL

---

## How Everything Connects

```
                        USER'S BROWSER
  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐
  │ Step 1   │→ │ Step 2   │→ │ Step 3 │→ │ Step 4   │
  │ Case Info│  │ Upload   │  │ Tabs   │  │ Generate │
  └────┬─────┘  └────┬─────┘  └────────┘  └────┬─────┘
       │              │                         │
  GET /evidence  POST /upload            POST /generate
  -stats              │                         │
       │              v                         v
  ─────┴────────────────────────────────────────────────
                  FLASK SERVER (app.py)

   evidence_stats.json <── Notebook extraction pipeline

   /uploads/ <── saved files (UUID names + thumbnails)

   ReportLab <── builds PDF:
     |-- Title Page (Times New Roman, LTB template)
     |-- Table of Contents (two-pass page numbers)
     |-- Tab Dividers (TAB N, 28pt)
     |-- Photos (one per page, 150 DPI, JPEG q72)
     |-- Documents (converted to images or text fallback)

   --> Streams PDF back to browser as download
  ─────────────────────────────────────────────────────
```

---

## Version History

### v1.0 — Initial Build
- Flask backend with ReportLab PDF generation
- 4-step wizard frontend (Case Info, Upload, Arrange Tabs, Review & Generate)
- Image upload with thumbnails, drag-and-drop tab organization
- PDF output: title page, table of contents, tab dividers (navy blue full-page), photos (2 per page)
- Two-pass rendering for accurate TOC page numbers
- `NumberedCanvas` for page footers

### v1.1 — HEIC + Word Document Support
- Added `pillow-heif` integration with macOS `sips` fallback for HEIC/HEIF photos
- Added `_convert_docx_to_pdf_reportlab()` — deep XML parser that walks DOCX body, extracts embedded images via DrawingML `<a:blip>` elements, preserves document order
- Modified upload route to auto-convert HEIC to JPEG before thumbnail generation
- Added `_convert_heic_to_jpeg()` with dual-path conversion (Python library or macOS CLI)

### v1.2 — PDF Size Optimization
- Added `_rl_image_compressed()` helper — downscales images to 150 DPI at display size, JPEG quality 72
- Reduced `convert_document_to_images` render DPI from 200 to 150, output format from PNG to JPEG
- All image embeddings now go through the compression helper
- Target: keep final PDF under 35MB

### v1.3 — LTB Template Matching
- Rewrote title page to match the official "Tenant Evidence Brief Title Page" PDF template
  - Times New Roman throughout (was Helvetica)
  - "LANDLORD AND TENANT BOARD / TRIBUNALS ONTARIO" centered
  - "Between:" section with party names centered + roles right-aligned
  - "TENANT'S EVIDENCE BRIEF" between horizontal rules
- Replaced navy blue tab dividers with minimal white pages (thin rules + centered text)
- Changed all PDF styles from Helvetica to Times-Roman/Times-Bold/Times-Italic
- Simplified TOC styling to match

### v1.4 — Evidence Stats Feature
- Added `DEFAULT_EVIDENCE_STATS` dictionary with N4 case data (hardcoded defaults)
- Added `GET /evidence-stats` route (loads from JSON file or falls back to defaults)
- Added Case Type dropdown (N4) to Step 1 with `onCaseTypeChange()` JavaScript
- Added evidence stats panel with percentage bars and category labels
- Added 5 new notebook cells (3-7): extraction pipeline header, API key setup, PDF upload, batch LLM processing via OpenRouter/DeepSeek, result aggregation + JSON export
- Extraction pipeline skips processing if `evidence_stats.json` already exists

### v1.5 — Alex the Mouse Mascot
- Added Alex the Mouse — an inline SVG character appearing on all 4 panels
  - Chibi/kawaii style: big round head, large sparkly eyes, pink inner ears, chubby body, fluffy striped tail, rosy cheeks
  - Speech bubble with contextual instructions per step
- Replaced all `.info-box` elements with mascot + speech bubble components
- Added CSS for `.mascot-container`, `.raccoon-svg`, `.speech-bubble` with appear animation
- Dynamic mascot behavior on Step 1:
  - Default: "Hi, I'm Alex the Mouse!" greeting
  - N4 selected: evidence guidance message + stats panel
  - N5 selected: "We're still working on N5 stats — stay tuned!"
- Added N5 option to Case Type dropdown

### v1.6 — PDF Layout & Notebook Fixes
- **One photo per page** — changed from 2-per-page layout to full-page images (more space, better readability)
- **Bigger page numbers** — "Page N" now Times-Bold 14pt (was Helvetica 8pt)
- **Bigger tab numbers** — "TAB N" now Times-Bold 28pt (was 14pt), tab title 18pt (was 12pt)
- **Notebook extraction skip** — Cell 5 now checks for `evidence_stats.json` before even prompting for PDF upload (no upload dialog, no API calls if stats already exist)
- **Notebook port conflict fix** — Cell 10 now kills any existing process on port 5050 before starting Flask
- **Cell 9 fix** — Removed `if __name__ == '__main__': app.run()` block that was conflicting with Cell 10's threaded server startup

### v1.7 — Privacy-First Evidence Analysis (Remove Cloud AI)
- **Removed all cloud AI/API usage** from the evidence extraction pipeline for data privacy
  - Deleted the API key input cell (getpass/OpenRouter)
  - Removed `requests` from pip install
  - No data leaves the machine — all processing is 100% local

### v1.8 — Local Semantic Analysis (sentence-transformers)
- **Replaced regex keyword matching** with local semantic understanding using `sentence-transformers`
- **New `evidence_analyzer.py` module** — standalone script that can be used from CLI or imported:
  - Uses `all-MiniLM-L6-v2` model (~80MB, runs on CPU, downloads once)
  - Each evidence category has 6-9 reference phrases describing what that evidence looks like in LTB decisions
  - Splits PDF text into individual cases by LTB file number patterns
  - Splits each case into sentence-level chunks (~200 chars)
  - Batch-encodes chunks using the transformer model
  - Computes cosine similarity between chunk embeddings and category reference embeddings
  - If any chunk in a case exceeds 0.35 similarity threshold for a category, that evidence type is counted
  - Produces identical `evidence_stats.json` output format
- **Notebook updated** (10 cells):
  - Cell 1: added `sentence-transformers` to pip install
  - Cell 5: `%%writefile /content/evidence_analyzer.py` — writes the analyzer module to disk
  - Cell 6: imports and runs `analyze_cases()` + `aggregate_stats()`, writes JSON
- **CLI support**: `python evidence_analyzer.py decisions.pdf [output.json]`
- **Why sentence-transformers over regex**: Regex only catches exact keyword matches. Semantic embeddings understand meaning — e.g. "the tenant provided proof of e-transfers" matches "Payment history" even without exact keyword overlap

### v1.9 — Comprehensive Test Suite

Added a full automated test suite (`test_ltb_tool.py`, ~1300 lines) with **49 tests across 6 categories**, structured test logging, realistic fake evidence file generators, and a saved artifacts folder for inspection.

#### New Files

| File / Folder | Purpose |
|---------------|---------|
| `test_ltb_tool.py` | Standalone test runner — run with `python3 test_ltb_tool.py` (fast) or `--include-slow` (includes semantic model tests) |
| `TEST_EXPLANATION.md` | Plain English explanation of every test, every file, and every result |
| `test_samples/uploaded_files/` | 52 saved test input files (AI-generated fake evidence) |
| `test_samples/generated_briefs/` | 15 saved PDF briefs produced by the tool during testing |
| `test_samples/test_logs/` | Archived JSON + TXT test run logs |
| `test_logs/` | Auto-created each run with timestamped JSON + TXT logs |

#### Test Architecture

- **TestLogger** — captures every test result to console + `.txt` + `.json` with timestamps, durations, file sizes
- **LTBTestFixture** — sets up Flask `test_client()` with an isolated `tempfile.mkdtemp()` upload directory; no real HTTP server needed; cleaned up after each run
- **TestRunner** — runs all tests in sequence, catches failures without aborting
- **File generators** — create realistic fake evidence files in memory (not simple color patches):
  - `make_png()` — hallway scene with door, window, floor damage, labels
  - `make_jpeg()` — kitchen with cabinets, countertop, water stain on ceiling
  - `make_webp()` — window frame with broken latch marked by red X
  - `make_gif()` — front door with visible scratch damage
  - `make_bmp()` — bathroom tiles with jagged crack line
  - `make_tiff()` — bedroom wall with mold patches
  - `make_heic()` — carpet with dark stain (requires `pillow-heif`)
  - `make_pdf_text()` — rent payment record table showing $4,650 arrears
  - `make_pdf_with_image()` — maintenance inspection report with embedded photo
  - `make_docx()` — formal demand letter citing the Residential Tenancies Act
  - `make_md()` — tenant communication log timeline (Markdown)

#### All 49 Test Cases

**Category 1: Smoke Tests (5 tests, SM-001 to SM-005)**
- GET index page returns 200 with expected HTML
- GET evidence-stats returns valid JSON
- Evidence-stats fallback when file is missing
- Thumbnail 404 for nonexistent file
- POST generate without JSON body returns error

**Category 2: Upload Tests (16 tests, UP-001 to UP-016)**
- Core image formats: PNG, JPEG, WEBP — verify `is_image=True`, thumbnail created
- Large image (2000×2000) — thumbnail constrained to ≤300px
- RGBA PNG — alpha channel handled
- Multi-file upload (3 PNGs in one POST)
- Document formats: PDF (text), PDF (with image), DOCX, Markdown — verify `is_image=False`
- Edge cases: no files field (400), corrupted JPEG (graceful handling)
- Extended image formats: GIF, BMP, TIFF, HEIC — all supported by the upload pipeline

**Category 3: PDF Generation Tests (15 tests, GEN-001 to GEN-015)**
- Minimal brief, single image, multi-image tab, three tabs, five tabs (stress)
- N5 application type
- DOCX in tab, PDF in tab, bad file IDs (graceful fallback)
- Individual format briefs: GIF-only, BMP-only, TIFF-only, Markdown-only, HEIC-only
- **All-formats mixed brief (GEN-015)** — 5 tabs combining all 10 supported formats: JPEG, PNG, WEBP, GIF, BMP, TIFF, HEIC, PDF, Markdown, DOCX

**Category 4: Evidence Analyzer — Case Splitting (8 tests, EA-001 to EA-008)**
- No case numbers → single `FULL_DOC` block
- Single and double case number detection
- Block too small → dropped
- Duplicate file numbers → only first kept
- AI-generated LTB file number format matched
- Text chunking (≤200 chars) and empty string edge case

**Category 5: Evidence Analyzer — Aggregation (3 tests, EA-009 to EA-011)**
- Empty input, normal 3-case input, uniform 5-case input

**Category 6: Evidence Analyzer — Semantic (2 slow tests, EA-012 to EA-013)**
- N4 decision text → "N4 Notice" category detected via embeddings
- Unrelated text (cooking recipe) → no categories matched

#### Format Coverage

Every supported file format is tested at three levels:

| Format | Upload Test | Own Brief Test | In Mixed Brief (GEN-015) |
|--------|------------|----------------|--------------------------|
| PNG | UP-001 | GEN-002 | Tab 1 |
| JPEG | UP-002 | GEN-002 | Tab 1 |
| WEBP | UP-003 | GEN-003 | Tab 1 |
| GIF | UP-013 | GEN-010 | Tab 2 |
| BMP | UP-014 | GEN-011 | Tab 2 |
| TIFF | UP-015 | GEN-012 | Tab 3 |
| HEIC | UP-016 | GEN-014 | Tab 3 |
| PDF | UP-007 | GEN-008 | Tab 4 |
| DOCX | UP-009 | GEN-007 | Tab 5 |
| Markdown | UP-010 | GEN-013 | Tab 4 |

#### Test Results

All 49 tests pass (47 fast + 2 slow with `--include-slow`). Run time: ~25 seconds (fast), ~2 minutes (with slow semantic tests).

#### Saved Artifacts

- **52 uploaded test files** in `test_samples/uploaded_files/` — prefixed with test IDs (e.g., `UP001_hallway_damage.png`, `GEN015a_kitchen_leak.jpeg`)
- **15 generated briefs** in `test_samples/generated_briefs/` — one per generation test (e.g., `GEN001_minimal_brief.pdf`, `GEN015_all_formats_mixed_brief.pdf`)
- **Test run logs** in `test_samples/test_logs/` — JSON (structured, machine-readable) + TXT (human-readable console output)

#### How to Run

```bash
# From the ltb_tool directory:
python3 test_ltb_tool.py              # Fast tests (~25 seconds)
python3 test_ltb_tool.py --include-slow  # All tests including semantic model (~2 minutes)
```

Output goes to `test_logs/test_run_YYYYMMDD_HHMMSS.json` and `.txt`.
