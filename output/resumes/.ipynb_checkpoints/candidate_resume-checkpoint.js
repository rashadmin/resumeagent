const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer, AlignmentType, PageOrientation, LevelFormat, BorderStyle, WidthType, ShadingType, TabStopType, TabStopPosition, Column, SectionType, PageNumber, PageBreak, HeadingLevel } = require('docx');
const fs = require('fs');

// Payload with extracted resume data
const payload = {
  "skills": ["Agentic Workflow Design", "Conversational AI Development", "Human-in-the-Loop System Design", "Prompt Engineering", "Retrieval-Augmented Generation", "LLM Orchestration", "Data Pipeline Design", "API Design and Integration", "Schema Validation and Data Modelling", "End-to-end ML Pipeline Design", "Time Series Forecasting", "Predictive Modelling", "Dashboard Design and Visualisation", "System Engineering", "DevOps Practices", "Data Analysis", "Model Deployment", "Software Architecture"],
  "technologies": ["Python", "FastAPI", "Docker", "LangChain", "LangGraph", "Pydantic", "Scikit-learn", "XGBoost", "Pandas", "NumPy", "Matplotlib", "Seaborn", "SQLAlchemy", "PostgreSQL", "Elasticsearch", "Git", "GitHub Actions", "Kubernetes", "Helm", "Terraform", "Ansible", "Bash", "Jupyter Notebooks", "Streamlit", "Flask", "React", "JavaScript", "HTML", "CSS", "REST APIs", "gRPC", "AWS", "Azure", "Google Cloud Platform", "Hugging Face Transformers", "OpenAI API", "LLaMA", "YouTube Data API"],
  "experience": [{"role_title": "Agentic AI Engineer", "date_range": "2023 – Present", "organisation": "Independent Projects / Research", "bullets": ["Designed and deployed stateful conversational AI agents using LangChain and LangGraph with custom tool nodes for medical and hospital scenarios", "Integrated human-in-the-loop validation mechanisms to improve accuracy and reliability of AI-driven guidance", "Developed end-to-end agentic workflows, including data ingestion, LLM interaction, and structured output generation using Pydantic", "Implemented API endpoints using FastAPI to serve AI agent functionalities, enabling integration with front-end applications", "Utilized Elasticsearch for efficient data retrieval and indexing within AI agent systems", "Managed containerized deployments using Docker and orchestrated workflows with GitHub Actions for CI/CD", "Built interactive dashboards using Streamlit to visualize agent performance and user interactions"]},
               {"role_title": "Data Scientist / ML Engineer", "date_range": "2022 – Present", "organisation": "Independent Projects / Research", "bullets": ["Developed and deployed predictive models for housing price prediction and fraud detection using Scikit-learn and XGBoost", "Engineered data pipelines for structured and unstructured data, ensuring data quality and efficient processing", "Performed comprehensive data analysis and visualization on European football leagues to identify performance trends", "Designed and implemented clustering algorithms for Glass identification datasets", "Created RESTful APIs with Flask to expose machine learning model predictions", "Managed version control and collaborated on projects using Git and GitHub", "Explored time series forecasting techniques for financial data analysis"]}],
  "projects": [{"name": "Medic Ai Agent", "tagline": "Conversational AI agent providing medical guidance and symptom analysis using LLMs and LangGraph.", "stack": ["Python", "LangChain", "LangGraph", "Pydantic", "FastAPI", "Docker", "Elasticsearch", "OpenAI API"], "bullets": ["Architected a stateful agent using LangGraph, defining custom nodes for symptom extraction, diagnosis suggestion, and treatment recommendation", "Enforced structured data output for patient information and medical advice using Pydantic models", "Integrated Elasticsearch for efficient retrieval of medical knowledge base articles", "Developed a FastAPI backend to expose the agent's capabilities as a RESTful API", "Containerized the application using Docker for consistent deployment"]},
               {"name": "Ny Taxi Workflow Orchestration", "tagline": "End-to-end data pipeline for processing and analyzing New York taxi trip data.", "stack": ["Python", "Pandas", "SQLAlchemy", "PostgreSQL", "Docker", "Airflow"], "bullets": ["Designed and implemented an ETL pipeline to ingest, clean, and transform large volumes of taxi trip data", "Utilized Pandas for data manipulation and SQLAlchemy for database interaction with PostgreSQL", "Orchestrated the workflow using Airflow, defining task dependencies and scheduling", "Containerized the pipeline components using Docker for reproducible execution"]},
               {"name": "Hospital Agent", "tagline": "AI agent designed to assist with hospital administrative tasks and patient inquiries.", "stack": ["Python", "LangChain", "LangGraph", "Pydantic", "Streamlit"], "bullets": ["Developed a conversational agent capable of handling patient registration and appointment scheduling", "Leveraged LangGraph to manage conversational state and complex decision-making logic", "Used Pydantic for validating and structuring input/output data related to patient records", "Created a user-friendly interface using Streamlit for interaction with the hospital agent"]},
               {"name": "Football Analysis In Europe Top 5 League", "tagline": "Comprehensive data analysis and visualization of European football leagues.", "stack": ["Python", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Jupyter Notebooks"], "bullets": ["Performed in-depth statistical analysis on player and team performance data across top European leagues", "Created insightful visualizations using Matplotlib and Seaborn to highlight key trends and performance metrics", "Applied data cleaning and preprocessing techniques to ensure data integrity", "Documented findings and methodologies in Jupyter Notebooks for clear communication"]}]}


// --- Constants and Styles ---
const COLOR_PRIMARY = "1F3864"; // Dark Navy
const COLOR_BODY = "222222";
const COLOR_SECONDARY = "555555";
const COLOR_TERTIARY = "666666";
const COLOR_QUATERNARY = "888888";
const FONT_SIZE_XL = 32; // Heading 1
const FONT_SIZE_LG = 28; // Heading 2
const FONT_SIZE_MD = 24; // Default body (12pt)
const FONT_SIZE_SM = 20; // 10pt
const FONT_SIZE_XS = 18; // 9pt

const MARGIN_SIDE = 900;
const MARGIN_TOP_BOTTOM = 720;

const CONTENT_WIDTH = 12240 - (2 * MARGIN_SIDE);

// Styles for the document
const styles = {
  default: {
    document: {
      run: {
        font: "Arial",
        size: FONT_SIZE_MD, // 12pt default
        color: COLOR_BODY,
        lineHeight: "1.5", // Approx 240 DXA for 12pt font
      }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: FONT_SIZE_XL, bold: true, font: "Arial", color: COLOR_PRIMARY },
        paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: FONT_SIZE_LG, bold: true, font: "Arial", color: COLOR_PRIMARY },
        paragraph: { spacing: { before: 120, after: 40 }, outlineLevel: 1 }
      },
      {
        id: "ExpRole", name: "Experience Role", basedOn: "Normal",
        run: { size: FONT_SIZE_MD, bold: true, font: "Arial", color: COLOR_PRIMARY }, // 12pt
        paragraph: { spacing: { after: 0 } }
      },
      {
        id: "ExpDate", name: "Experience Date", basedOn: "Normal",
        run: { size: FONT_SIZE_SM - 2, italic: true, font: "Arial", color: COLOR_TERTIARY }, // Approx 9pt
        paragraph: { spacing: { after: 0 } }
      },
      {
        id: "OrgName", name: "Organisation Name", basedOn: "Normal",
        run: { size: FONT_SIZE_SM - 1, italic: true, font: "Arial", color: COLOR_QUATERNARY }, // 9.5pt
        paragraph: { spacing: { after: 40 } }
      },
      {
        id: "ProjectName", name: "Project Name", basedOn: "Normal",
        run: { size: FONT_SIZE_MD, bold: true, font: "Arial", color: COLOR_PRIMARY }, // 12pt
        paragraph: { spacing: { after: 30 } }
      },
      {
        id: "ProjectTagline", name: "Project Tagline", basedOn: "Normal",
        run: { size: FONT_SIZE_SM - 2, italic: true, font: "Arial", color: COLOR_TERTIARY }, // Approx 9pt
        paragraph: { spacing: { after: 30 } }
      },
      {
        id: "ProjectStack", name: "Project Stack", basedOn: "Normal",
        run: { size: FONT_SIZE_SM - 1, bold: true, font: "Arial", color: COLOR_BODY }, // 9.5pt bold
        paragraph: { spacing: { after: 40 } }
      },
      {
        id: "ProjectStackTech", name: "Project Stack Tech", basedOn: "Normal",
        run: { size: FONT_SIZE_SM - 1, font: "Arial", color: COLOR_SECONDARY }, // 9.5pt
        paragraph: { spacing: { after: 40 } }
      },
      {
        id: "Education", name: "Education", basedOn: "Normal",
        run: { size: FONT_SIZE_SM, font: "Arial", color: COLOR_BODY }, // 10pt
        paragraph: { spacing: { after: 40 } }
      },
      {
        id: "ExpBullet", name: "Experience Bullet", basedOn: "Normal",
        run: { size: FONT_SIZE_SM, font: "Arial", color: COLOR_BODY }, // 10pt
        paragraph: { spacing: { after: 40 } }
      },
      {
        id: "ProjBullet", name: "Project Bullet", basedOn: "Normal",
        run: { size: FONT_SIZE_SM, font: "Arial", color: COLOR_BODY }, // 10pt
        paragraph: { spacing: { after: 40 } }
      },
    ]
  },
};


// --- Helper Functions ---
function createBulletParagraph(text, numberingRef, level = 0, styleId = "ExpBullet") {
  return new Paragraph({
    styleId: styleId,
    numbering: { reference: numberingRef, level: level },
    children: [new TextRun({ text: text, size: FONT_SIZE_SM, font: "Arial", color: COLOR_BODY })],
  });
}

function createSectionHeading(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, text: text });
}

// --- Document Content ---
const docChildren = [];

// Header
docChildren.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
      new TextRun({ text: "Candidate Name", size: FONT_SIZE_XL, bold: true, color: COLOR_PRIMARY }), // ~16pt bold
    ],
  })
);
docChildren.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
      new TextRun({ text: "email@example.com | github.com/yourusername | LinkedIn | Nigeria", size: FONT_SIZE_XS - 2, color: COLOR_SECONDARY }), // ~8pt
    ],
  })
);
// Divider
docChildren.push(
  new Paragraph({
    border: {
      bottom: { style: BorderStyle.SINGLE, size: 8, color: COLOR_PRIMARY, space: 4 }
    },
    spacing: { after: 120 },
    children: [],
  })
);

// Skills Section
docChildren.push(createSectionHeading("CORE SKILLS"));
const skillsTableWidth = CONTENT_WIDTH;
const skillColumns = 3;
const skillColWidth = Math.floor(skillsTableWidth / skillColumns);
const skillsChunkSize = Math.ceil(payload.skills.length / skillColumns);
const skillsChunks = [];
for (let i = 0; i < payload.skills.length; i += skillsChunkSize) {
  skillsChunks.push(payload.skills.slice(i, i + skillsChunkSize));
}

const skillsTableRows = [];
let maxSkillsInChunk = 0;
skillsChunks.forEach(chunk => { if(chunk.length > maxSkillsInChunk) maxSkillsInChunk = chunk.length; });

for (let i = 0; i < maxSkillsInChunk; i++) {
    const rowCells = [];
    for (let j = 0; j < skillColumns; j++) {
        if (skillsChunks[j] && skillsChunks[j][i]) {
            rowCells.push(
                new TableCell({
                    width: { size: skillColWidth, type: WidthType.DXA },
                    shading: { fill: "FFFFFF", type: ShadingType.CLEAR },
                    margins: { top: 40, bottom: 40, left: 80, right: 80 },
                    children: [
                        new Paragraph({
                            styleId: "ExpBullet",
                            children: [
                                new TextRun({ text: "›  ", size: FONT_SIZE_SM - 1, font: "Arial", color: COLOR_BODY }),
                                new TextRun({ text: skillsChunks[j][i], size: FONT_SIZE_SM - 1, font: "Arial", color: COLOR_BODY })
                            ],
                        })
                    ],
                })
            );
        } else {
            rowCells.push(new TableCell({ width: { size: skillColWidth, type: WidthType.DXA }, children: [new Paragraph({})] }));
        }
    }
    skillsTableRows.push(new TableRow({ children: rowCells }));
}

docChildren.push(
  new Table({
    width: { size: skillsTableWidth, type: WidthType.DXA },
    columnWidths: Array(skillColumns).fill(skillColWidth),
    rows: skillsTableRows,
  })
);
docChildren.push(new Paragraph({ spacing: { after: 160 } }));

// Technologies Section
docChildren.push(createSectionHeading("CORE TOOLS"));
const techTableWidth = CONTENT_WIDTH;
const techColumns = 3;
const techColWidth = Math.floor(techTableWidth / techColumns);
const techChunkSize = Math.ceil(payload.technologies.length / techColumns);
const techChunks = [];
for (let i = 0; i < payload.technologies.length; i += techChunkSize) {
  techChunks.push(payload.technologies.slice(i, i + techChunkSize));
}

const techTableRows = [];
let maxTechInChunk = 0;
techChunks.forEach(chunk => { if(chunk.length > maxTechInChunk) maxTechInChunk = chunk.length; });

for (let i = 0; i < maxTechInChunk; i++) {
    const rowCells = [];
    for (let j = 0; j < techColumns; j++) {
        if (techChunks[j] && techChunks[j][i]) {
            rowCells.push(
                new TableCell({
                    width: { size: techColWidth, type: WidthType.DXA },
                    shading: { fill: "FFFFFF", type: ShadingType.CLEAR },
                    margins: { top: 40, bottom: 40, left: 80, right: 80 },
                    children: [
                        new Paragraph({
                            children: [new TextRun({ text: techChunks[j][i], size: FONT_SIZE_SM - 1, font: "Arial", color: COLOR_BODY })],
                        })
                    ],
                })
            );
        } else {
            rowCells.push(new TableCell({ width: { size: techColWidth, type: WidthType.DXA }, children: [new Paragraph({})] }));
        }
    }
    techTableRows.push(new TableRow({ children: rowCells }));
}

docChildren.push(
  new Table({
    width: { size: techTableWidth, type: WidthType.DXA },
    columnWidths: Array(techColumns).fill(techColWidth),
    rows: techTableRows,
  })
);
docChildren.push(new Paragraph({ spacing: { after: 160 } }));


// Professional Experience Section
docChildren.push(createSectionHeading("PROFESSIONAL EXPERIENCE"));

const expBulletNumbering = {
  config: [
    {
      reference: "exp-bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
      }]
    }
  ]
};

payload.experience.forEach((exp, expIndex) => {
  docChildren.push(
    new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
      children: [
        new TextRun({ text: exp.role_title, size: FONT_SIZE_MD, bold: true, color: COLOR_PRIMARY }),
        new TextRun({ text: "\t" + exp.date_range, size: FONT_SIZE_SM - 2, italic: true, color: COLOR_TERTIARY }),
      ],
      spacing: { after: 0 },
    })
  );

  docChildren.push(
    new Paragraph({
      children: [new TextRun({ text: exp.organisation, size: FONT_SIZE_SM - 1, italic: true, color: COLOR_QUATERNARY })],
      spacing: { after: 40 }
    })
  );

  exp.bullets.forEach((bullet, bulletIndex) => {
    docChildren.push(createBulletParagraph(bullet, "exp-bullets", 0, "ExpBullet"));
  });

  docChildren.push(new Paragraph({ spacing: { after: 160 } }));
});


// Projects Section
docChildren.push(createSectionHeading("PROJECTS"));

const projBulletNumberingConfigs = {};
payload.projects.forEach((_, index) => {
  projBulletNumberingConfigs[`proj-${index}`] = {
    config: [
      {
        reference: `proj-${index}`,
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
      }
    ]
  };
});

payload.projects.forEach((project, projIndex) => {
  docChildren.push(
    new Paragraph({
      children: [new TextRun({ text: project.name, size: FONT_SIZE_MD, bold: true, color: COLOR_PRIMARY })],
      spacing: { after: 30 },
    })
  );

  docChildren.push(
    new Paragraph({
      children: [new TextRun({ text: project.tagline, size: FONT_SIZE_SM - 2, italic: true, color: COLOR_TERTIARY })],
      spacing: { after: 30 },
    })
  );

  docChildren.push(
    new Paragraph({
      children: [
        new TextRun({ text: "Stack:  ", size: FONT_SIZE_SM - 1, bold: true, color: COLOR_BODY }),
        new TextRun({ text: project.stack.join(", "), size: FONT_SIZE_SM - 1, color: COLOR_SECONDARY })
      ],
      spacing: { after: 40 },
    })
  );

  project.bullets.forEach((bullet, bulletIndex) => {
    docChildren.push(createBulletParagraph(bullet, `proj-${projIndex}`, 0, "ProjBullet"));
  });

  docChildren.push(new Paragraph({ spacing: { after: 160 } }));
});


// Education Section
docChildren.push(createSectionHeading("EDUCATION"));
docChildren.push(
  new Paragraph({
    children: [
      new TextRun({ text: "M.Sc. in Computer Science, University of Example, 2020", size: FONT_SIZE_SM, color: COLOR_BODY }),
    ],
    spacing: { after: 40 }
  })
);


// --- Document Creation ---
const doc = new Document({
  styles: styles,
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840, orientation: PageOrientation.PORTRAIT }, // US Letter
        margin: { top: MARGIN_TOP_BOTTOM, right: MARGIN_SIDE, bottom: MARGIN_TOP_BOTTOM, left: MARGIN_SIDE }
      }
    },
    headers: {
      default: new Header({ children: [] })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "Page ", size: FONT_SIZE_XS, color: COLOR_SECONDARY }),
              new PageNumber({ size: FONT_SIZE_XS, color: COLOR_SECONDARY })
            ],
            alignment: AlignmentType.CENTER
          })
        ]
      })
    },
    children: docChildren,
    numbering: {
      config: [
        ...(expBulletNumbering.config),
        ...(Object.values(projBulletNumberingConfigs).flatMap(conf => conf.config))
      ]
    }
  }]
});

// --- Output ---
const output_path = "/home/user/output/resumes/candidate_resume.docx"; // This path will be provided by generate_resume_js

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(output_path, buffer);
  console.log("Resume written to " + output_path);
});
