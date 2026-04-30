type Props = {
  level: "Trial" | "Pro" | "Enterprise" | string;
};

export function AccessLevelBadge({ level }: Props) {
  const tone = level === "Enterprise" ? "border-warning/40 bg-warning/10 text-warning" : level === "Pro" ? "border-neon/40 bg-neon/10 text-neon" : "border-plasma/40 bg-plasma/10 text-[#c8b8ff]";
  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-black uppercase tracking-[0.22em] ${tone}`}>ACCESS LEVEL: {level}</span>;
}
