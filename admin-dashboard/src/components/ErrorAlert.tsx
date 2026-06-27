import { XCircle } from "lucide-react";
import clsx from "../lib/clsx";

interface ErrorAlertProps {
  message: string | null;
  className?: string;
  onDismiss?: () => void;
}

export function ErrorAlert({ message, className, onDismiss }: ErrorAlertProps) {
  if (!message) return null;

  return (
    <div
      className={clsx(
        "flex items-center gap-2 rounded-md border border-[#f2dede] bg-[#fef2f2] px-4 py-3 text-sm text-[#8b3a3a]",
        className,
      )}
    >
      <XCircle size={16} className="shrink-0" />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="text-[#8b3a3a] hover:text-[#6b2a2a]">
          &times;
        </button>
      )}
    </div>
  );
}
