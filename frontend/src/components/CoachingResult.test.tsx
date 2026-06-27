import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CoachingResult } from './CoachingResult';

describe('CoachingResult', () => {
  const defaultProps = {
    tips: ['Improve your catch phase.', 'Kick from the hips.', 'Breathe bilaterally.'],
    drill: 'Single-arm freestyle drill: 25m each arm, focus on high elbow catch.',
  };

  it('renders all three tips with numbered labels', () => {
    render(<CoachingResult {...defaultProps} />);

    expect(screen.getByText('Tip 1')).toBeInTheDocument();
    expect(screen.getByText('Tip 2')).toBeInTheDocument();
    expect(screen.getByText('Tip 3')).toBeInTheDocument();

    expect(screen.getByText(defaultProps.tips[0])).toBeInTheDocument();
    expect(screen.getByText(defaultProps.tips[1])).toBeInTheDocument();
    expect(screen.getByText(defaultProps.tips[2])).toBeInTheDocument();
  });

  it('renders the drill text in a distinct section', () => {
    render(<CoachingResult {...defaultProps} />);

    const drillSection = screen.getByRole('complementary', { name: /drill recommendation/i });
    expect(drillSection).toBeInTheDocument();
    expect(drillSection).toHaveTextContent(defaultProps.drill);
  });

  it('renders tips in an ordered list', () => {
    render(<CoachingResult {...defaultProps} />);

    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
  });

  it('has an accessible section label for coaching results', () => {
    render(<CoachingResult {...defaultProps} />);

    const section = screen.getByRole('region', { name: /coaching results/i });
    expect(section).toBeInTheDocument();
  });

  it('applies the drill card styling class', () => {
    render(<CoachingResult {...defaultProps} />);

    const drillSection = screen.getByRole('complementary', { name: /drill recommendation/i });
    expect(drillSection).toHaveClass('coaching-result__drill');
  });
});
