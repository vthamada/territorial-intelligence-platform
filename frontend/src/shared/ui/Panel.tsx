import { useId, type ReactNode } from "react";

type PanelProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function Panel({ title, subtitle, actions, children }: PanelProps) {
  const titleId = useId();
  return (
    <section className="panel" aria-labelledby={titleId}>
      <header className="panel-header">
        <div>
          <h2 id={titleId}>{title}</h2>
          {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </header>
      <div>{children}</div>
    </section>
  );
}
