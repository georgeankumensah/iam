"use client";

import { useRef } from "react";
import { clsx } from "clsx";

type OtpInputProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
  autoFocus?: boolean;
};

const OTP_LENGTH = 6;

export function OtpInput({ value, onChange, disabled, invalid, autoFocus }: OtpInputProps) {
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length: OTP_LENGTH }, (_, index) => value[index] || "");

  function updateAt(index: number, nextValue: string) {
    const nextDigit = nextValue.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[index] = nextDigit;
    onChange(next.join("").slice(0, OTP_LENGTH));
    if (nextDigit && index < OTP_LENGTH - 1) refs.current[index + 1]?.focus();
  }

  function handlePaste(event: React.ClipboardEvent<HTMLInputElement>) {
    event.preventDefault();
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
    onChange(pasted);
    refs.current[Math.min(pasted.length, OTP_LENGTH - 1)]?.focus();
  }

  return (
    <div className="grid grid-cols-6 justify-center gap-2 sm:gap-3">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => {
            refs.current[index] = node;
          }}
          value={digit}
          onChange={(event) => updateAt(index, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Backspace" && !digits[index] && index > 0) refs.current[index - 1]?.focus();
          }}
          onPaste={handlePaste}
          disabled={disabled}
          autoFocus={autoFocus && index === 0}
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          className={clsx(
            "h-12 w-full rounded-[10px] border bg-white px-0 text-center text-[20px] font-semibold text-[#111111] outline-none transition focus:border-[#111111] focus:ring-0 disabled:bg-[#f5f5f5] sm:h-14",
            invalid ? "border-red-400" : "border-[#d1d5db]"
          )}
          aria-label={`Digit ${index + 1}`}
        />
      ))}
    </div>
  );
}
