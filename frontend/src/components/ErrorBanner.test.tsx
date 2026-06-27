import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ErrorBanner } from './ErrorBanner';

describe('ErrorBanner', () => {
  it('renders the error message with role="alert"', () => {
    render(<ErrorBanner message="Something went wrong." />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent('Something went wrong.');
  });

  it('does not render a retry button when onRetry is not provided', () => {
    render(<ErrorBanner message="Client error." />);

    expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
  });

  it('renders a "Try Again" button when onRetry is provided', () => {
    const handleRetry = vi.fn();
    render(<ErrorBanner message="Server error." onRetry={handleRetry} />);

    const button = screen.getByRole('button', { name: /try again/i });
    expect(button).toBeInTheDocument();
  });

  it('calls onRetry when the "Try Again" button is clicked', async () => {
    const user = userEvent.setup();
    const handleRetry = vi.fn();
    render(<ErrorBanner message="Network error." onRetry={handleRetry} />);

    await user.click(screen.getByRole('button', { name: /try again/i }));

    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
