import "./ZoomBar.css";

const MIN_ZOOM = 50;
const MAX_ZOOM = 150;
const STEP = 10;

export default function ZoomBar({ zoom, onZoomChange, onFitToWindow, isFitted, pageCount }) {
  return (
    <div className="zoom-bar">
      <div className="zoom-bar__controls">
        <button
          type="button"
          onClick={() => onZoomChange(Math.max(MIN_ZOOM, zoom - STEP))}
          disabled={zoom <= MIN_ZOOM}
        >
          −
        </button>
        <span className="zoom-bar__pct">{zoom}%</span>
        <button
          type="button"
          onClick={() => onZoomChange(Math.min(MAX_ZOOM, zoom + STEP))}
          disabled={zoom >= MAX_ZOOM}
        >
          +
        </button>
        <button
          type="button"
          className={`zoom-bar__fit ${isFitted ? "zoom-bar__fit--active" : ""}`}
          onClick={onFitToWindow}
        >
          Fit to window
        </button>
      </div>
      <span className="zoom-bar__pages">
        {pageCount} {pageCount === 1 ? "page" : "pages"}
      </span>
    </div>
  );
}
