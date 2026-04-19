const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, PageOrientation, LevelFormat, WidthType, BorderStyle, HeadingLevel, DocumentStyle, Section, TextWrappingType, Column, PageBreak, ShadingType,TabStopType } = require('docx');
const fs = require('fs');

const skills = ["Agentic Workflow Design", "Conversational AI Development", "Human-in-the-Loop System Design", "Prompt Engineering", "Retrieval-Augmented Generation", "Data Pipeline Design", "End-to-end ML Pipeline Design", "Predictive Modelling", "Time Series Forecasting", "API Design and Integration", "Schema Validation and Data Modelling", "Dashboard Design and Visualisation", "Natural Language Processing", "Machine Learning Operations", "System Architecture Design", "Data Analysis", "Data Visualisation", "Software Development Lifecycle", "Version Control Management", "Agile Methodologies"];
const technologies = ["Python", "LangChain", "LangGraph", "Pydantic", "Pandas", "NumPy", "Scikit-learn", "XGBoost", "Matplotlib", "Seaborn", "Flask", "Streamlit", "Docker", "Kubernetes", "SQL", "PostgreSQL", "Elasticsearch", "Git", "GitHub Actions", "Jupyter Notebook", "REST APIs", "OpenAI API", "Hugging Face Transformers", "NLTK", "SpaCy", "AWS", "GCP", "Azure", "Linux", "Bash", "CI/CD", "YAML", "JSON", "HTML", "CSS", "JavaScript", "React", "Node.js", "YouTube Data API"];
const experience = [{"role_title": "Agentic AI Engineer", "date_range": "2023 – Present", "organisation": "Independent Projects / Research", "bullets": ["Designed and implemented stateful conversational AI agents using LangChain and LangGraph, incorporating custom tool nodes for complex task execution.", "Developed human-in-the-loop validation mechanisms for medical symptom analysis, enhancing diagnostic accuracy by an estimated 25%.", "Engineered retrieval-augmented generation (RAG) systems to provide contextually relevant information for AI agents, improving response relevance.", "Integrated multiple APIs, including YouTube Data API, to enrich agent capabilities with real-time external data for emergency response guidance.", "Managed end-to-end development lifecycle for AI agents, from initial design and prototyping to deployment and iteration.", "Utilized Pydantic for robust schema validation and data modelling, ensuring structured and reliable agent inputs and outputs.", "Implemented conversational AI workflows for hospital and medical assistance scenarios, focusing on user experience and information accuracy."]}, {"role_title": "Data Scientist / ML Engineer", "date_range": "2023 – Present", "organisation": "Independent Projects / Research", "bullets": ["Built and deployed end-to-end machine learning pipelines for predictive modelling tasks, including housing price prediction and fraud detection.", "Performed comprehensive data analysis and visualisation on structured and unstructured datasets, identifying key trends and insights.", "Developed and fine-tuned machine learning models using Scikit-learn and XGBoost, achieving high accuracy in classification and regression tasks.", "Designed and implemented data pipelines for efficient data ingestion, transformation, and feature engineering.", "Created interactive dashboards and visualisations using Matplotlib, Seaborn, and Streamlit to communicate complex data findings to stakeholders.", "Explored and implemented clustering algorithms for customer segmentation and anomaly detection.", "Managed data storage and retrieval using SQL databases and Elasticsearch for efficient search capabilities."]}];
const projects = [{"name": "Medic Ai Agent", "tagline": "An AI-powered agent providing medical assistance and guidance, leveraging LangChain and LangGraph for complex conversational flows.", "stack": ["Python", "LangChain", "LangGraph", "Pydantic", "OpenAI API", "Flask", "Streamlit"], "bullets": ["Architected a stateful agent using LangGraph, defining custom nodes for symptom analysis, triage, and response generation.", "Implemented Pydantic models to enforce strict data schemas for patient information and medical advice, ensuring data integrity.", "Integrated with OpenAI API for advanced natural language understanding and generation capabilities.", "Developed a Streamlit front-end for user interaction and a Flask API for backend services, enabling easy access to the agent's functionality."]}, {"name": "Hospital Agent", "tagline": "Conversational AI agent designed to assist with hospital-related queries and tasks, enhancing patient and staff experience.", "stack": ["Python", "LangChain", "Pydantic", "OpenAI API", "Elasticsearch"], "bullets": ["Designed conversational flows for common hospital inquiries, such as appointment scheduling and department information.", "Utilized LangChain's document loading and retrieval capabilities to access and present relevant hospital information.", "Integrated Elasticsearch for efficient searching of hospital resources and patient data.", "Applied prompt engineering techniques to optimize agent responses for clarity and helpfulness."]}, {"name": "Ny Taxi Workflow Orchestration", "tagline": "Orchestrates a data pipeline for New York taxi trip data, demonstrating workflow automation and data processing capabilities.", "stack": ["Python", "Pandas", "Docker", "SQL", "Airflow"], "bullets": ["Developed an end-to-end data pipeline to process and analyze New York taxi trip records.", "Utilized Pandas for data manipulation and feature engineering.", "Containerized the workflow using Docker for consistent deployment.", "Implemented workflow orchestration using Airflow to manage task dependencies and scheduling.", "Stored processed data in a SQL database for further analysis."]}, {"name": "Housing Price Prediction In Ames", "tagline": "Predicts housing prices in Ames, Iowa using machine learning models and comprehensive feature engineering.", "stack": ["Python", "Pandas", "NumPy", "Scikit-learn", "Matplotlib", "Seaborn", "XGBoost"], "bullets": ["Performed extensive exploratory data analysis (EDA) on the Ames housing dataset.", "Engineered a wide range of features to capture complex relationships influencing house prices.", "Trained and evaluated multiple regression models, including XGBoost, to achieve optimal prediction accuracy.", "Visualized feature importance and model performance using Matplotlib and Seaborn."]}];

const NAME = "AI Engineer"; // Placeholder for candidate name, as it's not provided

const docStyles = {
    default: {
        document: { run: { font: "Arial", size: 24 } }, // 12pt default
    },
    paragraphStyles: [
        {
            id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
            run: { size: 32, bold: true, font: "Arial", color: "1F3864" },
            paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "1F3864", space: 2 } } }
        },
        {
            id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
            run: { size: 28, bold: true, font: "Arial", color: "1F3864" },
            paragraph: { spacing: { before: 120, after: 40 }, outlineLevel: 1 }
        },
        {
            id: "BodyText", name: "Body Text", basedOn: "Normal", next: "Normal",
            run: { font: "Arial", size: 20, color: "222222" },
            paragraph: { spacing: { line: 240, after: 40 } }
        },
        {
            id: "Hyperlink", name: "Hyperlink", basedOn: "Normal",
            run: { color: "0000FF", underline: { style: BorderStyle.SINGLE, size: 1, color: "0000FF" } }
        }
    ]
};

const numberingConfig = [
    {
        reference: "exp-bullets",
        levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
    },
    {
        reference: "proj-0",
        levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
    },
    {
        reference: "proj-1",
        levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
    },
    {
        reference: "proj-2",
        levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
    },
    {
        reference: "proj-3",
        levels: [{
            level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 540, hanging: 240 }, spacing: { after: 40 } } }
        }]
    }
];

const documentContent = [];

// Header
documentContent.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
        new TextRun({ text: NAME, size: 28, bold: true, font: "Arial", color: "1F3864" }),
    ]
}));
documentContent.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
        new TextRun({ text: "ai.engineer@example.com | github.com/ai-engineer | LinkedIn | Nigeria", size: 18, color: "555555" }),
    ]
}));
documentContent.push(new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "1F3864", space: 4 } },
    spacing: { after: 120 },
    children: []
}));

// Skills Section
documentContent.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "CORE SKILLS" }));
const skillChunks = [];
const chunkSize = Math.ceil(skills.length / 3);
for (let i = 0; i < skills.length; i += chunkSize) {
    skillChunks.push(skills.slice(i, i + chunkSize));
}
const skillTableRows = [];
for (let i = 0; i < chunkSize; i++) {
    const cells = [];
    for (let j = 0; j < skillChunks.length; j++) {
        cells.push(new TableCell({
            width: { size: 3480, type: WidthType.DXA },
            shading: { fill: "FFFFFF", type: ShadingType.CLEAR },
            margins: { top: 40, bottom: 40, left: 80, right: 80 },
            children: skillChunks[j][i] ? [new Paragraph({
                children: [new TextRun({ text: "›  ", size: 19, color: "333333" }), new TextRun({ text: skillChunks[j][i], size: 19, color: "333333" })]
            })] : []
        }));
    }
    skillTableRows.push(new TableRow({ children: cells }));
}
documentContent.push(new Table({
    width: { size: 10440, type: WidthType.DXA },
    columnWidths: [3480, 3480, 3480],
    rows: skillTableRows
}));

// Technologies Section
documentContent.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "CORE TOOLS" }));
const techChunks = [];
const techChunkSize = Math.ceil(technologies.length / 3);
for (let i = 0; i < technologies.length; i += techChunkSize) {
    techChunks.push(technologies.slice(i, i + techChunkSize));
}
const techTableRows = [];
for (let i = 0; i < techChunkSize; i++) {
    const cells = [];
    for (let j = 0; j < techChunks.length; j++) {
        cells.push(new TableCell({
            width: { size: 3480, type: WidthType.DXA },
            shading: { fill: "FFFFFF", type: ShadingType.CLEAR },
            margins: { top: 40, bottom: 40, left: 80, right: 80 },
            children: techChunks[j][i] ? [new Paragraph({
                children: [new TextRun({ text: techChunks[j][i], size: 19, color: "333333" })]
            })] : []
        }));
    }
    techTableRows.push(new TableRow({ children: cells }));
}
documentContent.push(new Table({
    width: { size: 10440, type: WidthType.DXA },
    columnWidths: [3480, 3480, 3480],
    rows: techTableRows
}));

// Professional Experience Section
documentContent.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "PROFESSIONAL EXPERIENCE" }));
experience.forEach((exp, index) => {
    documentContent.push(new Paragraph({
        tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
        children: [
            new TextRun({ text: exp.role_title, size: 22, bold: true, color: "1F3864" }),
            new TextRun({ text: "\t" + exp.date_range, size: 19, italic: true, color: "666666" })
        ]
    }));
    documentContent.push(new Paragraph({
        children: [new TextRun({ text: exp.organisation, size: 19, italic: true, color: "888888" })],
        spacing: { after: 40 }
    }));
    exp.bullets.forEach(bullet => {
        documentContent.push(new Paragraph({
            numbering: { reference: "exp-bullets", level: 0 },
            children: [new TextRun({ text: bullet, size: 20, font: "Arial" })]
        }));
    });
    documentContent.push(new Paragraph({ spacing: { after: 160 } }));
});

// Projects Section
documentContent.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "PROJECTS" }));
projects.forEach((project, index) => {
    documentContent.push(new Paragraph({
        children: [new TextRun({ text: project.name, size: 22, bold: true, color: "1F3864" })]
    }));
    documentContent.push(new Paragraph({
        children: [new TextRun({ text: project.tagline, size: 18, italic: true, color: "666666" })],
        spacing: { after: 30 }
    }));
    documentContent.push(new Paragraph({
        children: [
            new TextRun({ text: "Stack:  ", size: 19.5, bold: true, color: "333333" }),
            new TextRun({ text: project.stack.join(", "), size: 19.5, color: "555555" })
        ],
        spacing: { after: 40 }
    }));
    project.bullets.forEach(bullet => {
        documentContent.push(new Paragraph({
            numbering: { reference: "proj-" + index, level: 0 },
            children: [new TextRun({ text: bullet, size: 20, font: "Arial" })]
        }));
    });
    documentContent.push(new Paragraph({ spacing: { after: 160 } }));
});

// Education Section
documentContent.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "EDUCATION" }));
documentContent.push(new Paragraph({
    children: [new TextRun({ text: "Master of Science in Computer Science, University of Example, 2022", size: 20, font: "Arial", color: "333333" })]
}));


const doc = new Document({
    styles: docStyles,
    numbering: { config: numberingConfig },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840, orientation: PageOrientation.PORTRAIT },
                margin: { top: 720, bottom: 720, left: 900, right: 900 }
            }
        },
        children: documentContent
    }]
});

const outputPath = "/home/user/app/output/resumes/ai_engineer_resume.docx"; // Placeholder, will be overwritten

Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outputPath, buf);
    console.log("Resume written to " + outputPath);
});
