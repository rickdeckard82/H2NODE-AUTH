/* Gráficos leves em SVG puro — sem dependências. */

export const CHART_COLORS = [
  "#2b6cf6", // brand
  "#16a34a", // green
  "#f59e0b", // amber
  "#e11d48", // rose
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#ec4899", // pink
  "#84cc16", // lime
];

interface Slice {
  label: string;
  value: number;
}

/** Rosca colorida + legenda. */
export function DonutChart({
  data,
  size = 176,
  thickness = 24,
  unit = "",
  empty = "Sem dados",
}: {
  data: Slice[];
  size?: number;
  thickness?: number;
  unit?: string;
  empty?: string;
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2;
  const cx = size / 2;
  const circ = 2 * Math.PI * r;
  const gap = data.length > 1 ? 1.6 : 0;

  let acc = 0;
  const segs = data.map((d, i) => {
    const len = total ? (d.value / total) * circ : 0;
    const seg = {
      ...d,
      color: CHART_COLORS[i % CHART_COLORS.length],
      len,
      offset: acc,
      pct: total ? d.value / total : 0,
    };
    acc += len;
    return seg;
  });

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="shrink-0"
        role="img"
        aria-label="Distribuição por utilizador"
      >
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          strokeWidth={thickness}
          className="stroke-slate-100 dark:stroke-slate-800"
        />
        {total > 0 && (
          <g transform={`rotate(-90 ${cx} ${cx})`}>
            {segs
              .filter((s) => s.len > 0)
              .map((s, i) => {
                const dash = Math.max(s.len - gap, 0.001);
                return (
                  <circle
                    key={i}
                    cx={cx}
                    cy={cx}
                    r={r}
                    fill="none"
                    stroke={s.color}
                    strokeWidth={thickness}
                    strokeDasharray={`${dash} ${circ - dash}`}
                    strokeDashoffset={-s.offset}
                  />
                );
              })}
          </g>
        )}
        <text
          x="50%"
          y="48%"
          textAnchor="middle"
          className="fill-slate-900 dark:fill-slate-100"
          style={{ fontSize: size * 0.16, fontWeight: 700 }}
        >
          {total}
        </text>
        {unit && (
          <text
            x="50%"
            y="62%"
            textAnchor="middle"
            className="fill-slate-400 dark:fill-slate-500"
            style={{ fontSize: size * 0.06, letterSpacing: 1.5 }}
          >
            {unit.toUpperCase()}
          </text>
        )}
      </svg>

      {total > 0 ? (
        <ul className="w-full min-w-0 space-y-2 text-sm">
          {segs.map((s, i) => (
            <li key={i} className="flex items-center gap-2">
              <span
                className="h-3 w-3 shrink-0 rounded-full"
                style={{ backgroundColor: s.color }}
              />
              <span className="truncate font-medium text-slate-700 dark:text-slate-200">
                {s.label}
              </span>
              <span className="ml-auto shrink-0 tabular-nums text-slate-500 dark:text-slate-400">
                {s.value} · {(s.pct * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-400 dark:text-slate-500">{empty}</p>
      )}
    </div>
  );
}

/** Barra horizontal comparando aceitos x negados. */
export function CompareBar({
  accepts,
  rejects,
}: {
  accepts: number;
  rejects: number;
}) {
  const total = accepts + rejects;
  const aPct = total ? (accepts / total) * 100 : 0;
  const rPct = total ? (rejects / total) * 100 : 0;

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3">
        <h3 className="font-semibold">Aceitos vs. negados (7 dias)</h3>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          {total ? `${aPct.toFixed(0)}% de aprovação` : "sem eventos nos últimos 7 dias"}
        </span>
      </div>

      <div className="flex h-9 w-full overflow-hidden rounded-lg bg-slate-100 dark:bg-slate-800">
        {total > 0 && (
          <>
            <div
              className="flex items-center justify-start bg-emerald-500 px-2 text-xs font-semibold text-white transition-[width] duration-500"
              style={{ width: `${aPct}%` }}
            >
              {aPct >= 12 && <span className="tabular-nums">{accepts}</span>}
            </div>
            <div
              className="flex items-center justify-end bg-rose-500 px-2 text-xs font-semibold text-white transition-[width] duration-500"
              style={{ width: `${rPct}%` }}
            >
              {rPct >= 12 && <span className="tabular-nums">{rejects}</span>}
            </div>
          </>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          Aceitos <b className="tabular-nums text-slate-800 dark:text-slate-100">{accepts}</b>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
          Negados <b className="tabular-nums text-slate-800 dark:text-slate-100">{rejects}</b>
        </span>
      </div>
    </div>
  );
}

/* ---------------- Séries diárias (7 dias) ---------------- */

export interface DailyPoint {
  date: string; // YYYY-MM-DD (UTC)
  accepts: number;
  rejects: number;
  sessions: number;
}

/** "seg", "ter"… a partir de uma data ISO em UTC. */
function dayLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("pt-BR", { weekday: "short", timeZone: "UTC" }).replace(".", "");
}

/** Curva suave (Bézier com pontos de controle no ponto médio). */
function smoothPath(pts: [number, number][]): string {
  if (pts.length < 2) return "";
  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[i + 1];
    const mx = (x0 + x1) / 2;
    d += ` C ${mx} ${y0}, ${mx} ${y1}, ${x1} ${y1}`;
  }
  return d;
}

/** Barras empilhadas (aceitos + negados) por dia, últimos 7 dias. */
export function AuthTrendChart({ data }: { data: DailyPoint[] }) {
  const max = Math.max(1, ...data.map((d) => d.accepts + d.rejects));
  const totA = data.reduce((s, d) => s + d.accepts, 0);
  const totR = data.reduce((s, d) => s + d.rejects, 0);
  const total = totA + totR;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-3">
        <h3 className="font-semibold">Autenticações por dia · 7 dias</h3>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          {total ? `${((totA / total) * 100).toFixed(0)}% de aprovação` : "sem eventos"}
        </span>
      </div>

      <div className="flex h-44 items-end gap-2 sm:gap-3">
        {data.map((d, i) => {
          const t = d.accepts + d.rejects;
          const isToday = i === data.length - 1;
          return (
            <div
              key={d.date}
              className="group flex h-full flex-1 flex-col items-center justify-end gap-1.5"
            >
              <span className="text-[11px] tabular-nums text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 dark:text-slate-500">
                {t || " "}
              </span>
              <div
                className="flex w-full max-w-[44px] flex-col-reverse overflow-hidden rounded-md bg-slate-100 ring-1 ring-inset ring-black/[0.03] transition-all dark:bg-slate-800 dark:ring-white/5"
                style={{ height: `${Math.max((t / max) * 100, 2)}%` }}
                title={`${dayLabel(d.date)} — ${d.accepts} aceitos · ${d.rejects} negados`}
              >
                <div
                  className="w-full bg-emerald-500 transition-[flex-grow] duration-500"
                  style={{ flexGrow: d.accepts }}
                />
                <div
                  className="w-full bg-rose-500 transition-[flex-grow] duration-500"
                  style={{ flexGrow: d.rejects }}
                />
              </div>
              <span
                className={`text-[11px] capitalize ${
                  isToday
                    ? "font-semibold text-slate-600 dark:text-slate-300"
                    : "text-slate-400 dark:text-slate-500"
                }`}
              >
                {dayLabel(d.date)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600 dark:text-slate-300">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          Aceitos <b className="tabular-nums text-slate-800 dark:text-slate-100">{totA}</b>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
          Negados <b className="tabular-nums text-slate-800 dark:text-slate-100">{totR}</b>
        </span>
      </div>
    </div>
  );
}

/** Área suave: sessões iniciadas por dia, últimos 7 dias. */
export function SessionsAreaChart({ data }: { data: DailyPoint[] }) {
  const W = 300;
  const H = 96;
  const pad = 6;
  const max = Math.max(1, ...data.map((d) => d.sessions));
  const peak = Math.max(...data.map((d) => d.sessions), 0);
  const total = data.reduce((s, d) => s + d.sessions, 0);

  const pts: [number, number][] = data.map((d, i) => [
    data.length > 1 ? (i / (data.length - 1)) * W : W / 2,
    H - pad - (d.sessions / max) * (H - pad * 2),
  ]);
  const line = smoothPath(pts);
  const area = line ? `${line} L ${W} ${H} L 0 ${H} Z` : "";

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3">
        <h3 className="font-semibold">Sessões por dia · 7 dias</h3>
        <span className="text-sm text-slate-500 dark:text-slate-400">
          {total ? `${total} no total · pico ${peak}` : "sem sessões"}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={H}
        preserveAspectRatio="none"
        role="img"
        aria-label="Sessões por dia"
        className="overflow-visible"
      >
        <defs>
          <linearGradient id="sessGrad" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={CHART_COLORS[0]} stopOpacity="0.35" />
            <stop offset="100%" stopColor={CHART_COLORS[0]} stopOpacity="0" />
          </linearGradient>
        </defs>
        {area && <path d={area} fill="url(#sessGrad)" />}
        {line && (
          <path
            d={line}
            fill="none"
            stroke={CHART_COLORS[0]}
            strokeWidth={2}
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>

      <div className="mt-1 flex justify-between text-[11px] capitalize text-slate-400 dark:text-slate-500">
        {data.map((d, i) => (
          <span key={d.date} className={i === data.length - 1 ? "font-semibold" : ""}>
            {dayLabel(d.date)}
          </span>
        ))}
      </div>
    </div>
  );
}
