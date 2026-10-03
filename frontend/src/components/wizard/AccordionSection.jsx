import "./AccordionSection.css";

export default function AccordionSection({ id, title, isOpen, onOpen, onContinue, continueLabel, children }) {
  return (
    <div className={`accordion-section ${isOpen ? "accordion-section--open" : ""}`}>
      <button
        type="button"
        className="accordion-section__header"
        onClick={() => onOpen(isOpen ? null : id)}
        aria-expanded={isOpen}
      >
        <span>{title}</span>
        <span className="accordion-section__chevron">{isOpen ? "−" : "+"}</span>
      </button>
      {isOpen && (
        <div className="accordion-section__body">
          {children}
          {onContinue && (
            <button type="button" className="btn btn-accent accordion-section__continue" onClick={onContinue}>
              Continue to {continueLabel} →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
