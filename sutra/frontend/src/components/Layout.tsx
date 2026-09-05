import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header  from "./Header";
import Toaster from "./Toaster";
import { useSessionStore } from "@/store/session";
import { useKeyboard } from "@/hooks/useKeyboard";
import { cn } from "@/lib/utils";

const BANNER: Record<string, string> = {
  unclassified: "classify-unclassified",
  restricted:   "classify-restricted",
  confidential: "classify-confidential",
  secret:       "classify-secret",
};

export default function Layout() {
  const classification = useSessionStore(
    (s) => s.session?.classification ?? "unclassified"
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close mobile sidebar on route change
  // (runs every render when location changes — cheap)
  const _ = location.pathname; // suppress unused warning

  // Keyboard: press \ to toggle sidebar on mobile
  useKeyboard({ "\\": () => setSidebarOpen((o) => !o) });

  const bannerCls = BANNER[classification] ?? "classify-unclassified";

  return (
    <div className="flex flex-col h-dvh bg-slate-950 overflow-hidden">
      {/* Classification banner — top */}
      <div className={bannerCls}>
        <span>◆</span>
        <span>{classification.toUpperCase()}</span>
        <span>◆</span>
      </div>

      <div className="flex flex-1 min-h-0 relative">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar — hidden on mobile unless open */}
        <div
          className={cn(
            "fixed inset-y-0 left-0 z-30 lg:relative lg:z-auto",
            "transition-transform duration-200",
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          )}
        >
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </div>

        {/* Main content */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <Header onMenuClick={() => setSidebarOpen((o) => !o)} />
          <main className="flex-1 overflow-y-auto p-4 sm:p-6">
            {/* Route-change fade animation key */}
            <div key={location.pathname} className="animate-fade-in h-full">
              <Outlet />
            </div>
          </main>
        </div>
      </div>

      {/* Classification banner — bottom */}
      <div className={bannerCls}>
        <span>◆</span>
        <span>{classification.toUpperCase()}</span>
        <span>◆</span>
      </div>

      {/* Global toast notifications */}
      <Toaster />
    </div>
  );
}
