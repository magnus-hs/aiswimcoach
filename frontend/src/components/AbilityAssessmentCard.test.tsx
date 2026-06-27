import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AbilityAssessmentCard } from './AbilityAssessmentCard';
import { AbilityAssessment } from '../types';

describe('AbilityAssessmentCard', () => {
  const mockAssessment: AbilityAssessment = {
    percentile_estimate: 'Top 15% for your age group',
    local_ranking: 'Competitive at local pool level, likely top 5 in casual meets',
    national_ranking: 'Mid-tier nationally, would need significant improvement for national competition',
    competitive_analysis: 'Strong recreational swimmer with good technique fundamentals. Current pace suggests you could compete in local masters events. Focus on consistent training volume to reach regional level.',
  };

  it('renders the card title', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(screen.getByText('Competitive Ability Assessment')).toBeInTheDocument();
  });

  it('renders percentile ranking section with label and value', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(screen.getByText('Percentile Ranking')).toBeInTheDocument();
    expect(screen.getByText(mockAssessment.percentile_estimate)).toBeInTheDocument();
  });

  it('renders local ranking section with label and value', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(screen.getByText('Local Ranking')).toBeInTheDocument();
    expect(screen.getByText(mockAssessment.local_ranking)).toBeInTheDocument();
  });

  it('renders national ranking section with label and value', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(screen.getByText('National Ranking')).toBeInTheDocument();
    expect(screen.getByText(mockAssessment.national_ranking)).toBeInTheDocument();
  });

  it('renders competitive analysis section with label and value', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(screen.getByText('Competitive Analysis')).toBeInTheDocument();
    expect(screen.getByText(mockAssessment.competitive_analysis)).toBeInTheDocument();
  });

  it('renders all four sections', () => {
    render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    const sections = screen.getAllByRole('heading', { level: 3 });
    expect(sections).toHaveLength(4);
    
    const sectionTitles = sections.map(section => section.textContent);
    expect(sectionTitles).toEqual([
      'Percentile Ranking',
      'Local Ranking',
      'National Ranking',
      'Competitive Analysis',
    ]);
  });

  it('applies correct CSS classes', () => {
    const { container } = render(<AbilityAssessmentCard assessment={mockAssessment} />);
    
    expect(container.querySelector('.ability-assessment-card')).toBeTruthy();
    expect(container.querySelector('.ability-assessment-card__heading')).toBeTruthy();
    expect(container.querySelector('.ability-assessment-card__content')).toBeTruthy();
    
    const sections = container.querySelectorAll('.ability-assessment-card__section');
    expect(sections).toHaveLength(4);
  });

  it('handles long text content without breaking layout', () => {
    const longAssessment: AbilityAssessment = {
      percentile_estimate: 'A'.repeat(100),
      local_ranking: 'B'.repeat(200),
      national_ranking: 'C'.repeat(200),
      competitive_analysis: 'D'.repeat(800),
    };
    
    render(<AbilityAssessmentCard assessment={longAssessment} />);
    
    expect(screen.getByText(longAssessment.percentile_estimate)).toBeInTheDocument();
    expect(screen.getByText(longAssessment.local_ranking)).toBeInTheDocument();
    expect(screen.getByText(longAssessment.national_ranking)).toBeInTheDocument();
    expect(screen.getByText(longAssessment.competitive_analysis)).toBeInTheDocument();
  });

  it('renders nothing when assessment is null', () => {
    const { container } = render(<AbilityAssessmentCard assessment={null} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when assessment is undefined', () => {
    const { container } = render(<AbilityAssessmentCard assessment={undefined} />);
    
    expect(container.firstChild).toBeNull();
  });
});
