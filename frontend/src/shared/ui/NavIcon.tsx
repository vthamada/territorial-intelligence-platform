/**
 * Minimal SVG navigation icons inspired by Lucide / Feather icon sets.
 * 20×20 viewBox, 1.5px stroke, currentColor, no fill.
 */

const paths: Record<string, string> = {
  home: "M3 10.5L10 4l7 6.5V17a1 1 0 01-1 1h-4v-4H8v4H4a1 1 0 01-1-1v-6.5z",
  map: "M3 6l5-2 4 2 5-2v12l-5 2-4-2-5 2V6zM8 4v12M12 6v12",
  priorities:
    "M4 6h12M4 10h12M4 14h8M16 13l-2 2 4 4",
  insights: "M9 2a1 1 0 012 0v1a1 1 0 01-2 0V2zM10 6a4 4 0 00-4 4c0 1.5.8 2.8 2 3.5V15a2 2 0 004 0v-1.5A4 4 0 0010 6zM8 15h4",
  scenarios:
    "M4 4h4v4H4V4zM12 4h4v4h-4V4zM8 6h4M6 8v4M14 8v4M4 12h4v4H4v-4zM12 12h4v4h-4v-4z",
  briefs: "M4 4h12v14H4V4zM7 8h6M7 11h6M7 14h3",
  territory:
    "M3 5a2 2 0 012-2h10a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V5zM3 10h14M10 3v14",
  electorate:
    "M5 3h10a1 1 0 011 1v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1zM8 8l2 2 3-3M7 14h6",
  admin:
    "M10 13a3 3 0 100-6 3 3 0 000 6zM16.5 10a6.5 6.5 0 01-.4 2.2l1.4 1.1-1.2 2-1.7-.5a6.5 6.5 0 01-3.8 1.6L10 18l-1.8-1.6a6.5 6.5 0 01-3.8-1.6l-1.7.5-1.2-2 1.4-1.1A6.5 6.5 0 013.5 10c0-.8.1-1.5.4-2.2L2.5 6.7l1.2-2 1.7.5A6.5 6.5 0 019.2 3.6L10 2l.8 1.6a6.5 6.5 0 013.8 1.6l1.7-.5 1.2 2-1.4 1.1c.3.7.4 1.4.4 2.2z",
};

type NavIconProps = {
  name: string;
  size?: number;
  className?: string;
};

export function NavIcon({ name, size = 20, className }: NavIconProps) {
  const d = paths[name];
  if (!d) return null;

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
