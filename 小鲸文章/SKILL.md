---
name: 小鲸文章
description: 快速编写有权威来源支撑、适合知识库入库的健康科普文章。用于用户要求写慢病、肿瘤、筛查、风险评估、预防、报告解读、用药科普、患者教育等 Markdown 文章，并需要引用最新指南、论文、数据库或权威机构来源时。
---

# 小鲸文章

## Overview

Write fast, high-quality health education articles that are easy for ordinary readers to understand and strict enough for a medical knowledge base. The skill combines topic refinement, article specification, authoritative source verification, structured explanatory writing, and final quality gates.

The output should feel like a polished patient-facing article, not a literature review and not a casual internet post: clear title, useful conclusions, plain-language explanation, risk boundaries, practical next steps, and traceable sources. By default, produce a batch of at least 5 `.md` articles and save them into the best matching directory under `/Users/hua/Documents/基础知识`.

## When to Use

- Writing disease education articles, especially chronic disease, cancer, screening, prevention, risk assessment, symptoms, report interpretation, treatment overview, medication education, lifestyle management, myths, or family support.
- Creating Markdown articles for a health knowledge base, RAG corpus, patient education library, public health content system, or standardized disease module.
- The user asks for articles that need journal, paper, guideline, consensus, PubMed, WHO/IARC, CDC, NCI, NCCN, ESMO, CSCO, Cochrane, SEER, GLOBOCAN, or similar support.
- The user provides example articles and wants new articles with the same quality, rhythm, structure, and citation discipline.
- The user wants quick batch writing and has already provided the disease, module, topic list, target directory, or article count.
- The user gives only a disease/topic and expects the agent to locate or create the right folder under `/Users/hua/Documents/基础知识`.

**When NOT to use:** Do not use for personal diagnosis, emergency triage, individualized treatment decisions, prescription changes, or content that asks the agent to replace a clinician. For code documentation, follow the `documentation-and-adrs` skill instead. For framework implementation, follow the `source-driven-development` skill.

## Core Workflow

```
INPUT -> ARTICLE SPEC -> PATH PLAN -> SOURCE PACK -> DRAFT BATCH -> SAFETY PASS -> SAVE/REPORT
```

### 1. Identify the article spec

Extract these fields from the user request and existing files. Ask only when a missing field would materially change the output.

| Field | Default if missing |
|---|---|
| Disease/topic | Infer from path, examples, or user wording |
| Module | Infer from folder name or standard knowledge system |
| Audience | Ordinary patients and family members |
| Language | Match the user's language; Chinese for Chinese requests |
| Format | Markdown article |
| Article count | At least 5 `.md` articles per batch unless the user explicitly asks for fewer |
| Length | 900-1600 Chinese characters for quick knowledge-base articles; longer only if requested |
| Tone | Plain, calm, practical, non-alarmist |
| Output path | Prefer the directory the user provided; otherwise search `/Users/hua/Documents/基础知识` and create the best matching topic directory if needed |
| Source freshness | Prefer the latest 3 years; include older landmark guidance only when still authoritative |

If the user gives example files, read them first and mirror their useful properties:

- Title style and filename style
- Section rhythm
- Reader level
- Citation format
- Disclaimer placement
- Practical tables or checklists

### 2. Plan the output path and batch

Before drafting, resolve where the articles should live.

Default knowledge base root:

```
/Users/hua/Documents/基础知识
```

Path selection rules:

1. If the user provides an exact output directory, use it.
2. If the user provides a disease/topic but no exact directory, search `/Users/hua/Documents/基础知识` for matching disease names, aliases, organ systems, or existing module folders.
3. If a matching disease directory exists but the requested article category does not, create a new category directory under that disease directory.
4. If no matching disease/topic directory exists, create a new top-level disease/topic directory under `/Users/hua/Documents/基础知识`, then create the requested article category inside it when useful.
5. Preserve nearby naming conventions. For example, if similar folders use `基础认知与风险评估`, use that exact module name instead of inventing a synonym.

Batch rules:

- Produce at least 5 Markdown files in one run unless the user explicitly asks for fewer.
- If the user gives fewer than 5 titles, expand them into at least 5 tightly related article angles.
- If the user gives more than 5 titles, write the requested count.
- Number filenames with two digits when creating a series: `01_标题.md`, `02_标题.md`, etc.
- Avoid overwriting existing files. If a filename exists, choose a distinct title or add a short suffix that preserves readability.
- After writing, report the saved file paths.

### 3. Refine the angle before writing

Borrow the clarity habit from `idea-refine`: each article needs one sharp promise. Before drafting, reduce the topic to one sentence:

```
This article helps [audience] understand [specific question] so they can [practical decision/action].
```

Good health education angles:

- "Which people are high risk and should not wait for symptoms?"
- "What does this test mean, and what can it not prove?"
- "Which risk factors can be changed, and which only change screening priority?"
- "When should a person monitor, make an appointment, or seek urgent care?"

Avoid articles that try to cover mechanism, symptoms, diagnosis, treatment, diet, and psychology all at once unless the user explicitly asks for a broad overview.

### 4. Build a source pack

For every article, gather enough evidence before writing. Do not invent citations. Use web search or local provided references when the topic is medical, current, statistical, guideline-based, or high-stakes.

Source hierarchy:

| Priority | Source type | Examples |
|---|---|---|
| 1 | Current clinical guidelines and expert consensus | NCCN, ESMO, ACG, AGA, ADA, ACC/AHA, CSCO, Chinese Medical Association |
| 2 | Government and international agencies | WHO, IARC, CDC, NCI, NIH, FDA, EMA |
| 3 | Peer-reviewed reviews, systematic reviews, major clinical studies | PubMed, Cochrane, NEJM, Lancet, JAMA, BMJ, Gut, Gastroenterology |
| 4 | Epidemiology databases | GLOBOCAN, SEER, IHME, national cancer registries |
| 5 | Patient-facing pages from authoritative medical institutions | NCI PDQ, Cancer Research UK, Mayo Clinic, NHS, specialty society patient pages |

Minimum source rule:

- 3 sources for a short article.
- 4-6 sources for a standard article.
- At least 1 guideline/consensus or major institutional source when giving screening, diagnosis, prevention, or treatment-pathway advice.
- At least 1 epidemiology database when using incidence, mortality, survival, or population burden statistics.

Every source note should capture:

- Article/report/page title
- Journal or institution
- Year
- DOI, PubMed URL, original full-text URL, or database URL
- The specific claims it supports

If sources conflict, say what differs and prefer the newest, most local, most guideline-level source for practical advice.

### 5. Draft in a patient-friendly structure

Use this default Markdown structure unless the examples clearly use another one:

```markdown
# [Clear article title]

> 适用模块：[module]
> 更新日期：[YYYY-MM-DD]
> 内容定位：[one-sentence promise]
> 提醒：本文用于健康科普，不能替代医生诊断和个体化治疗建议。

## 先说结论

[3-5 plain-language conclusions. Put the highest-value decision information first.]

## [Explain the concept in plain language]

[Use a concrete metaphor only if it makes the mechanism clearer.]

## [Who is affected / who is higher risk / what changes the decision]

[Separate common situations from high-risk situations.]

## [What to do next]

[Give practical, low-risk next steps: test, appointment, follow-up, lifestyle risk reduction, report questions.]

## 需要尽快就医的情况

[Use when relevant. Distinguish alarm signs from routine screening.]

## 参考来源

- [Source list with title, journal/institution, year, DOI/link.]
```

For risk assessment articles, add a simple table when it improves scanning:

```markdown
| 风险层级 | 常见情况 | 建议 |
|---|---|---|
| 普通风险 | ... | ... |
| 风险升高 | ... | ... |
| 高风险 | ... | ... |
```

### 6. Write with medical safety boundaries

Required writing rules:

- Use "risk increases", "should consider", "discuss with a clinician", and "may need evaluation" when evidence is probabilistic.
- Do not say a symptom, test result, gene, infection, or biomarker "means cancer" or "proves no cancer" unless the cited guideline supports that exact claim.
- Do not provide personalized drug regimens, antibiotic combinations, chemotherapy regimens, or stop/start medication instructions unless the task is explicitly about general guideline education and the wording stays non-prescriptive.
- Separate screening from diagnosis. Screening identifies risk; diagnosis requires clinical evaluation.
- Separate population advice from individual advice. A guideline recommendation is not automatically the right choice for every person.
- Include urgent-care language for red flags: severe bleeding, chest pain, stroke-like symptoms, severe breathing difficulty, persistent vomiting, black stool, unexplained major weight loss, severe dehydration, or other disease-specific alarm signs.
- Avoid miracle cures, detox language, anti-medical framing, and fear-based hooks.

### 7. Final source and quality pass

Before saving or delivering, check the article like an editor:

- Does the title match the actual content?
- Does the "先说结论" section answer the reader's main question quickly?
- Are high-risk groups and ordinary-risk groups separated?
- Are screening, diagnosis, prevention, and treatment not mixed together?
- Are all numeric thresholds, screening ages, survival rates, and medical claims source-backed?
- Does every citation include title, journal/institution, year, and DOI/link where available?
- Is the article readable without medical training?
- Does it avoid both false reassurance and unnecessary panic?
- If writing multiple articles, do they avoid repeating the same opening and the same reference list mechanically?

## Article Patterns

### Basic cognition

Use for "what is this disease", "how it develops", "why early symptoms are vague", or "what the report wording means." Focus on mechanism, plain-language metaphor, and what the concept changes in real life.

### Risk assessment

Use for "who is high risk", "family history", "infection", "lifestyle risks", "occupational exposure", "age and sex differences", or "when to screen." Focus on risk stacking and next-step triage.

### Screening and early detection

Use for "which test to choose", "what a test can and cannot do", "how often to follow up", or "what abnormal results mean." Focus on test purpose, limitations, and referral logic.

### Myth correction

Use for misinformation-heavy topics. Structure each myth as: claim, why it is wrong or incomplete, what the evidence says, what to do instead.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "This is just popular science, citations can be loose." | Health content changes behavior. Every claim that affects screening, medication, diagnosis, or risk perception needs a traceable source. |
| "I know this from memory." | Medical guidance changes. Verify current guidelines and dates before writing. |
| "The article sounds good, so it is good enough." | A fluent article can still be unsafe, outdated, or misleading. Run the safety and source pass. |
| "One source is enough." | One source can be narrow or outdated. Use guidelines plus supporting literature or databases. |
| "Readers want certainty." | Medical risk is probabilistic. Overstating certainty creates harm. |
| "A tumor marker/test/result is easy to explain as yes/no." | Most screening and lab tests have false positives and false negatives. Explain limits clearly. |
| "The user only named one topic, so one article is enough." | 小鲸文章 is a batch-writing skill. Unless the user asks for fewer, create at least 5 `.md` articles with distinct angles. |
| "No path was provided, so I can save anywhere." | The default corpus root is `/Users/hua/Documents/基础知识`. Search it, reuse matching structure, or create the needed topic directory there. |

## Red Flags

- No source list, dead links, missing years, or citations that do not support the claims.
- Statistics without country, year, population, or database.
- Article starts with fear instead of useful orientation.
- Same generic paragraph reused across multiple disease articles.
- Fewer than 5 articles created when the user did not explicitly ask for fewer.
- Files saved outside `/Users/hua/Documents/基础知识` without an explicit user-provided path.
- A new directory name ignores existing nearby naming conventions.
- Patient advice sounds like a prescription or individualized diagnosis.
- Screening recommendations are copied from one country without noting local context.
- Tumor markers, genetic variants, imaging findings, or symptoms are described as definitive proof without qualification.
- The article is organized around medical jargon instead of reader decisions.

## Verification

Before considering the article complete, confirm:

- [ ] The topic, module, audience, language, and output path match the user request.
- [ ] At least 5 `.md` articles were produced unless the user explicitly requested fewer.
- [ ] The output directory was selected by first searching `/Users/hua/Documents/基础知识`, reusing a suitable existing path when available, or creating the correct disease/topic directory when absent.
- [ ] Current authoritative sources were checked for medical, guideline, statistical, or high-stakes claims.
- [ ] The article includes an update date and a medical education disclaimer.
- [ ] The article has a clear "先说结论" or equivalent summary.
- [ ] Practical next steps are specific but not personalized medical orders.
- [ ] Alarm signs are included when relevant.
- [ ] Every reference lists article/report/page title, journal or institution, year, and DOI/link where available.
- [ ] The article is readable for non-specialists and avoids unnecessary fear.
- [ ] The saved filename is descriptive and consistent with nearby examples.
- [ ] The final response lists every saved Markdown file path.
