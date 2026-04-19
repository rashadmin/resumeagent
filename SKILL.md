# Resume DOCX Skill — Custom Spec

## Overview

Professional resume in the Ameen Abdulrasheed style. No lines, no tables,
tight spacing, navy headings. Skills and tools use tab-stop paragraphs — not
tables — so there are zero border issues.

Section order: Header → Summary → Core Skills → Core Tools →
Professional Experience → Projects → Education

---

## Setup

```javascript
const fs   = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun,
  AlignmentType, LevelFormat, BorderStyle,
  WidthType, ShadingType, TabStopType, TabStopPosition,
  HeadingLevel, PageBreak, PageOrientation,
  PageNumber, ExternalHyperlink, VerticalAlign
} = require("docx");
```

Note: `Table`, `TableRow`, `TableCell` are NOT needed — skills and tools use
tab-stop paragraphs instead. Keep the require line above exactly as written.

After the require lines, load profile and payload:

```javascript
const profile = JSON.parse(
  fs.readFileSync(path.join(__dirname, "candidate_profile.json"), "utf8"));

// CRITICAL: load from the sidecar JSON — NEVER hardcode arrays in the script
const payload = JSON.parse(
  fs.readFileSync(path.join(__dirname, "<candidate_name>_payload.json"), "utf8"));
```

---

## Page Setup

```javascript
sections: [{
  properties: {
    page: {
      size: { width: 12240, height: 15840 },  // US Letter — NO orientation property
      margin: { top: 620, bottom: 620, left: 900, right: 900 }
    }
  },
  children: [ /* all content paragraphs */ ]
}]
```

Content width = 12240 − 900 − 900 = **10440 DXA**

---

## Typography

| Use                 | Font  | Size (half-pts) | Weight        | Color  |
|---------------------|-------|-----------------|---------------|--------|
| Candidate name      | Arial | 32 (16pt)       | bold          | 1F3864 |
| Title line          | Arial | 20 (10pt)       | normal        | 1F3864 |
| Contact line        | Arial | 18 (9pt)        | normal        | 1F3864 |
| Section heading     | Arial | 20 (10pt)       | bold, allCaps | 1F3864 |
| Body / bullets      | Arial | 20 (10pt)       | normal        | 000000 |
| Org / date sub-line | Arial | 19 (9.5pt)      | italic        | 666666 |
| Role title          | Arial | 21 (10.5pt)     | bold          | 1F3864 |
| Skills / tools text | Arial | 19 (9.5pt)      | normal        | 222222 |

**Size in docx-js is always in half-points**: 10pt = size 20, 9.5pt = size 19.

---

## Document Styles Block

```javascript
styles: {
  default: {
    document: { run: { font: "Arial", size: 20, color: "000000" } }
  },
  paragraphStyles: [
    {
      id: "Heading1", name: "Heading 1",
      basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: "Arial", size: 20, bold: true, allCaps: true, color: "1F3864" },
      paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 0 }
    },
    {
      id: "Heading2", name: "Heading 2",
      basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: "Arial", size: 21, bold: true, color: "1F3864" },
      paragraph: { spacing: { before: 100, after: 30 }, outlineLevel: 1 }
    }
  ]
}
```

---

## Numbering Config

Only needed for experience and project bullets — NOT for skills/tools.

```javascript
numbering: {
  config: [
    {
      reference: "exp-bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 360, hanging: 180 }, spacing: { after: 40 } } }
      }]
    },
    { reference: "proj-0", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 180 }, spacing: { after: 40 } } } }] },
    { reference: "proj-1", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 180 }, spacing: { after: 40 } } } }] },
    { reference: "proj-2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 180 }, spacing: { after: 40 } } } }] },
    { reference: "proj-3", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 180 }, spacing: { after: 40 } } } }] },
  ]
}
```

---

## NO Lines Rule — Critical

**Zero lines, rules, or borders anywhere in this document.**
There are no tables, so there are no table borders to worry about.
Never add a `border` property to any `Paragraph`.

---

## Section-by-Section Spec

Build the `children` array in this EXACT order:
1. Header (name → title → contact)
2. Professional Summary
3. Core Skills
4. Core Tools
5. Professional Experience
6. Projects
7. Education

---

### 1. HEADER

Three centered paragraphs — no table.

```javascript
// Name
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 30 },
  children: [new TextRun({ text: profile.name, bold: true, size: 32, font: "Arial", color: "1F3864" })]
}),

// Title
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 30 },
  children: [new TextRun({ text: profile.title, size: 20, font: "Arial", color: "1F3864" })]
}),

// Contact — order: email | phone | portfolio | github | linkedin | location
new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 140 },
  children: [
    new TextRun({ text: profile.email,     size: 18, font: "Arial", color: "1F3864" }),
    new TextRun({ text: "  |  ",           size: 18, font: "Arial", color: "AAAAAA" }),
    new TextRun({ text: profile.phone,     size: 18, font: "Arial", color: "1F3864" }),
    new TextRun({ text: "  |  ",           size: 18, font: "Arial", color: "AAAAAA" }),
    new TextRun({ text: profile.portfolio, size: 18, font: "Arial", color: "1F3864" }),
    new TextRun({ text: "  |  ",           size: 18, font: "Arial", color: "AAAAAA" }),
    new TextRun({ text: profile.github,    size: 18, font: "Arial", color: "1F3864" }),
    new TextRun({ text: "  |  ",           size: 18, font: "Arial", color: "AAAAAA" }),
    new TextRun({ text: profile.linkedin,  size: 18, font: "Arial", color: "1F3864" }),
    new TextRun({ text: "  |  ",           size: 18, font: "Arial", color: "AAAAAA" }),
    new TextRun({ text: profile.location,  size: 18, font: "Arial", color: "1F3864" }),
  ]
}),
```

---

### 2. PROFESSIONAL SUMMARY

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "PROFESSIONAL SUMMARY", font: "Arial" })]
}),
new Paragraph({
  spacing: { after: 120, line: 260 },
  children: [new TextRun({ text: payload.summary, size: 20, font: "Arial", color: "000000" })]
}),
```

---

### 3. CORE SKILLS — 4 per row using tab stops

**No table.** Each paragraph holds 4 skills separated by `\t`.
Tab stops divide content width into fifths: 2088, 4176, 6264, 8352 DXA.
(10440 / 4 = 2610 per column)

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "CORE SKILLS", font: "Arial" })]
}),

...(() => {
  const SKILLS_PER_ROW = 4;

  // 10440 total width ÷ 4 columns
  const TAB1 = 2610;
  const TAB2 = 5220;
  const TAB3 = 7830;

  const rows = [];
  for (let i = 0; i < payload.skills.length; i += SKILLS_PER_ROW) {
    const s = payload.skills;
    const children = [];

    // First skill (no tab)
    children.push(new TextRun({
      text: "\u2022  " + (s[i] || ""),
      size: 19,
      font: "Arial",
      color: "222222"
    }));

    // Remaining skills with tabs
    for (let j = 1; j < SKILLS_PER_ROW; j++) {
      if (s[i + j] !== undefined) {
        children.push(new TextRun({
          text: "\t\u2022  " + s[i + j],
          size: 19,
          font: "Arial",
          color: "222222"
        }));
      }
    }

    rows.push(new Paragraph({
      tabStops: [
        { type: TabStopType.LEFT, position: TAB1 },
        { type: TabStopType.LEFT, position: TAB2 },
        { type: TabStopType.LEFT, position: TAB3 },
      ],
      spacing: { after: 40 },
      children
    }));
  }

  return rows;
})(),
```

---

### 4. CORE TOOLS — 5 per row using tab stops, with bullet prefix

**No table.** Same approach as skills — 5 per row, bullet prefix `• `.
Tab stops at fifths of content width.
(10440 / 5 = 2088 per column)

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "CORE TOOLS", font: "Arial" })]
}),

...(() => {
  const TOOLS_PER_ROW = 5;

  const TAB1 = 2088;  // 10440 / 5
  const TAB2 = 4176;
  const TAB3 = 6264;
  const TAB4 = 8352;

  const rows = [];

  for (let i = 0; i < payload.technologies.length; i += TOOLS_PER_ROW) {
    const t = payload.technologies;
    const children = [];

    // First item — no tab prefix
    children.push(new TextRun({
      text: "\u2022  " + (t[i] || ""),
      size: 19,
      font: "Arial",
      color: "222222"
    }));

    for (let j = 1; j < TOOLS_PER_ROW; j++) {
      if (t[i + j] !== undefined) {
        children.push(new TextRun({
          text: "\t\u2022  " + t[i + j],
          size: 19,
          font: "Arial",
          color: "222222"
        }));
      }
    }

    rows.push(new Paragraph({
      tabStops: [
        { type: TabStopType.LEFT, position: TAB1 },
        { type: TabStopType.LEFT, position: TAB2 },
        { type: TabStopType.LEFT, position: TAB3 },
        { type: TabStopType.LEFT, position: TAB4 },
      ],
      spacing: { after: 40 },
      children
    }));
  }

  return rows;
})(),
```

---

### 5. PROFESSIONAL EXPERIENCE

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "PROFESSIONAL EXPERIENCE", font: "Arial" })]
}),

...payload.experience.flatMap((entry, ei) => [
  // Role title left, date right via tab stop
  new Paragraph({
    alignment: AlignmentType.LEFT,
    tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
    spacing: { before: 100, after: 0 },
    children: [
      new TextRun({ text: entry.role_title, bold: true, size: 21, font: "Arial", color: "1F3864" }),
      new TextRun({ text: "\t" + entry.date_range, italics: true, size: 19, font: "Arial", color: "666666" })
    ]
  }),
  // Organisation
  new Paragraph({
    spacing: { before: 0, after: 80 },
    children: [new TextRun({ text: entry.organisation, italics: true, size: 19, font: "Arial", color: "888888" })]
  }),
  // Bullets
  ...entry.bullets.map((bullet, bi) => new Paragraph({
    numbering: { reference: "exp-bullets", level: 0 },
    spacing: { after: bi === entry.bullets.length - 1 ? 160 : 40 },
    children: [new TextRun({ text: bullet, size: 20, font: "Arial", color: "000000" })]
  }))
]),
```

---

### 6. PROJECTS

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "PROJECTS", font: "Arial" })]
}),

...payload.projects.flatMap((project, pi) => [
  // Project name
  new Paragraph({
    spacing: { before: 100, after: 50 },
    children: [new TextRun({ text: project.name, bold: true, size: 21, font: "Arial", color: "1F3864" })]
  }),
  // Bullets — "proj-" + pi for independent reset per project
  ...project.bullets.map((bullet, bi) => new Paragraph({
    numbering: { reference: "proj-" + pi, level: 0 },
    spacing: { after: bi === project.bullets.length - 1 ? 160 : 40 },
    children: [new TextRun({ text: bullet, size: 20, font: "Arial", color: "000000" })]
  }))
]),
```

**NEVER use `projectIndex` — always use `pi` from `flatMap`/`forEach`.**

---

### 7. EDUCATION

```javascript
new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "EDUCATION", font: "Arial" })]
}),

...profile.education.map(edu => new Paragraph({
  spacing: { after: 60 },
  children: [new TextRun({
    text: edu.degree + "  |  " + edu.institution + ".  " + edu.year,
    size: 20, font: "Arial", color: "000000"
  })]
})),
```

---

## Output

End every script with EXACTLY this — `OUTPUT_PATH_PLACEHOLDER` verbatim:

```javascript
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("OUTPUT_PATH_PLACEHOLDER", buf);
  console.log("Resume written to OUTPUT_PATH_PLACEHOLDER");
}).catch(err => {
  console.error("Failed:", err.message);
  process.exit(1);
});
```

The `generate_resume_js` tool replaces `OUTPUT_PATH_PLACEHOLDER` with the
real absolute path automatically. Never hardcode any path.

---

## Critical Rules Checklist

Before calling `generate_resume_js`, verify ALL of these:

- [ ] Exact require line present — no Table/TableRow/TableCell needed
- [ ] `const path = require("path")` present
- [ ] `candidate_profile.json` read with `path.join(__dirname, ...)`
- [ ] `<candidate_name>_payload.json` read with `path.join(__dirname, ...)` — NEVER hardcode data
- [ ] Page: width 12240, height 15840, NO orientation — margins top/bottom 620, left/right 900
- [ ] Section order: Header → Summary → Core Skills → Core Tools → Experience → Projects → Education
- [ ] Core Skills: 5 per row, tab stops at 2088 4176 6264 8352, bullet prefix `• `
- [ ] Core Tools: 6 per row, tab stops at 1740 3480 5220 6960 8700, bullet prefix `• `
- [ ] Heading color `1F3864` on all Heading1 TextRuns, role_title TextRuns, project name TextRuns
- [ ] `LevelFormat.BULLET` in numbering config — no `•` directly in TextRun for exp/project bullets
- [ ] All four `proj-0` through `proj-3` defined in numbering.config
- [ ] Projects loop uses `"proj-" + pi` — never `projectIndex`
- [ ] No `\n` inside any TextRun — separate Paragraph elements only
- [ ] `OUTPUT_PATH_PLACEHOLDER` verbatim in Packer.toBuffer call
