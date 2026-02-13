import { useId, useState, type ReactNode } from "react";

type CollapsiblePanelProps = {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  badgeCount?: number;
  children: ReactNode;
};

export function CollapsiblePanel({
  title,
  subtitle,
  defaultOpen = true,
  badgeCount,
  children,
}: CollapsiblePanelProps) {
  const titleId = useId();
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="panel" aria-labelledby={titleId}>
      <header className="panel-header">
        <button
          type="button"
          className="collapsible-toggle"
          aria-expanded={open}
          aria-controls={`${titleId}-body`}
          onClick={() => setOpen((prev) => !prev)}
        >
          <span className="collapsible-chevron" aria-hidden="true">
            {open ? "▾" : "▸"}
          </span>
          <div>
            <h2 id={titleId} style={{ display: "inline" }}>
              {title}
            </h2>
            {badgeCount != null && !open ? (
              <span className="badge-count" aria-label={`${badgeCount} itens`}>
                {" "}
                ({badgeCount})
              </span>
            ) : null}
            {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
          </div>
        </button>
      </header>
      {open ? <div id={`${titleId}-body`}>{children}</div> : null}
    </section>
  );
}
