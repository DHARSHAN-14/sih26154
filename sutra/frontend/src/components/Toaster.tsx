import { useEffect } from "react";
import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToastStore, type ToastVariant } from "@/hooks/useToast";

const ICONS: Record<ToastVariant, React.ElementType> = {
  success: CheckCircle,
  error:   XCircle,
  warning: AlertTriangle,
  info:    Info,
};

const ICON_COLOR: Record<ToastVariant, string> = {
  success: "text-emerald-400",
  error:   "text-red-400",
  warning: "text-amber-400",
  info:    "text-blue-400",
};

export default function Toaster() {
  const { toasts, exit, dismiss } = useToastStore();

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
    >
      {toasts.map((toast) => {
        const Icon = ICONS[toast.variant];
        return (
          <ToastItem
            key={toast.id}
            toast={toast}
            Icon={Icon}
            iconColor={ICON_COLOR[toast.variant]}
            onDismiss={() => { exit(toast.id); setTimeout(() => dismiss(toast.id), 300); }}
          />
        );
      })}
    </div>
  );
}

interface ToastItemProps {
  toast: { id: string; variant: ToastVariant; title: string; description?: string; exiting?: boolean };
  Icon: React.ElementType;
  iconColor: string;
  onDismiss: () => void;
}

function ToastItem({ toast, Icon, iconColor, onDismiss }: ToastItemProps) {
  return (
    <div
      className={cn(
        `toast-${toast.variant}`,
        "pointer-events-auto",
        toast.exiting ? "animate-toast-out" : "animate-toast-in"
      )}
      role="alert"
    >
      <Icon size={16} className={cn("shrink-0 mt-0.5", iconColor)} />
      <div className="flex-1 min-w-0">
        <p className="font-semibold leading-tight">{toast.title}</p>
        {toast.description && (
          <p className="text-xs opacity-80 mt-0.5 leading-snug">{toast.description}</p>
        )}
      </div>
      <button
        onClick={onDismiss}
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity ml-1"
        aria-label="Dismiss"
      >
        <X size={13} />
      </button>
    </div>
  );
}
