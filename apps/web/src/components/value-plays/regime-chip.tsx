export function RegimeChip({ regime }: { regime: string }) {
  return (
    <span className="inline-block rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
      {regime}
    </span>
  )
}
