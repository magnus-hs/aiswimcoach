export interface KudosIconProps {
  active: boolean;
  size?: number;
  onClick?: () => void;
  className?: string;
}

/**
 * Premium minimal line-art thumbs-up icon.
 * Renders as an inline SVG with a clean, single-stroke-weight hand in side profile.
 *
 * - Inactive: outline only, muted stroke
 * - Active: filled with primary color
 */
export function KudosIcon({ active, size = 24, onClick, className }: KudosIconProps) {
  const stroke = active ? 'hsl(45, 95%, 50%)' : 'var(--color-text-muted)';
  const fill = active ? 'hsl(45, 95%, 50%)' : 'none';
  const cursor = onClick ? 'pointer' : 'default';

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke={stroke}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      onClick={onClick}
      className={className}
      style={{ cursor, display: 'inline-block', verticalAlign: 'middle' }}
      role={onClick ? 'button' : 'img'}
      aria-label="Kudos"
    >
      {/* Thumb */}
      <path d="M7 22V11l3.5-8a1.5 1.5 0 0 1 2.8.7L12 9h7a2 2 0 0 1 2 2.2l-1.4 7A2 2 0 0 1 17.6 20H7z" />
      {/* Palm/wrist area */}
      <rect x="2" y="11" width="5" height="11" rx="1" />
    </svg>
  );
}
