"use client";

import React from "react";
import { AlertTriangle, Check, Copy, Info, Loader2, type LucideIcon } from "lucide-react";

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
export { cx };

/* ----------------------------------------------------------------------------
 * Layout
 * ------------------------------------------------------------------------- */

export function PageHeader({
  title,
  description,
  icon: Icon,
  actions,
}: {
  title: string;
  description?: React.ReactNode;
  icon?: LucideIcon;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="flex items-center gap-2.5 text-xl font-bold tracking-tight text-white sm:text-2xl">
          {Icon && <Icon className="h-5 w-5 shrink-0 text-cyan-400" aria-hidden />}
          {title}
        </h1>
        {description && <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({
  children,
  className,
  padded = true,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  className?: string;
  padded?: boolean;
  as?: "div" | "section";
}) {
  return (
    <Tag className={cx("rounded-xl border border-white/10 bg-surface/70 shadow-sm", padded && "p-5", className)}>
      {children}
    </Tag>
  );
}

export function SectionTitle({ children, icon: Icon, right }: { children: React.ReactNode; icon?: LucideIcon; right?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        {Icon && <Icon className="h-3.5 w-3.5 text-cyan-400" aria-hidden />}
        {children}
      </h2>
      {right}
    </div>
  );
}

/* ----------------------------------------------------------------------------
 * Controls
 * ------------------------------------------------------------------------- */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const buttonStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-[0_0_0_1px_rgba(34,211,238,0.4),0_8px_24px_-8px_rgba(34,211,238,0.5)]",
  secondary: "border border-white/10 bg-slate-800/80 text-slate-200 hover:bg-slate-700/80 hover:text-white",
  ghost: "text-slate-300 hover:bg-white/5 hover:text-white",
  danger: "border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20",
};

export function Button({
  variant = "secondary",
  size = "md",
  icon: Icon,
  loading,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  loading?: boolean;
}) {
  const sizes = { sm: "h-8 px-3 text-xs gap-1.5", md: "h-9 px-3.5 text-sm gap-2", lg: "h-11 px-5 text-sm gap-2" };
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || loading}
      className={cx(
        "inline-flex shrink-0 items-center justify-center rounded-lg font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50",
        sizes[size],
        buttonStyles[variant],
        className
      )}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : Icon && <Icon className="h-4 w-4" aria-hidden />}
      {children}
    </button>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <Button
      size="sm"
      icon={copied ? Check : Copy}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {
          /* clipboard unavailable (e.g. insecure context) */
        }
      }}
      aria-live="polite"
    >
      {copied ? "Copied" : label}
    </Button>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  options: Array<{ value: T; label: React.ReactNode; icon?: LucideIcon; count?: number }>;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto rounded-lg border border-white/5 bg-slate-900/60 p-1">
      {options.map((o) => {
        const active = o.value === value;
        const Icon = o.icon;
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={cx(
              "flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
              active ? "bg-slate-700/80 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
            )}
          >
            {Icon && <Icon className="h-3.5 w-3.5" aria-hidden />}
            {o.label}
            {o.count !== undefined && (
              <span className={cx("rounded px-1.5 font-mono text-[10px]", active ? "bg-cyan-400/15 text-cyan-300" : "bg-white/5")}>
                {o.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ----------------------------------------------------------------------------
 * Display
 * ------------------------------------------------------------------------- */

type Tone = "neutral" | "cyan" | "green" | "amber" | "red" | "violet" | "blue";

const toneStyles: Record<Tone, string> = {
  neutral: "bg-slate-800 text-slate-300 border-white/10",
  cyan: "bg-cyan-400/10 text-cyan-300 border-cyan-400/25",
  green: "bg-emerald-400/10 text-emerald-300 border-emerald-400/25",
  amber: "bg-amber-400/10 text-amber-300 border-amber-400/25",
  red: "bg-red-400/10 text-red-300 border-red-400/25",
  violet: "bg-violet-400/10 text-violet-300 border-violet-400/25",
  blue: "bg-blue-400/10 text-blue-300 border-blue-400/25",
};

export function Badge({ tone = "neutral", children, className, dot }: { tone?: Tone; children: React.ReactNode; className?: string; dot?: boolean }) {
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold", toneStyles[tone], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}

export function Stat({ label, value, hint, icon: Icon, tone = "cyan" }: { label: string; value: React.ReactNode; hint?: string; icon?: LucideIcon; tone?: Tone }) {
  return (
    <div className="rounded-xl border border-white/10 bg-surface/70 p-4" title={hint}>
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {Icon && (
          <span className={cx("flex h-6 w-6 items-center justify-center rounded-md border", toneStyles[tone])}>
            <Icon className="h-3.5 w-3.5" aria-hidden />
          </span>
        )}
        {label}
      </div>
      <div className="mt-2 font-mono text-xl font-bold tabular-nums text-white">{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-slate-500">{hint}</div>}
    </div>
  );
}

export function Callout({ tone = "amber", title, children, icon }: { tone?: "amber" | "red" | "cyan"; title?: string; children: React.ReactNode; icon?: LucideIcon }) {
  const Icon = icon ?? (tone === "cyan" ? Info : AlertTriangle);
  const styles = {
    amber: "border-amber-400/25 bg-amber-400/[0.07] text-amber-200",
    red: "border-red-400/30 bg-red-400/[0.08] text-red-200",
    cyan: "border-cyan-400/25 bg-cyan-400/[0.06] text-cyan-100",
  }[tone];
  return (
    <div role={tone === "red" ? "alert" : "status"} className={cx("flex gap-3 rounded-lg border p-3 text-sm animate-fade-in", styles)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0 leading-relaxed">
        {title && <div className="font-semibold">{title}</div>}
        <div className={cx(title && "text-[13px] opacity-90")}>{children}</div>
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-slate-800/60">
        <Icon className="h-5 w-5 text-slate-400" aria-hidden />
      </div>
      <div className="text-sm font-semibold text-slate-200">{title}</div>
      {children && <div className="mt-1 max-w-md text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton", className)} aria-hidden />;
}

export function ScoreBar({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="font-mono text-slate-500">n/a</span>;
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-emerald-400" : pct >= 50 ? "bg-amber-400" : "bg-red-400";
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-800" aria-hidden>
        <span className={cx("block h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </span>
      <span className="w-9 text-right font-mono tabular-nums text-slate-200">{pct}%</span>
    </span>
  );
}
