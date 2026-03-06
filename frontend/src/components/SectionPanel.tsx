import type { ReactNode } from "react";

type SectionPanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

export default function SectionPanel({
  eyebrow,
  title,
  description,
  children,
}: SectionPanelProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <p className="panel__eyebrow">{eyebrow}</p>
        <h2 className="panel__title">{title}</h2>
        <p className="panel__description">{description}</p>
      </div>
      <div className="panel__content">{children}</div>
    </section>
  );
}
