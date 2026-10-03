const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function handle(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchStaffNames() {
  const res = await fetch(`${API_BASE}/api/staff-names`);
  return handle(res);
}

export async function fetchCandidates(createdBy) {
  const url = createdBy
    ? `${API_BASE}/api/candidates?created_by=${encodeURIComponent(createdBy)}`
    : `${API_BASE}/api/candidates`;
  const res = await fetch(url);
  return handle(res);
}

export async function extractCandidate({ resumeFile, jdText, jdImageFile }) {
  const formData = new FormData();
  formData.append("resume_file", resumeFile);
  if (jdImageFile) {
    formData.append("jd_image", jdImageFile);
  } else {
    formData.append("jd_text", jdText);
  }
  const res = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    body: formData,
  });
  return handle(res);
}

export async function saveCandidate({ createdBy, extractedFields, jdData, resumeFile }) {
  const formData = new FormData();
  formData.append("created_by", createdBy);
  formData.append("extracted_fields_json", JSON.stringify(extractedFields));
  formData.append("jd_data_json", JSON.stringify(jdData));
  formData.append("resume_file", resumeFile);
  const res = await fetch(`${API_BASE}/api/candidates`, {
    method: "POST",
    body: formData,
  });
  return handle(res);
}

export async function fetchCandidate(candidateId) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}`);
  return handle(res);
}

export async function generateContent(candidateId) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/generate`, {
    method: "POST",
  });
  return handle(res);
}

export async function regenerateSection(candidateId, company, customInstruction) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/regenerate-section`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company, custom_instruction: customInstruction || null }),
  });
  return handle(res);
}

export async function regenerateSkills(candidateId, customInstruction) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/regenerate-skills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ custom_instruction: customInstruction || null }),
  });
  return handle(res);
}

export async function regenerateCareerObjective(candidateId, customInstruction) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/regenerate-career-objective`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ custom_instruction: customInstruction || null }),
  });
  return handle(res);
}

export async function saveResumeContent(candidateId, { extractedFields, generatedContent }) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/resume-content`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extracted_fields: extractedFields, generated_content: generatedContent }),
  });
  return handle(res);
}

export async function fetchTemplates() {
  const res = await fetch(`${API_BASE}/api/templates`);
  return handle(res);
}

export async function saveFormatSettings(candidateId, formatSettings) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/format`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formatSettings),
  });
  return handle(res);
}

export async function checkAtsScore(candidateId) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/ats-score`, { method: "POST" });
  return handle(res);
}

async function handleBlob(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // not JSON
    }
    throw new Error(detail);
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="(.+)"/);
  const filename = match ? match[1] : "resume";
  const blob = await response.blob();
  return { blob, filename };
}

export async function exportPdf(candidateId) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/export/pdf`, { method: "POST" });
  return handleBlob(res);
}

export async function exportDocx(candidateId) {
  const res = await fetch(`${API_BASE}/api/candidates/${candidateId}/export/docx`, { method: "POST" });
  return handleBlob(res);
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
