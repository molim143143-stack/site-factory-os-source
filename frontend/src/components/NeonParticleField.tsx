export function NeonParticleField() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: 28 }).map((_, index) => (
        <span
          key={index}
          className="absolute h-px w-16 rotate-45 rounded-full bg-gradient-to-r from-transparent via-neon to-transparent opacity-50"
          style={{
            left: `${(index * 37) % 100}%`,
            top: `${(index * 19) % 100}%`,
            animation: `float ${4 + (index % 5)}s ease-in-out infinite`,
            animationDelay: `${index * 0.12}s`
          }}
        />
      ))}
    </div>
  );
}
