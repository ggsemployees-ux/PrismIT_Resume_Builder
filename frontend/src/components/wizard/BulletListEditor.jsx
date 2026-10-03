import { useRef } from "react";
import { toggleBoldInTextarea } from "../../utils/richText.jsx";
import "./BulletListEditor.css";

export default function BulletListEditor({ items, onChange, placeholder = "New bullet point" }) {
  const textareaRefs = useRef(new Map());

  function updateItem(index, value) {
    const next = [...items];
    next[index] = value;
    onChange(next);
  }

  function addItem() {
    onChange([...items, ""]);
  }

  function removeItem(index) {
    onChange(items.filter((_, i) => i !== index));
  }

  function handleBold(index) {
    const textarea = textareaRefs.current.get(index);
    if (!textarea) return;
    const { newValue, cursorStart, cursorEnd } = toggleBoldInTextarea(textarea);
    updateItem(index, newValue);
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(cursorStart, cursorEnd);
    });
  }

  return (
    <div className="bullet-editor">
      {items.map((item, i) => (
        <div className="bullet-editor__row" key={i}>
          <span className="bullet-editor__dot">•</span>
          <textarea
            ref={(node) => {
              if (node) textareaRefs.current.set(i, node);
              else textareaRefs.current.delete(i);
            }}
            rows={2}
            value={item}
            placeholder={placeholder}
            onChange={(e) => updateItem(i, e.target.value)}
          />
          <div className="bullet-editor__actions">
            <button type="button" className="bullet-editor__bold" title="Bold selected text" onClick={() => handleBold(i)}>
              B
            </button>
            <button type="button" className="bullet-editor__remove" title="Remove bullet" onClick={() => removeItem(i)}>
              ×
            </button>
          </div>
        </div>
      ))}
      <button type="button" className="btn btn-ghost btn-sm" onClick={addItem}>
        + Add bullet
      </button>
    </div>
  );
}
