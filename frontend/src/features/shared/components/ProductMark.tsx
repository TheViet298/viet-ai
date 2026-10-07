import type { ComponentProps } from "react";

export function ProductMark({ className = "w-4 h-4", ...props }: ComponentProps<"svg">) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
      {...props}
    >
      <path
        d="M5 9.5 L16 24 L27 9.5 L22.4 9.5 L16 18.2 L9.6 9.5 Z"
        fill="currentColor"
      />
      <path
        d="M9.5 7 L16 15.5 L22.5 7 L19.4 7 L16 11.5 L12.6 7 Z"
        fill="#60A5FA"
        opacity="0.9"
      />
    </svg>
  );
}
