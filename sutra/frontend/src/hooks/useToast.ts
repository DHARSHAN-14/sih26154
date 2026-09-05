/**
 * hooks/useToast.ts
 * Lightweight global toast system with no external deps.
 * Usage:
 *   const { toast } = useToast();
 *   toast.success("Artefact approved");
 *   toast.error("Upload failed", "Check your connection");
 */
import { create } from "zustand";
import { useCallback } from "react";

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  durationMs: number;
  /** set to true by Toaster when fading out */
  exiting?: boolean;
}

interface ToastStore {
  toasts: Toast[];
  add:    (t: Omit<Toast, "id" | "exiting">) => string;
  dismiss:(id: string) => void;
  exit:   (id: string) => void;
}

let _seq = 0;

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],

  add: (t) => {
    const id = `toast-${Date.now()}-${++_seq}`;
    set((s) => ({ toasts: [...s.toasts, { ...t, id }] }));
    return id;
  },

  exit: (id) =>
    set((s) => ({
      toasts: s.toasts.map((t) => (t.id === id ? { ...t, exiting: true } : t)),
    })),

  dismiss: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

/** Convenience hook — returns typed helper methods */
export function useToast() {
  const { add, exit, dismiss } = useToastStore();

  const show = useCallback(
    (
      variant: ToastVariant,
      title: string,
      description?: string,
      durationMs = 4000
    ) => {
      const id = add({ variant, title, description, durationMs });
      // Start exit animation before full dismiss
      const exitTimer   = setTimeout(() => exit(id), durationMs);
      const removeTimer = setTimeout(() => dismiss(id), durationMs + 300);
      return () => { clearTimeout(exitTimer); clearTimeout(removeTimer); dismiss(id); };
    },
    [add, exit, dismiss]
  );

  return {
    toast: {
      success: (title: string, desc?: string) => show("success", title, desc),
      error:   (title: string, desc?: string) => show("error",   title, desc),
      warning: (title: string, desc?: string) => show("warning", title, desc),
      info:    (title: string, desc?: string) => show("info",    title, desc),
    },
  };
}
