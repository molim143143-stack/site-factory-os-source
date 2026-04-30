import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  glow?: "cyan" | "purple" | "danger" | "none";
};

export function GlassCard({ children, className = "", glow = "cyan" }: Props) {
  const glowClass =
    glow === "purple" ? "hover:shadow-plasma" : glow === "danger" ? "hover:shadow-danger" : glow === "none" ? "" : "hover:shadow-neon";
  return (
    <section className={`glass-card ${glowClass} ${className}`}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-neon/70 to-transparent" />
      {children}
    </section>
  );
}
