# RICS Report Rebuild — Master Project Document
> **Created**: 2026-03-26 | **Status**: ACTIVE | **Timeline**: 1 Work Week

---

## 🎯 Objective

Rebuild the RICS Level 3 report generation pipeline from ground up. Transform 22-page text-only PDF → professional 250+ page report with embedded photos, RICS-compliant formatting, intelligent version management, and AI-powered WYSIWYG editing.

---

## Production Pipeline

```
Field Inspection → Photos + Voice Notes per room
    ↓
Room Report (Partial) — per room independently
    ↓  ← Surveyor selects photos → Generate → Review → Edit (Voice/Web) → Approve
    ↓
Final RICS Report — built EXCLUSIVELY from approved room reports
    ↓  ← Same review loop: Generate → Review → Edit → v2 → Review → Approve
    ↓
Final PDF ready for client delivery (up to 250 pages)
```

## Review Loop (applies to Room Reports AND Final Report)

```
Select photos → Generate (v1) → Surveyor reviews
                                    ↙        ↘
                                Approve ✅    Edit (Voice/Web/AI)
                                                ↓
                                        Generate (v2) ← new default
                                                ↓
                                        Review → Approve ✅
```

## Current State — What Works vs What's Broken

| Component | Status | Detail |
|---|---|---|
| Field inspection + room data | ✅ | Good engineering data |
| Room report — generation | ✅ | Data works, no embedded photos |
| Room report — versioning | ❌ | No version system |
| Room report — voice edit | ❌ | Not functional |
| Final report — generation | ⚠️ | 22 pages text only, no photos, weak formatting |
| Final report — photos | ❌ | 31 photos on disk, mapper doesn't wire paths |
| Final report — versioning | ❌ | Saves MD only, no per-version PDF |
| Final report — voice edit | ❌ | Not functional |
| Web editor | ❌ | `/report/editor` → 404 |
| VIEW/DOWNLOAD/SHARE | ⚠️ | Downloads PDF but no photos in it |

## Architecture Decisions

1. **Photos**: Only surveyor-selected photos from approved room reports
2. **Template T.pdf**: Retired — generate from scratch with RICS design compliance
3. **Editor**: AI-powered WYSIWYG exceeding Microsoft Word (TipTap/Plate + Gemini 3)
4. **Default version**: Always the latest generated after edits
5. **PDF engine**: Must support 250+ pages with photos (research Phase 1)

## Technical Equation

```
Approved Room Reports (selected photos + narratives + ratings)
  + room_element_mapper (rooms → RICS elements D1-G5)
  + Gemini 3 (professional narratives per element)
  + Jinja2 template (rics_skeleton.md.j2)
  + Powerful PDF engine (supports 250 pages + images)
  = Complete RICS Level 3 Report
```

## 8-Phase Plan Reference

See: [implementation_plan.md](file:///Users/SalimBAssil/.gemini/antigravity/brain/5a74c755-1f23-489d-b791-c29eebf9ac0a/implementation_plan.md)
