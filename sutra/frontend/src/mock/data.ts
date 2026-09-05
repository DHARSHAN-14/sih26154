/**
 * mock/data.ts
 * Complete NTRO-themed demo dataset for UI demonstration.
 * This is UI presentation data only — not fake AI output.
 * All text is fictional and created for demonstration purposes.
 */
import type {
  Session, Source, SourceOfTruth, OutputConfig, Job,
  Artifact, SessionVersion, PipelineStageInfo,
} from "@/types";

// ─── IDs ──────────────────────────────────────────────────────────────────────
export const DEMO = {
  SESSION_ID:  "sess-ntro-2026-sih154-demo",
  SOURCE_ID:   "src-apt-assessment-q3-2026",
  SOT_ID:      "sot-apt-assessment-q3-2026",
  JOB_ID:      "job-001-pipeline-complete",
  CFG_PRESS:   "cfg-press-release-en",
  CFG_INTEL:   "cfg-intel-summary-en",
  CFG_BULLETIN:"cfg-op-bulletin-hi",
  ART_PRESS:   "art-press-release-final",
  ART_INTEL:   "art-intel-summary-final",
  ART_BULLETIN:"art-op-bulletin-final",
};

// ─── Source ───────────────────────────────────────────────────────────────────
export const MOCK_SOURCE: Source = {
  id:          DEMO.SOURCE_ID,
  name:        "APT_ASSESSMENT_CRITICAL_INFRA_Q3_2026_DRAFT.pdf",
  type:        "document",
  mimeType:    "application/pdf",
  sizeBytes:   2_847_392,
  uploadedAt:  "2026-09-05T04:00:00.000Z",
  checksum:    "sha256:4a7f3b2d9e1c8f5a0b6d4e2f7a9c3b1d8e4f2a6c",
  language:    "en",
  pageCount:   24,
};

// ─── Source of Truth ──────────────────────────────────────────────────────────
export const MOCK_SOT: SourceOfTruth = {
  id:        DEMO.SOT_ID,
  sourceId:  DEMO.SOURCE_ID,
  status:    "locked",
  createdAt: "2026-09-05T04:02:15.000Z",
  lockedAt:  "2026-09-05T04:05:30.000Z",
  lockedBy:  "operator-001",
  language:  "en",
  wordCount: 8432,
  summary:
    "Advanced Persistent Threat group APT-X41, attributed with high confidence to a state-sponsored actor operating from Southeast Asia, conducted a sustained cyber operation (Operation Blackout) targeting India's critical infrastructure during Q3 2026. The operation resulted in the compromise of 47 industrial control systems belonging to the National Power Grid Corporation (NPGC), with an estimated 2.3 TB of operational telemetry data exfiltrated. The primary attack vector was spear-phishing leading to exploitation of CVE-2026-7381, a zero-day in widely-deployed SCADA middleware. CERT-In has been coordinating national incident response since 12 July 2026. Attribution confidence: HIGH.",
  rawText:
    "CLASSIFIED THREAT ASSESSMENT — CRITICAL INFRASTRUCTURE\nQ3 2026 | RESTRICTED DISTRIBUTION\n\nEXECUTIVE SUMMARY\nThreat Actor APT-X41, operating under the codename Operation Blackout, has conducted a sustained and sophisticated cyber campaign targeting India's critical infrastructure sector between July and September 2026. Analysis of indicators of compromise, malware signatures, and command-and-control infrastructure has enabled attribution to a state-sponsored group based in Southeast Asia with HIGH confidence.\n\nKEY FINDINGS\n1. 47 industrial control systems belonging to the National Power Grid Corporation (NPGC) were compromised across the Mumbai Metropolitan Region and Delhi NCT.\n2. Estimated 2.3 TB of operational data, including SCADA configuration files and network topology maps, was exfiltrated over 11 weeks.\n3. The primary entry vector was a spear-phishing campaign exploiting CVE-2026-7381, a zero-day vulnerability in SCADA middleware deployed across critical utilities.\n4. Cobalt Strike beacons were identified on 23 compromised hosts, with lateral movement achieved through credential harvesting and pass-the-hash techniques.\n5. CERT-In was notified on 15 July 2026 and has been coordinating national incident response.\n\nTHREAT ACTOR PROFILE\nDesignation: APT-X41 (also tracked as 'Shadow Grid' by international partners)\nSponsorship: State-sponsored, Southeast Asia\nCapability: Tier-1 (Nation-state level)\nTTPs: Spear-phishing, zero-day exploitation, living-off-the-land, long-dwell persistence\nOperation Name: Operation Blackout\n\nIMPACT ASSESSMENT\nOperational disruption risk: HIGH\nData sensitivity of exfiltrated material: CRITICAL\nPotential for follow-on destructive attack: MEDIUM-HIGH\n\nRECOMMENDATIONS\n1. Immediate patching of CVE-2026-7381 across all SCADA deployments.\n2. Network segmentation of OT/IT interfaces at all critical infrastructure facilities.\n3. Enhanced monitoring for Cobalt Strike indicators.\n4. Mandatory credential rotation for all NPGC system administrators.",
  entities: [
    { id: "ent-01", text: "APT-X41",                     type: "organization", confidence: 0.97, sourceRef: { page: 2, paragraph: 1 }, normalized: "APT-X41 Threat Group" },
    { id: "ent-02", text: "Operation Blackout",           type: "event",        confidence: 0.95, sourceRef: { page: 2, paragraph: 1 } },
    { id: "ent-03", text: "National Power Grid Corporation", type: "organization", confidence: 0.99, sourceRef: { page: 2, paragraph: 2 }, normalized: "NPGC" },
    { id: "ent-04", text: "CERT-In",                      type: "organization", confidence: 0.99, sourceRef: { page: 3, paragraph: 5 }, normalized: "Computer Emergency Response Team India" },
    { id: "ent-05", text: "Ministry of Electronics and IT", type: "organization", confidence: 0.93, sourceRef: { page: 1, paragraph: 1 }, normalized: "MeitY" },
    { id: "ent-06", text: "Shadow Grid",                  type: "organization", confidence: 0.88, sourceRef: { page: 4, paragraph: 1 } },
    { id: "ent-07", text: "Mumbai Metropolitan Region",   type: "location",     confidence: 0.99, sourceRef: { page: 3, paragraph: 2 } },
    { id: "ent-08", text: "Delhi NCT",                    type: "location",     confidence: 0.99, sourceRef: { page: 3, paragraph: 2 } },
    { id: "ent-09", text: "Southeast Asia",               type: "location",     confidence: 0.91, sourceRef: { page: 2, paragraph: 3 } },
    { id: "ent-10", text: "12 July 2026",                 type: "date",         confidence: 0.99, sourceRef: { page: 3, paragraph: 5 } },
    { id: "ent-11", text: "Q3 2026",                      type: "date",         confidence: 0.98, sourceRef: { page: 1, paragraph: 1 } },
    { id: "ent-12", text: "CVE-2026-7381",               type: "technical",    confidence: 0.99, sourceRef: { page: 3, paragraph: 3 }, normalized: "Zero-day SCADA middleware vulnerability" },
    { id: "ent-13", text: "Cobalt Strike",                type: "technical",    confidence: 0.97, sourceRef: { page: 3, paragraph: 4 } },
    { id: "ent-14", text: "SCADA Systems",               type: "technical",    confidence: 0.96, sourceRef: { page: 2, paragraph: 2 } },
    { id: "ent-15", text: "47 industrial control systems", type: "numeric",      confidence: 0.99, sourceRef: { page: 2, paragraph: 2 } },
    { id: "ent-16", text: "2.3 TB exfiltrated data",     type: "numeric",      confidence: 0.98, sourceRef: { page: 2, paragraph: 2 } },
    { id: "ent-17", text: "state-sponsored actor",       type: "claim",        confidence: 0.94, sourceRef: { page: 1, paragraph: 2 } },
    { id: "ent-18", text: "HIGH attribution confidence", type: "fact",         confidence: 0.96, sourceRef: { page: 1, paragraph: 2 } },
  ],
  relations: [
    { id: "rel-01", fromId: "ent-01", toId: "ent-03", label: "targeted",       confidence: 0.97 },
    { id: "rel-02", fromId: "ent-01", toId: "ent-12", label: "exploited",      confidence: 0.95 },
    { id: "rel-03", fromId: "ent-01", toId: "ent-13", label: "deployed",       confidence: 0.94 },
    { id: "rel-04", fromId: "ent-02", toId: "ent-01", label: "conducted_by",   confidence: 0.98 },
    { id: "rel-05", fromId: "ent-04", toId: "ent-02", label: "responded_to",   confidence: 0.99 },
    { id: "rel-06", fromId: "ent-01", toId: "ent-09", label: "originates_from",confidence: 0.91 },
    { id: "rel-07", fromId: "ent-02", toId: "ent-07", label: "targeted",       confidence: 0.97 },
    { id: "rel-08", fromId: "ent-02", toId: "ent-08", label: "targeted",       confidence: 0.95 },
    { id: "rel-09", fromId: "ent-12", toId: "ent-14", label: "affects",        confidence: 0.99 },
    { id: "rel-10", fromId: "ent-01", toId: "ent-06", label: "also_known_as",  confidence: 0.88 },
  ],
};

// ─── Output Configs ───────────────────────────────────────────────────────────
export const MOCK_OUTPUT_CONFIGS: OutputConfig[] = [
  {
    id:           DEMO.CFG_PRESS,
    type:         "press_release",
    templateId:   "press_release_default",
    language:     "en",
    tone:         "formal",
    classification: "unclassified",
    model:        "gpt-4o",
    maxTokens:    800,
    enabled:      true,
    detailLevel:  "standard",
    objective:    "inform",
    audience:     "media",
    style:        "narrative",
  },
  {
    id:           DEMO.CFG_INTEL,
    type:         "intelligence_summary",
    templateId:   "intel_summary_default",
    language:     "en",
    tone:         "analytical",
    classification: "secret",
    model:        "claude-3-5-sonnet",
    maxTokens:    1500,
    enabled:      true,
    detailLevel:  "comprehensive",
    objective:    "brief",
    audience:     "executive",
    style:        "mixed",
  },
  {
    id:           DEMO.CFG_BULLETIN,
    type:         "operational_bulletin",
    templateId:   "op_bulletin_default",
    language:     "hi",
    tone:         "urgent",
    classification: "restricted",
    model:        "gemini-1.5-pro",
    maxTokens:    500,
    enabled:      true,
    detailLevel:  "brief",
    objective:    "alert",
    audience:     "field_operator",
    style:        "bullet_points",
  },
];

// ─── Pipeline Stages (all complete) ───────────────────────────────────────────
export const MOCK_STAGES: PipelineStageInfo[] = [
  { id: "upload",           label: "Source Upload",            description: "Source material received and stored",                  status: "done", durationMs: 1240,  startedAt: "2026-09-05T04:06:00Z", completedAt: "2026-09-05T04:06:01Z", progress: 100 },
  { id: "multimodal",       label: "Multimodal Understanding",  description: "Document type detection and modal parsing",           status: "done", durationMs: 3820,  startedAt: "2026-09-05T04:06:01Z", completedAt: "2026-09-05T04:06:05Z", progress: 100 },
  { id: "ocr_asr_nlp",      label: "OCR / ASR / NLP",          description: "Text extraction from images, audio, and documents",   status: "done", durationMs: 8430,  startedAt: "2026-09-05T04:06:05Z", completedAt: "2026-09-05T04:06:13Z", progress: 100 },
  { id: "rag_kg",           label: "RAG + Knowledge Graph",     description: "Entity indexing and graph construction",              status: "done", durationMs: 12700, startedAt: "2026-09-05T04:06:13Z", completedAt: "2026-09-05T04:06:26Z", progress: 100 },
  { id: "sot_build",        label: "Build Source of Truth",     description: "Verified entity and claim extraction",                status: "done", durationMs: 9100,  startedAt: "2026-09-05T04:06:26Z", completedAt: "2026-09-05T04:06:35Z", progress: 100 },
  { id: "sot_lock",         label: "SOT Lock",                  description: "Source of truth sealed for generation",               status: "done", durationMs: 520,   startedAt: "2026-09-05T04:06:35Z", completedAt: "2026-09-05T04:06:36Z", progress: 100 },
  { id: "planner",          label: "Output Planner",            description: "Generate output plan from SOT and configs",           status: "done", durationMs: 4200,  startedAt: "2026-09-05T04:06:36Z", completedAt: "2026-09-05T04:06:40Z", progress: 100 },
  { id: "template",         label: "Template Contracts",        description: "Template resolution and token binding",               status: "done", durationMs: 2100,  startedAt: "2026-09-05T04:06:40Z", completedAt: "2026-09-05T04:06:42Z", progress: 100 },
  { id: "generation",       label: "LLM Generation",            description: "Content generated per output configuration",          status: "done", durationMs: 42800, startedAt: "2026-09-05T04:06:42Z", completedAt: "2026-09-05T04:07:25Z", progress: 100 },
  { id: "validation",       label: "Fact Consistency",          description: "Cross-referencing generated content against SOT",     status: "done", durationMs: 7600,  startedAt: "2026-09-05T04:07:25Z", completedAt: "2026-09-05T04:07:33Z", progress: 100 },
  { id: "rendering",        label: "Rendering",                 description: "Format conversion and layout application",            status: "done", durationMs: 5300,  startedAt: "2026-09-05T04:07:33Z", completedAt: "2026-09-05T04:07:38Z", progress: 100 },
  { id: "visual_validation", label: "Visual Validation",        description: "Layout integrity and format compliance checks",       status: "done", durationMs: 3200,  startedAt: "2026-09-05T04:07:38Z", completedAt: "2026-09-05T04:07:42Z", progress: 100 },
  { id: "artifacts",        label: "Final Artefacts",           description: "Artefacts packaged with provenance metadata",         status: "done", durationMs: 1800,  startedAt: "2026-09-05T04:07:42Z", completedAt: "2026-09-05T04:07:44Z", progress: 100 },
];

// ─── Job ──────────────────────────────────────────────────────────────────────
export const MOCK_JOB: Job = {
  id:             DEMO.JOB_ID,
  sessionId:      DEMO.SESSION_ID,
  status:         "completed",
  createdAt:      "2026-09-05T04:06:00.000Z",
  startedAt:      "2026-09-05T04:06:00.000Z",
  completedAt:    "2026-09-05T04:07:44.000Z",
  stages:         MOCK_STAGES,
  outputCount:    3,
  outputConfigIds:[DEMO.CFG_PRESS, DEMO.CFG_INTEL, DEMO.CFG_BULLETIN],
  progress:       100,
};

// ─── Artifacts ────────────────────────────────────────────────────────────────
export const MOCK_ARTIFACTS: Artifact[] = [
  {
    id:             DEMO.ART_PRESS,
    jobId:          DEMO.JOB_ID,
    outputConfigId: DEMO.CFG_PRESS,
    type:           "press_release",
    format:         "docx",
    title:          "CERT-In Issues Advisory on Critical Infrastructure Cyber Threats",
    classification: "unclassified",
    language:       "en",
    version:        1,
    sizeBytes:      187_432,
    createdAt:      "2026-09-05T04:07:44.000Z",
    downloadUrl:    "/api/outputs/art-press-release-final/download",
    previewText:    "NEW DELHI — The Indian Computer Emergency Response Team (CERT-In), under the Ministry of Electronics and Information Technology, has issued a high-priority cybersecurity advisory following the detection of a sophisticated threat campaign targeting critical infrastructure facilities across India.\n\nThe advisory, classified at UNCLASSIFIED level for public dissemination, warns operators of industrial control systems to immediately apply patches for a recently disclosed vulnerability. Organisations managing power generation and distribution assets are urged to conduct immediate security audits.\n\n\"India's digital infrastructure remains a high-value target for sophisticated adversaries. Prompt action by all stakeholders is essential to maintain operational continuity,\" said a CERT-In spokesperson.\n\nAffected organisations should review their network segmentation protocols and report any indicators of compromise to CERT-In at incident@cert-in.org.in.",
    validation: {
      factScore:        0.94,
      consistencyScore: 0.96,
      hallucination:    0.04,
      passed:           true,
      issues: [
        { id: "iss-01", severity: "info", claim: "CERT-In spokesperson quoted", expected: "Direct quote present", actual: "Paraphrased quote used", sourceRef: "Page 1, Para 3" },
      ],
    },
    visualValidation: {
      score:             0.97,
      passed:            true,
      layoutCompliant:   true,
      templateAdherence: true,
      fontCompliant:     true,
      imageQuality:      true,
      checks: [
        { id: "vc-01", label: "Header / footer placement",       passed: true },
        { id: "vc-02", label: "Font family compliance",          passed: true },
        { id: "vc-03", label: "Margin & padding specification",  passed: true },
        { id: "vc-04", label: "Classification marking placement", passed: true },
        { id: "vc-05", label: "Logo and branding compliance",    passed: false, detail: "Government logo resolution below 300 DPI threshold" },
      ],
    },
    provenance: [
      { id: "prov-01", claim: "CERT-In coordinates national incident response", sourceEntityId: "ent-04", sourceText: "CERT-In has been coordinating national incident response since 12 July 2026.", sourceRef: { page: 3, paragraph: 5 }, confidence: 0.99, verified: true },
      { id: "prov-02", claim: "Critical infrastructure targeted by sophisticated threat", sourceEntityId: "ent-01", sourceText: "APT-X41 conducted a sustained and sophisticated cyber campaign targeting India's critical infrastructure sector.", sourceRef: { page: 1, paragraph: 1 }, confidence: 0.97, verified: true },
      { id: "prov-03", claim: "CVE-2026-7381 vulnerability exploited", sourceEntityId: "ent-12", sourceText: "spear-phishing campaign exploiting CVE-2026-7381, a zero-day vulnerability in SCADA middleware.", sourceRef: { page: 3, paragraph: 3 }, confidence: 0.99, verified: true },
    ],
  },
  {
    id:             DEMO.ART_INTEL,
    jobId:          DEMO.JOB_ID,
    outputConfigId: DEMO.CFG_INTEL,
    type:           "intelligence_summary",
    format:         "pdf",
    title:          "INTELLIGENCE ASSESSMENT: APT-X41 Operation Blackout — Attribution and Impact Report",
    classification: "secret",
    language:       "en",
    version:        1,
    sizeBytes:      542_871,
    createdAt:      "2026-09-05T04:07:44.000Z",
    downloadUrl:    "/api/outputs/art-intel-summary-final/download",
    previewText:    "[SECRET//NOFORN]\n\nINTELLIGENCE ASSESSMENT\nSubject: APT-X41 — Operation Blackout — Critical Infrastructure Targeting\nDate: 05 September 2026 | Classification: SECRET | Distribution: EYES ONLY\n\nKEY JUDGMENTS\n• APT-X41, a state-sponsored threat actor operating from Southeast Asia, conducted Operation Blackout against Indian critical infrastructure with HIGH CONFIDENCE attribution.\n• The operation compromised 47 ICS/SCADA systems within the National Power Grid Corporation, exfiltrating 2.3 TB of operational telemetry.\n• Exploitation of CVE-2026-7381 represents a significant capability escalation by APT-X41, indicating zero-day acquisition from external brokers or internal research.\n• The long dwell time (>11 weeks) before detection indicates sophisticated operational security and suggests pre-positioning for a potential follow-on destructive attack.\n• Cobalt Strike C2 infrastructure overlaps with previously attributed APT-X41 campaigns in other regions.\n\nATTRIBUTION CONFIDENCE: HIGH (multiple independent indicators corroborated).",
    validation: {
      factScore:        0.98,
      consistencyScore: 0.97,
      hallucination:    0.02,
      passed:           true,
      issues: [],
    },
    visualValidation: {
      score:             0.99,
      passed:            true,
      layoutCompliant:   true,
      templateAdherence: true,
      fontCompliant:     true,
      imageQuality:      true,
      checks: [
        { id: "vc-01", label: "SECRET classification banner",    passed: true },
        { id: "vc-02", label: "NOFORN caveat marking",          passed: true },
        { id: "vc-03", label: "Page numbering format",           passed: true },
        { id: "vc-04", label: "Redaction placeholder format",   passed: true },
        { id: "vc-05", label: "Template section structure",      passed: true },
      ],
    },
    provenance: [
      { id: "prov-04", claim: "HIGH CONFIDENCE attribution to APT-X41", sourceEntityId: "ent-18", sourceText: "Attribution to a state-sponsored group based in Southeast Asia with HIGH confidence.", sourceRef: { page: 1, paragraph: 2 }, confidence: 0.96, verified: true },
      { id: "prov-05", claim: "47 ICS/SCADA systems compromised", sourceEntityId: "ent-15", sourceText: "47 industrial control systems belonging to the National Power Grid Corporation (NPGC) were compromised.", sourceRef: { page: 2, paragraph: 2 }, confidence: 0.99, verified: true },
      { id: "prov-06", claim: "2.3 TB of operational data exfiltrated", sourceEntityId: "ent-16", sourceText: "Estimated 2.3 TB of operational data, including SCADA configuration files and network topology maps, was exfiltrated over 11 weeks.", sourceRef: { page: 2, paragraph: 2 }, confidence: 0.98, verified: true },
      { id: "prov-07", claim: "Cobalt Strike C2 infrastructure identified", sourceEntityId: "ent-13", sourceText: "Cobalt Strike beacons were identified on 23 compromised hosts.", sourceRef: { page: 3, paragraph: 4 }, confidence: 0.97, verified: true },
    ],
  },
  {
    id:             DEMO.ART_BULLETIN,
    jobId:          DEMO.JOB_ID,
    outputConfigId: DEMO.CFG_BULLETIN,
    type:           "operational_bulletin",
    format:         "pdf",
    title:          "परिचालन बुलेटिन: साइबर खतरा — राष्ट्रीय महत्वपूर्ण अवसंरचना",
    classification: "restricted",
    language:       "hi",
    version:        1,
    sizeBytes:      214_563,
    createdAt:      "2026-09-05T04:07:44.000Z",
    downloadUrl:    "/api/outputs/art-op-bulletin-final/download",
    previewText:    "[प्रतिबंधित]\n\nपरिचालन बुलेटिन — उच्च प्राथमिकता साइबर सुरक्षा चेतावनी\n\n• खतरा समूह APT-X41 ने राष्ट्रीय विद्युत वितरण नेटवर्क पर साइबर हमला किया है।\n• 47 औद्योगिक नियंत्रण प्रणालियाँ प्रभावित हुई हैं — मुंबई और दिल्ली क्षेत्र में।\n• CVE-2026-7381 भेद्यता का उपयोग हमले के प्राथमिक माध्यम के रूप में किया गया।\n• सभी SCADA ऑपरेटरों को तत्काल सुरक्षा पैच लागू करने के निर्देश दिए जाते हैं।\n• किसी भी संदिग्ध गतिविधि की सूचना तुरंत CERT-In को दें: incident@cert-in.org.in\n\nकार्रवाई की आवश्यकता: तत्काल",
    validation: {
      factScore:        0.91,
      consistencyScore: 0.93,
      hallucination:    0.07,
      passed:           true,
      issues: [
        { id: "iss-02", severity: "warning", claim: "मुंबई क्षेत्र में 47 प्रणालियाँ", expected: "मुंबई और दिल्ली दोनों में संयुक्त 47", actual: "केवल मुंबई का उल्लेख", sourceRef: "SOT Entity ent-15" },
      ],
    },
    visualValidation: {
      score:             0.94,
      passed:            true,
      layoutCompliant:   true,
      templateAdherence: true,
      fontCompliant:     true,
      imageQuality:      true,
      checks: [
        { id: "vc-01", label: "Devanagari font rendering",        passed: true },
        { id: "vc-02", label: "RESTRICTED classification banner", passed: true },
        { id: "vc-03", label: "Bullet point alignment",           passed: true },
        { id: "vc-04", label: "Hindi date format compliance",     passed: false, detail: "Date in English format; Hindi locale date format expected" },
        { id: "vc-05", label: "Government seal placement",        passed: true },
      ],
    },
    provenance: [
      { id: "prov-08", claim: "APT-X41 ने राष्ट्रीय विद्युत नेटवर्क को लक्षित किया", sourceEntityId: "ent-01", sourceText: "APT-X41 conducted a sustained and sophisticated cyber campaign targeting India's critical infrastructure sector.", sourceRef: { page: 1, paragraph: 1 }, confidence: 0.97, verified: true },
      { id: "prov-09", claim: "CERT-In को सूचित करें", sourceEntityId: "ent-04", sourceText: "CERT-In has been coordinating national incident response since 12 July 2026.", sourceRef: { page: 3, paragraph: 5 }, confidence: 0.99, verified: true },
      { id: "prov-10", claim: "CVE-2026-7381 पैच करें", sourceEntityId: "ent-12", sourceText: "spear-phishing campaign exploiting CVE-2026-7381, a zero-day vulnerability in SCADA middleware.", sourceRef: { page: 3, paragraph: 3 }, confidence: 0.99, verified: true },
    ],
  },
];

// ─── Versions ─────────────────────────────────────────────────────────────────
export const MOCK_VERSIONS: SessionVersion[] = [
  {
    id:            "ver-003",
    sessionId:     DEMO.SESSION_ID,
    version:       3,
    createdAt:     "2026-09-05T04:07:44.000Z",
    createdBy:     "operator-001",
    sourceId:      DEMO.SOURCE_ID,
    sourceName:    "APT_ASSESSMENT_CRITICAL_INFRA_Q3_2026_DRAFT.pdf",
    artifactCount: 3,
    status:        "active",
    notes:         "Final generation — all 3 outputs complete. SOT locked at v3.",
  },
  {
    id:            "ver-002",
    sessionId:     DEMO.SESSION_ID,
    version:       2,
    createdAt:     "2026-09-05T03:30:00.000Z",
    createdBy:     "operator-001",
    sourceId:      DEMO.SOURCE_ID,
    sourceName:    "APT_ASSESSMENT_CRITICAL_INFRA_Q3_2026_DRAFT.pdf",
    artifactCount: 2,
    status:        "archived",
    notes:         "Partial run — Hindi bulletin excluded. Re-run required.",
  },
  {
    id:            "ver-001",
    sessionId:     DEMO.SESSION_ID,
    version:       1,
    createdAt:     "2026-09-05T02:15:00.000Z",
    createdBy:     "operator-001",
    sourceId:      DEMO.SOURCE_ID,
    sourceName:    "APT_ASSESSMENT_Q3_2026_INITIAL.pdf",
    artifactCount: 1,
    status:        "archived",
    notes:         "Initial draft — source document replaced with final version.",
  },
];

// ─── Full Demo Session ─────────────────────────────────────────────────────────
export const MOCK_SESSION: Session = {
  id:           DEMO.SESSION_ID,
  createdAt:    "2026-09-05T04:00:00.000Z",
  updatedAt:    "2026-09-05T04:07:44.000Z",
  operatorId:   "operator-001",
  classification: "restricted",
  source:       MOCK_SOURCE,
  sot:          MOCK_SOT,
  outputConfigs: MOCK_OUTPUT_CONFIGS,
  jobs:         [MOCK_JOB],
  artifacts:    MOCK_ARTIFACTS,
  currentStage: "results",
};
