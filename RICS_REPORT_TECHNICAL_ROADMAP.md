# RICS Report Rebuild — Technical Roadmap

> **Author**: Lead Engineering Consultant
> **Date**: 2026-03-26
> **Reference**: [Master Document](file:///Users/SalimBAssil/Documents/AntiGravity_Core_Vault_v2026/04_Source_Code/RISC_V2_Core_System/RICS_REPORT_REBUILD_MASTER.md)

---

## System Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUTTER WITNESS APP                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Room     │  │ Final    │  │ TipTap   │  │ PDF Native │ │
│  │ Reports  │  │ Report   │  │ WebView  │  │ Viewer     │ │
│  │ Tab      │  │ Tab      │  │ (Editor) │  │ (OpenFilex)│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘ │
│       │              │             │               │        │
└───────┼──────────────┼─────────────┼───────────────┼────────┘
        │              │             │               │
   ┌────▼──────────────▼─────────────▼───────────────▼────────┐
   │                  FASTAPI BACKEND (Brain)                  │
   │                                                           │
   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
   │  │ Report       │  │ Version      │  │ TipTap Web     │ │
   │  │ Generator    │  │ Manager      │  │ App Server     │ │
   │  │              │  │              │  │                │ │
   │  │ room_element │  │ report_      │  │ /editor/{pid}  │ │
   │  │ _mapper.py   │  │ versioning.py│  │                │ │
   │  │              │  │              │  │ AI: Gemini 3   │ │
   │  │ md_report_   │  │ MD + PDF per │  │ Custom LLM     │ │
   │  │ builder.py   │  │ version      │  │ resolver       │ │
   │  └──────┬───────┘  └──────────────┘  └────────────────┘ │
   │         │                                                 │
   │  ┌──────▼───────┐  ┌──────────────┐  ┌────────────────┐ │
   │  │ Playwright   │  │ Gemini 3     │  │ PostgreSQL     │ │
   │  │ PDF Engine   │  │ Flash        │  │ Database       │ │
   │  │ (Chromium)   │  │ Preview      │  │                │ │
   │  │              │  │              │  │ Projects,      │ │
   │  │ HTML+CSS →   │  │ Narratives,  │  │ Rooms,         │ │
   │  │ 250pg PDF    │  │ Voice Edit,  │  │ Versions,      │ │
   │  │ with images  │  │ AI Editor    │  │ Approvals      │ │
   │  └──────────────┘  └──────────────┘  └────────────────┘ │
   └───────────────────────────────────────────────────────────┘
```

## Data Flow: Inspection → Final Report

```
1. FIELD INSPECTION
   └─ Surveyor captures: photos, voice notes, measurements per room

2. ROOM REPORT GENERATION
   └─ For each room:
      ├─ Select photos (surveyor chooses)
      ├─ Generate report (Gemini + template)
      ├─ Review → Edit (Voice/TipTap) → Regenerate → v(N+1)
      └─ Approve ✅ → locked

3. FINAL REPORT GENERATION
   └─ Aggregation:
      ├─ Only approved rooms
      ├─ room_element_mapper: rooms → RICS elements (D1-G5)
      ├─ Gemini 3: professional narratives per element
      ├─ Jinja2: rics_skeleton.md.j2 template
      ├─ Playwright: HTML+CSS → PDF (250+ pages with photos)
      ├─ Version saved: v(N).md + v(N).pdf
      └─ Review → Edit → Regenerate → Approve ✅

4. DELIVERY
   └─ VIEW PDF → OpenFilex native viewer
   └─ DOWNLOAD → timestamped copy to device
   └─ SHARE → system share sheet
```

## Key Technology Decisions

| Component | Old | New | Why |
|---|---|---|---|
| PDF Engine | PyMuPDF Story API | **Playwright/Chromium** | 250+ pages, full CSS, images |
| Web Editor | None (404) | **TipTap + Gemini 3** | AI-powered WYSIWYG |
| Version Storage | MD only | **MD + PDF per version** | Complete audit trail |
| Photo Pipeline | Empty paths | **Absolute Docker paths** | Photos actually appear |
| Template | T.pdf stamping | **HTML/CSS generation** | Dynamic 250+ pages |

## File Map (What Changes Where)

### Backend — `/02_Brain_Cluster/`
```
services/
  ├── md_report_builder.py      [MODIFY] Use Playwright, filter approved rooms
  ├── room_element_mapper.py    [MODIFY] Wire photo paths to EvidencePhoto
  ├── report_versioning.py      [MODIFY] Save PDF per version, active_version_id
  ├── playwright_pdf_generator.py [NEW] Chromium-based PDF renderer
  ├── pdf_generator.py          [RETIRE] PyMuPDF subprocess approach
  └── rics_stamper.py           [RETIRE] T.pdf template stamping

routers/
  └── projects.py               [MODIFY] Version endpoints, editor endpoints

templates/
  ├── rics_style.css            [MODIFY] Photo grids, cover page, print CSS
  └── rics_skeleton.md.j2       [MODIFY] Photo rendering improvements

web_editor/                     [NEW] TipTap web application
  ├── index.html
  ├── editor.js                 [TipTap + Gemini AI integration]
  └── editor.css
```

### Flutter — `/01_Witness_Cluster/`
```
lib/screens/
  ├── final_report_tab.dart     [MODIFY] Version management, PDF methods
  └── report_webview_screen.dart [MODIFY] Load TipTap editor

pubspec.yaml                    [MODIFY] open_filex, dio
```

## Quality Gates

Each phase must pass before proceeding:
- **Phase 1**: Playwright generates PDF with images inside Docker ✅
- **Phase 2**: HTML report shows `<img>` tags with valid photo paths ✅
- **Phase 3**: PDF matches RICS template visually ✅
- **Phase 4**: Each regeneration creates version with MD + PDF ✅
- **Phase 5**: Voice edit → new version with correct changes ✅
- **Phase 6**: TipTap editor loads in WebView with AI features ✅
- **Phase 7**: Approved rooms → final report, unapproved blocked ✅
- **Phase 8**: 15/15 test checklist passes ✅
