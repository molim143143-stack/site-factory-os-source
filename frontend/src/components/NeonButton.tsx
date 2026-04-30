import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  tone?: "primary" | "purple" | "success" | "warning" | "danger" | "ghost";
};

export const NeonButton = forwardRef<HTMLButtonElement, Props>(function NeonButton({ children, tone = "primary", className = "", type = "button", ...props }, ref) {
  const tones = {
    primary: "border-neon/40 bg-neon/10 text-neon hover:bg-neon/20 hover:shadow-neon",
    purple: "border-plasma/40 bg-plasma/10 text-[#c8b8ff] hover:bg-plasma/20 hover:shadow-plasma",
    success: "border-success/40 bg-success/10 text-success hover:bg-success/20",
    warning: "border-warning/40 bg-warning/10 text-warning hover:bg-warning/20",
    danger: "border-danger/40 bg-danger/10 text-danger hover:bg-danger/20 hover:shadow-danger",
    ghost: "border-white/10 bg-white/5 text-textWeak hover:border-neon/40 hover:text-neon"
  };
  return (
    <button
      ref={ref}
      type={type}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-all duration-200 active:scale-[0.98] ${tones[tone]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
});
