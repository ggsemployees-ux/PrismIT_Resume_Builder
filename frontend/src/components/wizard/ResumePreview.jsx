import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";
import { usePagedBlocks, PAGE_WIDTH, PAGE_HEIGHT, PAGE_PADDING, CONTENT_WIDTH } from "../../utils/pagination";
import { renderRichText } from "../../utils/richText.jsx";
import "./ResumePreview.css";

// Mirrors backend/app/templates.py -- kept in sync manually since the two
// are different languages, but describe the same 4 templates.
export const TEMPLATE_THEMES = {
  classic: { accentColor: "#0b1220", titleStyle: "underline", density: "normal", layout: "single" },
  modern: { accentColor: "#2f96da", titleStyle: "accent-bar", density: "normal", layout: "single" },
  sidebar: { accentColor: "#1c2740", titleStyle: "underline", density: "normal", layout: "sidebar" },
  compact: { accentColor: "#0b1220", titleStyle: "underline", density: "compact", layout: "single" },
};

// Fixed size hierarchy, expressed as ratios against the body-text size --
// mirrors FONT_SIZE_RATIOS in backend/app/templates.py exactly, so the
// preview and the exported PDF/DOCX stay visually consistent. The
// font-size control the user sees sets the BODY size; everything else
// scales proportionally around it.
const FONT_SIZE_RATIOS = {
  name: 20 / 12,
  contact: 14 / 12,
  heading: 14 / 12,
  body: 1,
};

const SIDEBAR_WIDTH_PX = 220;

function formatDateRange(start, end, isCurrent) {
  const endLabel = isCurrent ? "Present" : end || "—";
  return `${start || "—"} – ${endLabel}`;
}

function isResumeEmpty(data) {
  return (
    !data.personal_info?.full_name &&
    (!data.work_experience || data.work_experience.length === 0) &&
    (!data.skill_categories || data.skill_categories.length === 0) &&
    (!data.education || data.education.length === 0)
  );
}

const GHOST_DATA = {
  personal_info: {
    full_name: "Your Name",
    mobile: "+91 00000 00000",
    email: "your.email@example.com",
    location: "City, State",
  },
  career_objective:
    "A short, JD-tailored career objective will appear here once content is generated, making the case for why this candidate fits the target role.",
  skill_categories: [
    { category: "Category One", skills: ["Skill A", "Skill B", "Skill C"] },
    { category: "Category Two", skills: ["Skill D", "Skill E"] },
  ],
  work_experience: [
    {
      company: "Company Name",
      generated_job_title: "Job Title",
      start_date: "Jan 2020",
      end_date: "Present",
      is_current: true,
      responsibilities: [
        "This is where a generated responsibility bullet will appear.",
        "Another responsibility bullet will show up here, with project-level detail folded directly in.",
      ],
    },
  ],
  education: [{ degree: "Degree Name", institution: "Institution Name", start_date: "2016", end_date: "2020" }],
  certifications: [],
  languages_known: [],
};

function buildHeaderNode(resumeData) {
  const p = resumeData.personal_info || {};
  const contactLine = [p.mobile, p.email, p.location, p.linkedin_url, p.portfolio_url].filter(Boolean).join("   •   ");
  return (
    <div className="pv-header">
      <h1>{p.full_name || "—"}</h1>
      <p className="pv-contact">{contactLine}</p>
    </div>
  );
}

function buildSkillsNodes(resumeData, push) {
  if (!resumeData.skill_categories?.length) return;
  push("skills-title", "skills", <div className="pv-section-title">Core Technical Skills</div>, "skills-title");
  resumeData.skill_categories.forEach((cat, i) => {
    push(
      `skills-cat-${i}`,
      "skills",
      <div className="pv-skill-category">
        <strong>{cat.category}:</strong> {cat.skills.join(", ")}
      </div>,
      `${cat.category}${cat.skills.join(",")}`
    );
  });
}

function buildEducationNodes(resumeData, push) {
  if (!resumeData.education?.length) return;
  push("edu-title", "education", <div className="pv-section-title">Education</div>, "edu-title");
  resumeData.education.forEach((edu, i) => {
    push(
      `edu-${i}`,
      "education",
      <div className="pv-edu">
        <div className="pv-edu__top">
          <strong>{edu.degree}</strong>
          <span className="pv-job-dates">{formatDateRange(edu.start_date, edu.end_date, false)}</span>
        </div>
        <div className="pv-job-company">{edu.institution}</div>
      </div>,
      `${edu.degree}${edu.institution}${edu.start_date}${edu.end_date}`
    );
  });
}

function buildInlineListNodes(title, sectionKey, items, push) {
  if (!items?.length) return;
  push(`${sectionKey}-title`, sectionKey, <div className="pv-section-title">{title}</div>, `${sectionKey}-title`);
  push(`${sectionKey}-body`, sectionKey, <div className="pv-inline-list">{items.join("  •  ")}</div>, items.join(","));
}

/** Company bold and first, date range on the same line (right-aligned); job
 * title secondary underneath -- per the requested layout swap. No separate
 * projects section -- project-level detail lives inside the bullets. A
 * spacer block is inserted between companies (but not after the last one)
 * for visual separation. */
function buildExperienceNodes(resumeData, push) {
  if (!resumeData.work_experience?.length) return;
  push("exp-title", "experience", <div className="pv-section-title">Professional Experience</div>, "exp-title");
  const jobs = resumeData.work_experience;
  jobs.forEach((job, jobIndex) => {
    const sectionKey = `experience-${job.company}`;
    push(
      `job-header-${jobIndex}`,
      sectionKey,
      <div className="pv-job-header">
        <div className="pv-job-header__top">
          <strong className="pv-job-company-name">{job.company || "—"}</strong>
          <span className="pv-job-dates">{formatDateRange(job.start_date, job.end_date, job.is_current)}</span>
        </div>
        <div className="pv-job-title">{job.generated_job_title || job.job_title || ""}</div>
      </div>,
      `${job.company}${job.start_date}${job.end_date}`
    );
    (job.responsibilities || []).forEach((resp, i) => {
      push(
        `resp-${jobIndex}-${i}`,
        sectionKey,
        <div className="pv-bullet">
          <span>•</span>
          <p>{renderRichText(resp)}</p>
        </div>,
        resp
      );
    });
    if (jobIndex < jobs.length - 1) {
      push(`company-gap-${jobIndex}`, sectionKey, <div className="pv-company-gap" />, "gap");
    }
  });
}

/** Non-sidebar templates: everything is one flowing, paginated block list. */
function buildFlowBlocks(resumeData) {
  const blocks = [];
  const push = (id, section, node, measureKey) => blocks.push({ id, section, node, measureKey });

  push("header", "personal", buildHeaderNode(resumeData), (resumeData.personal_info?.full_name || "") + "h");
  if (resumeData.career_objective) {
    push("objective-title", "career_objective", <div className="pv-section-title">Career Objective</div>, "objective-title");
    push("career-objective", "career_objective", <div className="pv-objective">{renderRichText(resumeData.career_objective)}</div>, resumeData.career_objective);
  }
  buildSkillsNodes(resumeData, push);
  buildExperienceNodes(resumeData, push);
  buildEducationNodes(resumeData, push);
  buildInlineListNodes("Certifications", "certifications", resumeData.certifications, push);
  buildInlineListNodes("Languages", "languages", resumeData.languages_known, push);
  return blocks;
}

/** Sidebar template: header/skills/education/certs/languages render once as
 * a static (unpaginated) sidebar repeated on every page; only career
 * objective + experience actually paginate, in the narrower main column. */
function buildSidebarStaticNode(resumeData) {
  const blocks = [];
  const push = (id, section, node) => blocks.push({ id, node });
  push("header", "personal", buildHeaderNode(resumeData));
  buildSkillsNodes(resumeData, push);
  buildEducationNodes(resumeData, push);
  buildInlineListNodes("Certifications", "certifications", resumeData.certifications, push);
  buildInlineListNodes("Languages", "languages", resumeData.languages_known, push);
  return blocks;
}

function buildMainFlowBlocks(resumeData) {
  const blocks = [];
  const push = (id, section, node, measureKey) => blocks.push({ id, section, node, measureKey });
  if (resumeData.career_objective) {
    push("objective-title", "career_objective", <div className="pv-section-title">Career Objective</div>, "objective-title");
    push("career-objective", "career_objective", <div className="pv-objective">{renderRichText(resumeData.career_objective)}</div>, resumeData.career_objective);
  }
  buildExperienceNodes(resumeData, push);
  return blocks;
}

const ResumePreview = forwardRef(function ResumePreview(
  { resumeData, zoom, templateId = "classic", fontFamily = "Arial", fontSizePt = 12, boldHeaders = true },
  ref
) {
  const empty = isResumeEmpty(resumeData);
  const effectiveData = empty ? GHOST_DATA : resumeData;
  const theme = TEMPLATE_THEMES[templateId] || TEMPLATE_THEMES.classic;
  const isSidebar = theme.layout === "sidebar";

  const flowBlocks = useMemo(
    () => (isSidebar ? buildMainFlowBlocks(effectiveData) : buildFlowBlocks(effectiveData)),
    [effectiveData, isSidebar]
  );
  const sidebarStaticBlocks = useMemo(() => (isSidebar ? buildSidebarStaticNode(effectiveData) : []), [effectiveData, isSidebar]);

  const measureWidth = isSidebar ? CONTENT_WIDTH - SIDEBAR_WIDTH_PX : CONTENT_WIDTH;
  const { pages, overflowBlockIds, ready, setMeasureRef } = usePagedBlocks(flowBlocks);
  const blockNodeRefs = useRef(new Map());
  const sidebarNodeRef = useRef(null);

  useImperativeHandle(ref, () => ({
    scrollToSection(sectionKey) {
      const sidebarSections = ["personal", "skills", "education", "certifications", "languages"];
      if (isSidebar && sidebarSections.includes(sectionKey)) {
        sidebarNodeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      const block = flowBlocks.find((b) => b.section === sectionKey);
      if (!block) return;
      const node = blockNodeRefs.current.get(block.id);
      if (node) node.scrollIntoView({ behavior: "smooth", block: "center" });
    },
  }));

  const blockMap = useMemo(() => Object.fromEntries(flowBlocks.map((b) => [b.id, b])), [flowBlocks]);
  const scale = zoom / 100;

  const densityScale = theme.density === "compact" ? 0.8 : 1;

  // Functional font-size control: fontSizePt is the BODY size the user
  // sets; name/contact/heading sizes scale proportionally around it via
  // CSS variables consumed in ResumePreview.css, so changing the number
  // actually changes the rendered output (this replaces the old bug where
  // the control set an inline style nothing in CSS actually read).
  const pageStyle = {
    width: PAGE_WIDTH,
    height: PAGE_HEIGHT,
    padding: PAGE_PADDING,
    fontFamily,
    fontSize: `${fontSizePt}pt`,
    "--pv-accent": theme.accentColor,
    "--pv-title-style": theme.titleStyle,
    "--pv-density": densityScale,
    "--pv-title-weight": boldHeaders ? 700 : 600,
    "--pv-name-size": `${(fontSizePt * FONT_SIZE_RATIOS.name).toFixed(1)}pt`,
    "--pv-contact-size": `${(fontSizePt * FONT_SIZE_RATIOS.contact).toFixed(1)}pt`,
    "--pv-heading-size": `${(fontSizePt * FONT_SIZE_RATIOS.heading).toFixed(1)}pt`,
    "--pv-body-size": `${fontSizePt}pt`,
  };

  const sidebarContent = (
    <div className="resume-sidebar" ref={sidebarNodeRef} style={{ width: SIDEBAR_WIDTH_PX, background: `${theme.accentColor}0d` }}>
      {sidebarStaticBlocks.map((b) => (
        <div key={b.id} className="pv-block-wrap">
          {b.node}
        </div>
      ))}
    </div>
  );

  return (
    <div className="resume-preview">
      <div
        className="resume-preview__measure"
        style={{
          width: measureWidth,
          fontFamily,
          fontSize: `${fontSizePt}pt`,
          "--pv-accent": theme.accentColor,
          "--pv-density": densityScale,
          "--pv-title-weight": boldHeaders ? 700 : 600,
          "--pv-name-size": `${(fontSizePt * FONT_SIZE_RATIOS.name).toFixed(1)}pt`,
          "--pv-contact-size": `${(fontSizePt * FONT_SIZE_RATIOS.contact).toFixed(1)}pt`,
          "--pv-heading-size": `${(fontSizePt * FONT_SIZE_RATIOS.heading).toFixed(1)}pt`,
          "--pv-body-size": `${fontSizePt}pt`,
        }}
      >
        {flowBlocks.map((b) => (
          <div key={b.id} ref={setMeasureRef(b.id)} className="pv-block-wrap">
            {b.node}
          </div>
        ))}
      </div>

      <div
        className={`resume-preview__pages ${empty ? "resume-preview__pages--ghost" : ""}`}
        style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
      >
        {(ready ? pages : [flowBlocks.map((b) => b.id)]).map((pageBlockIds, pageIndex, allPages) => (
          <div className="resume-page" key={pageIndex} style={pageStyle} data-template={templateId}>
            <span className="resume-page__badge">
              Page {pageIndex + 1} of {allPages.length}
            </span>
            {isSidebar ? (
              <div className="resume-page__sidebar-layout">
                {sidebarContent}
                <div className="resume-main-col" style={{ width: measureWidth }}>
                  {pageBlockIds.map((id) => (
                    <div
                      key={id}
                      ref={(node) => {
                        if (node) blockNodeRefs.current.set(id, node);
                        else blockNodeRefs.current.delete(id);
                      }}
                      className={`pv-block-wrap ${overflowBlockIds.has(id) ? "pv-block-wrap--overflow" : ""}`}
                    >
                      {blockMap[id]?.node}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              pageBlockIds.map((id) => (
                <div
                  key={id}
                  ref={(node) => {
                    if (node) blockNodeRefs.current.set(id, node);
                    else blockNodeRefs.current.delete(id);
                  }}
                  className={`pv-block-wrap ${overflowBlockIds.has(id) ? "pv-block-wrap--overflow" : ""}`}
                >
                  {blockMap[id]?.node}
                </div>
              ))
            )}
          </div>
        ))}
      </div>
    </div>
  );
});

export default ResumePreview;
export { isResumeEmpty };
