import Link from "next/link";

interface BreadcrumbNavProps {
  ticId: string;
}

export default function BreadcrumbNav({ ticId }: BreadcrumbNavProps) {
  return (
    <nav className="flex items-center gap-2 px-4 py-2 border-b border-[var(--border-color)] bg-[var(--panel)]">
      <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
        [
      </span>
      <Link
        href="/"
        className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)] hover:text-[var(--fg)] transition-colors"
      >
        HOME
      </Link>
      <span className="font-mono text-[10px] text-[var(--border-color)]">
        //
      </span>
      <span className="font-mono text-[10px] tracking-widest text-[var(--fg)] font-bold">
        {ticId}
      </span>
      <span className="font-mono text-[10px] tracking-widest text-[var(--fg-dim)]">
        ]
      </span>
    </nav>
  );
}
