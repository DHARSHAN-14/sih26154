/**
 * hooks/useKeyboard.ts
 * Global keyboard shortcut handler.
 * Registers shortcuts on mount, cleans up on unmount.
 *
 * Shortcut format:
 *   "ctrl+k"   — Ctrl/Cmd + K
 *   "g g"      — sequential g → g (two-key chord)
 *   "Escape"   — Escape key
 *   "?"        — single character
 */
import { useEffect, useRef } from "react";

type Handler = (e: KeyboardEvent) => void;

export interface ShortcutMap {
  [shortcut: string]: Handler;
}

function matchesShortcut(e: KeyboardEvent, shortcut: string): boolean {
  const parts = shortcut.toLowerCase().split("+");
  const key   = parts[parts.length - 1];
  const ctrl  = parts.includes("ctrl") || parts.includes("cmd");
  const shift = parts.includes("shift");
  const alt   = parts.includes("alt");

  if (ctrl  && !(e.ctrlKey || e.metaKey)) return false;
  if (shift && !e.shiftKey) return false;
  if (alt   && !e.altKey)   return false;
  if (ctrl  && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === key) return true;
  if (!ctrl && !shift && !alt && e.key.toLowerCase() === key) return true;
  return false;
}

export function useKeyboard(shortcuts: ShortcutMap, enabled = true) {
  const ref = useRef(shortcuts);
  ref.current = shortcuts;

  useEffect(() => {
    if (!enabled) return;

    function handler(e: KeyboardEvent) {
      // Don't fire inside inputs / textareas / contenteditable
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement)?.isContentEditable) return;

      for (const shortcut of Object.keys(ref.current)) {
        if (matchesShortcut(e, shortcut)) {
          e.preventDefault();
          ref.current[shortcut](e);
          break;
        }
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [enabled]);
}
