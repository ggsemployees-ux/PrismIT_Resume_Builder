/**
 * Minimal rich-text support: only handles **bold** so the editor can offer
 * bold without pulling in a full rich-text editor dependency. Renders a
 * string containing **bold** markers into React nodes.
 */
export function renderRichText(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

/** Wraps the current text-selection in a textarea with ** ** markers, or
 * inserts an empty ** ** pair at the cursor if nothing is selected. Returns
 * the new full string and the new cursor position so the caller can restore
 * focus/selection after the state update. */
export function toggleBoldInTextarea(textarea) {
  const { value, selectionStart, selectionEnd } = textarea;
  const selected = value.slice(selectionStart, selectionEnd);
  const before = value.slice(0, selectionStart);
  const after = value.slice(selectionEnd);

  if (selected) {
    const newValue = `${before}**${selected}**${after}`;
    return { newValue, cursorStart: selectionStart + 2, cursorEnd: selectionEnd + 2 };
  }
  const newValue = `${before}****${after}`;
  return { newValue, cursorStart: selectionStart + 2, cursorEnd: selectionStart + 2 };
}
