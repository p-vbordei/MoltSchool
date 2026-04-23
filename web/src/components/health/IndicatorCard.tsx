type Props = {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "warn";
};

export function IndicatorCard({ label, value, hint, tone = "neutral" }: Props) {
  const valueClass = {
    neutral: "text-foreground",
    good: "text-accent",
    warn: "text-red-400",
  }[tone];
  return (
    <div className="grimoire-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`mt-1 font-serif text-2xl ${valueClass}`}>{value}</div>
      {hint && (
        <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
      )}
    </div>
  );
}
