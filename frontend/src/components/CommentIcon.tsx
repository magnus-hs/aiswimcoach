export interface CommentIconProps {
  size?: number;
  className?: string;
}

/**
 * Minimal line-art speech bubble icon for comment count display.
 */
export function CommentIcon({ size = 14, className }: CommentIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="hsl(45, 95%, 50%)"
      stroke="hsl(45, 95%, 50%)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ display: 'inline-block', verticalAlign: 'middle' }}
      role="img"
      aria-label="Comments"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
