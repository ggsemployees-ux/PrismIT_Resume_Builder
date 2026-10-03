import { useLayoutEffect, useRef, useState } from "react";

// A4 at 96dpi, with ~0.6in padding on all sides -- matches the printable
// area a real PDF render (Phase 4) will use, so page counts here are a
// realistic preview of the eventual PDF, not just an arbitrary UI choice.
export const PAGE_WIDTH = 794;
export const PAGE_HEIGHT = 1123;
export const PAGE_PADDING = 56;
export const CONTENT_WIDTH = PAGE_WIDTH - PAGE_PADDING * 2;
export const CONTENT_HEIGHT = PAGE_HEIGHT - PAGE_PADDING * 2;

/**
 * Takes an ordered list of blocks (each { id, measureKey }) and, by measuring
 * each block's real rendered height at CONTENT_WIDTH, groups them into pages
 * such that no single block is ever split across a page boundary -- if a
 * block doesn't fit in the remaining space on the current page, the whole
 * block moves to the next page instead of being sliced.
 *
 * Returns { pages: [[blockId, ...], ...], overflowBlockIds: Set, ready }.
 * `ready` is false on the very first render before measurement has run --
 * callers should show all blocks on a single unmeasured page (or a loading
 * state) until ready flips true, to avoid a layout flash.
 */
export function usePagedBlocks(blocks) {
  const measureRefs = useRef(new Map());
  const [result, setResult] = useState({ pages: [], overflowBlockIds: new Set(), ready: false });

  useLayoutEffect(() => {
    const heights = blocks.map((b) => {
      const node = measureRefs.current.get(b.id);
      return { id: b.id, height: node ? node.offsetHeight : 0 };
    });

    const pages = [];
    const overflowBlockIds = new Set();
    let currentPage = [];
    let currentHeight = 0;

    for (const { id, height } of heights) {
      if (height > CONTENT_HEIGHT) {
        // Single block taller than a whole page (e.g. a pasted wall of text).
        // Give it its own page rather than looping forever trying to fit it.
        if (currentPage.length > 0) {
          pages.push(currentPage);
          currentPage = [];
          currentHeight = 0;
        }
        pages.push([id]);
        overflowBlockIds.add(id);
        continue;
      }
      if (currentHeight + height > CONTENT_HEIGHT && currentPage.length > 0) {
        pages.push(currentPage);
        currentPage = [];
        currentHeight = 0;
      }
      currentPage.push(id);
      currentHeight += height;
    }
    if (currentPage.length > 0) pages.push(currentPage);
    if (pages.length === 0) pages.push([]);

    setResult({ pages, overflowBlockIds, ready: true });
    // Re-measure whenever the set of blocks or their content changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [blocks.map((b) => b.id + ":" + b.measureKey).join("|")]);

  function setMeasureRef(id) {
    return (node) => {
      if (node) measureRefs.current.set(id, node);
      else measureRefs.current.delete(id);
    };
  }

  return { ...result, setMeasureRef };
}
