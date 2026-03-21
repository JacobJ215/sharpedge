type BreakdownRow = {
  total_bets: number
  wins: number
  losses: number
  win_rate: number
  roi: number
}

function SectionHeader({ label, accent }: { label: string; accent: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <div className={`h-2.5 w-0.5 rounded-full ${accent}`} />
      <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">{label}</div>
    </div>
  )
}

function MiniTable({
  rows,
  labelCol,
}: {
  rows: Array<BreakdownRow & Record<string, string | number>>
  labelCol: { key: string; header: string }
}) {
  if (rows.length === 0) {
    return <p className="text-[10px] text-zinc-600">No settled bets in this slice yet.</p>
  }
  return (
    <div className="overflow-x-auto rounded border border-zinc-800/60">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/30">
            <th className="py-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              {labelCol.header}
            </th>
            <th className="py-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              Bets
            </th>
            <th className="py-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              W-L
            </th>
            <th className="py-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              Win%
            </th>
            <th className="py-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              ROI%
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-zinc-900/80 last:border-0 hover:bg-zinc-900/25">
              <td className="max-w-[140px] truncate py-1 px-2 text-[11px] text-zinc-300">
                {String(row[labelCol.key])}
              </td>
              <td className="py-1 px-2 font-mono text-[11px] text-zinc-400">{row.total_bets}</td>
              <td className="py-1 px-2 font-mono text-[11px] text-zinc-400">
                {row.wins}-{row.losses}
              </td>
              <td className="py-1 px-2 font-mono text-[11px] text-zinc-400">{row.win_rate.toFixed(1)}</td>
              <td
                className={`py-1 px-2 font-mono text-[11px] ${
                  row.roi >= 0 ? 'text-emerald-500/90' : 'text-red-400/90'
                }`}
              >
                {row.roi >= 0 ? '+' : ''}
                {row.roi.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export interface PortfolioBreakdownTablesProps {
  unitSize: number
  bySport: Array<BreakdownRow & { sport: string }>
  byBetType: Array<BreakdownRow & { bet_type: string }>
  byBook: Array<BreakdownRow & { sportsbook: string }>
  byJuice: Array<BreakdownRow & { bucket: string }>
}

export function PortfolioBreakdownTables({
  unitSize,
  bySport,
  byBetType,
  byBook,
  byJuice,
}: PortfolioBreakdownTablesProps) {
  const hasAny =
    bySport.length + byBetType.length + byBook.length + byJuice.length > 0

  if (!hasAny) {
    return (
      <div className="rounded border border-zinc-800/50 bg-zinc-950/40 px-3 py-2">
        <p className="text-[10px] text-zinc-600">
          Performance splits (sport, market type, book, juice) appear after settled bets are recorded.
        </p>
        {unitSize > 0 && (
          <p className="mt-1 text-[10px] text-zinc-500">
            Unit size on file: <span className="font-mono text-zinc-400">${unitSize.toFixed(2)}</span>
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {unitSize > 0 && (
        <p className="text-[10px] text-zinc-500">
          Unit size: <span className="font-mono text-zinc-400">${unitSize.toFixed(2)}</span>
          <span className="text-zinc-600"> — used when logging from the app</span>
        </p>
      )}
      <div>
        <SectionHeader label="By sport" accent="bg-violet-500" />
        <MiniTable rows={bySport} labelCol={{ key: 'sport', header: 'Sport' }} />
      </div>
      <div>
        <SectionHeader label="By bet type" accent="bg-cyan-500" />
        <MiniTable rows={byBetType} labelCol={{ key: 'bet_type', header: 'Type' }} />
      </div>
      <div>
        <SectionHeader label="By sportsbook" accent="bg-amber-500" />
        <MiniTable rows={byBook} labelCol={{ key: 'sportsbook', header: 'Book' }} />
      </div>
      <div>
        <SectionHeader label="By juice (American odds)" accent="bg-rose-500" />
        <MiniTable rows={byJuice} labelCol={{ key: 'bucket', header: 'Odds range' }} />
      </div>
    </div>
  )
}
