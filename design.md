# IP-SAKTI Sahayak — UI/UX Design System Specification

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Design Aesthetics & Visual Identity

The design language of **IP-SAKTI Sahayak** bridges ancient Ayurvedic heritage with futuristic, high-trust legal-tech intelligence. It combines deep emerald herb tones, warm turmeric gold accents, dark obsidian slate backgrounds, and translucent glassmorphism surfaces.

```
+-----------------------------------------------------------------------------------------------+
|                                    COLOR PALETTE SYSTEM                                       |
+----------------------+-----------------------+------------------------------------------------+
| Token Name           | Hex Code              | Role & Semantic Application                    |
+----------------------+-----------------------+------------------------------------------------+
| `--ayur-primary`     | `#059669` (Emerald)   | Core Brand, Primary Actions, Satisfied Rules   |
| `--ayur-accent`      | `#D97706` (Amber/Gold)| Traditional Knowledge, Warnings, Highlights    |
| `--ayur-dark-bg`     | `#0F172A` (Slate 900) | Deep Tech Background Canvas                    |
| `--ayur-card-bg`     | `rgba(30,41,59,0.7)`  | Translucent Glassmorphic Surface               |
| `--ayur-border`      | `rgba(255,255,255,0.1)`| Frosted Glass Border                           |
| `--conf-high`        | `#10B981` (Green)     | High Confidence Status Chip                    |
| `--conf-medium`      | `#F59E0B` (Yellow)    | Medium Confidence Status Chip                  |
| `--conf-low`         | `#F97316` (Orange)    | Low Confidence Status Chip                     |
| `--conf-abstain`     | `#EF4444` (Crimson)   | Insufficient Evidence / Abstention Alert       |
+----------------------+-----------------------+------------------------------------------------+
```

---

## 2. Typography & Spatial System

- **Primary Font**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`.
- **Display & Headings**: `Outfit`, `Cinzel` for hero headlines.
- **Indic Script Support**: `Noto Sans Devanagari` (Hindi/Marathi), `Noto Sans Tamil`, `Noto Sans Telugu`, `Noto Sans Bengali`.
- **Border Radius**: `rounded-2xl` ($16\text{px}$) for cards, `rounded-xl` ($12\text{px}$) for input groups, `rounded-full` for chips.
- **Backdrop Blur**: `backdrop-blur-md` ($12\text{px}$) with frosted highlights.

---

## 3. Core UI Components & Interactive Patterns

### 3.1 Innovation Passport Intake Builder
- Dynamic form layout with botanical autocomplete.
- Fact origin pill tags:
  - `User-confirmed` (Solid Emerald badge)
  - `Document-extracted` (Blue outline badge)
  - `Inferred` (Purple dashed badge)
  - `Unknown` (Amber warning badge)
- Clarification Alert Card with direct resolution buttons.

### 3.2 Cross-Jurisdiction Comparison Matrix
- 3-Column responsive grid comparing **India (ASU / Aahara)**, **United States (DSHEA)**, and **Canada (NHP)**.
- Header cards showing Calibrated Confidence Chips (`HIGH 🟢`, `MEDIUM 🟡`, `LOW 🟠`, `ABSTAIN 🔴`).
- Clickable citation badges with hover effects that trigger the **Citation Slide-over Inspector**.
- Persistent **Coverage Limitations Alert** positioned at the base of each column.

### 3.3 Interactive "Why?" Provenance Graph
- Visual flowchart nodes connecting:
  $$\text{[User Fact]} \longrightarrow \text{[Evaluated Rule]} \longrightarrow \text{[Statutory Gazette Section]} \longrightarrow \text{[Resulting Finding]}$$
- Color-coded branches indicating satisfied conditions vs gaps.

### 3.4 Live What-If Simulator Diff Workspace
- Split-screen layout:
  - **Left Pane**: Live editable formulation attributes & claim text.
  - **Right Pane**: Reactive visual diff highlighting newly triggered requirements (Green = Relaxed, Red = Stricter compliance required).

### 3.5 "Challenge My Innovation" Red-Team Drawer
- Dark crimson-accented review drawer simulating 2–3 examiner objections with investigable action recommendations.

### 3.6 Evidence-Gap Action Checklist & Coverage Meter
- Dependency-ordered checklist with lifecycle state pills (`Missing`, `Uploaded`, `Needs Review`, `Accepted`).
- Circular & linear progress **Coverage Meter** with tooltip clarifying that it indicates task completion, *not* approval probability.

---

## 4. Multilingual & Accessibility Layout

- Floating multilingual switcher supporting 10 scripts with native language labels.
- High contrast WCAG 2.1 AA certified text contrast ratios ($> 4.5:1$).
- Offline-status indicator pill in navbar with local sync queue counter.
