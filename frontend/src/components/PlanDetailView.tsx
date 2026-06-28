import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPlanById, StructuredPlan, WeekBlock, SessionTemplate } from '../api/planService';
import './PlanDetailView.css';

/**
 * Full plan detail view with week-by-week expandable sections.
 * Each week shows session cards with type badges and set lists.
 */
export function PlanDetailView() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<StructuredPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedWeeks, setExpandedWeeks] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!planId) return;

    async function loadPlan() {
      try {
        const data = await getPlanById(planId!);
        setPlan(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load plan.';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadPlan();
  }, [planId]);

  const toggleWeek = (weekNumber: number) => {
    setExpandedWeeks((prev) => {
      const next = new Set(prev);
      if (next.has(weekNumber)) {
        next.delete(weekNumber);
      } else {
        next.add(weekNumber);
      }
      return next;
    });
  };

  if (loading) {
    return <div className="plan-detail__loading">Loading plan…</div>;
  }

  if (error) {
    return (
      <div className="plan-detail__error" role="alert">
        <p>{error}</p>
        <button onClick={() => navigate('/plans')}>Back to Plans</button>
      </div>
    );
  }

  if (!plan) {
    return <div className="plan-detail__error">Plan not found.</div>;
  }

  return (
    <div className="plan-detail">
      <button className="plan-detail__back" onClick={() => navigate('/plans')}>
        ← Back to Plans
      </button>

      <header className="plan-detail__header">
        <div className="plan-detail__header-main">
          <h1 className="plan-detail__title">{plan.goal.event}</h1>
          <StatusBadge status={plan.status} />
        </div>
        <div className="plan-detail__meta">
          <span>Target: {plan.goal.target_time}</span>
          <span>{plan.duration_weeks} weeks</span>
          <span>{plan.sessions_per_week} sessions/week</span>
          {plan.goal.personal_best_seconds && (
            <span>PB: {formatTime(plan.goal.personal_best_seconds)}</span>
          )}
        </div>
      </header>

      {plan.weeks && plan.weeks.length > 0 ? (
        <div className="plan-detail__weeks">
          {plan.weeks.map((week) => (
            <WeekSection
              key={week.week_number}
              week={week}
              expanded={expandedWeeks.has(week.week_number)}
              onToggle={() => toggleWeek(week.week_number)}
            />
          ))}
        </div>
      ) : (
        <p className="plan-detail__empty">No week data available for this plan.</p>
      )}
    </div>
  );
}

function WeekSection({
  week,
  expanded,
  onToggle,
}: {
  week: WeekBlock;
  expanded: boolean;
  onToggle: () => void;
}) {
  const totalDistance = week.sessions.reduce((sum, s) => sum + s.total_distance, 0);

  return (
    <div className="plan-detail__week">
      <button
        className="plan-detail__week-header"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <span className="plan-detail__week-title">Week {week.week_number}</span>
        <span className="plan-detail__week-summary">
          {week.sessions.length} sessions · {totalDistance.toLocaleString()}m total
        </span>
        <span className="plan-detail__week-chevron" aria-hidden="true">
          {expanded ? '▾' : '▸'}
        </span>
      </button>

      {expanded && (
        <div className="plan-detail__week-body">
          {week.sessions.map((session, idx) => (
            <SessionCard key={idx} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}

function SessionCard({ session }: { session: SessionTemplate }) {
  return (
    <div className="plan-detail__session">
      <div className="plan-detail__session-header">
        <h4 className="plan-detail__session-title">{session.session_title}</h4>
        <SessionTypeBadge type={session.session_type} />
      </div>

      <div className="plan-detail__session-sets">
        <div className="plan-detail__set">
          <h5 className="plan-detail__set-label">Warm-up</h5>
          <ul className="plan-detail__set-list">
            {session.warm_up.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="plan-detail__set">
          <h5 className="plan-detail__set-label">Main Set</h5>
          <ul className="plan-detail__set-list">
            {session.main_set.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="plan-detail__set">
          <h5 className="plan-detail__set-label">Cool-down</h5>
          <ul className="plan-detail__set-list">
            {session.cool_down.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="plan-detail__session-footer">
        <span className="plan-detail__distance">
          {session.total_distance.toLocaleString()}m
        </span>
        <span className="plan-detail__focus">{session.focus_notes}</span>
      </div>
    </div>
  );
}

function SessionTypeBadge({ type }: { type: SessionTemplate['session_type'] }) {
  const classMap = {
    endurance: 'plan-detail__type-badge--endurance',
    speed: 'plan-detail__type-badge--speed',
    technique: 'plan-detail__type-badge--technique',
    threshold: 'plan-detail__type-badge--threshold',
  };

  return (
    <span className={`plan-detail__type-badge ${classMap[type]}`}>
      {type}
    </span>
  );
}

function StatusBadge({ status }: { status: StructuredPlan['status'] }) {
  const classMap = {
    active: 'plan-detail__status--active',
    draft: 'plan-detail__status--draft',
    archived: 'plan-detail__status--archived',
  };

  return (
    <span className={`plan-detail__status ${classMap[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(1);
  return mins > 0 ? `${mins}:${secs.padStart(4, '0')}` : `${secs}s`;
}
