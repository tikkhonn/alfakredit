export function Mark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden>
      <path d="M8 40 L24 8 L40 40 Z" fill="#ef3124" />
      <path d="M18 40 C22 32 26 32 30 40" fill="none" stroke="#070707" strokeWidth="3.4" />
    </svg>
  )
}
