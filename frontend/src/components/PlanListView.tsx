import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStructuredPlans, updatePlanStatus, StructuredPlan } from '../api/planService';
import './PlanListView.css';

/**
 * Displays all structured plans as cards with status badges and lifecycle actions.
 */
export function PlanListView() {
  const [plans, setPlans] = useState<StructuredPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadPlans = async () => {
    try {
      const data = await getStructuredPlans();
      setPlans(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load plans.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  const handleActivate = async (planId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await updatePlanStatus(planId, 'active');
      await loadPlans();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to activate plan.';
      setError(message);
    }
  };

  const handleArchive = async (planId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await updatePlanStatus(planId, 'archived');
      await loadPlans();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to archive plan.';
      setError(message);
    }
  };

  if (loading) {
    return <p className="plan-list__loading">Loading plans…</p>;
  }

  if (error) {
    return <p className="plan-list__error" role="alert">{error}</p>;
  }

  if (plans.length === 0) {
    return (
      <p className="plan-list__empty">
        No structured plans yet. Create one to get started.
      </p>
    );
  }

  return (
    <div className="plan-list">
      {plans.map((plan) => (
        <div
          key={plan.plan_id}
          className="plan-list__card"
          onClick={() => navigate(`/plans/${plan.plan_id}`)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              navigate(`/plans/${plan.plan_id}`);
            }
          }}
        >
          <div className="plan-list__card-header">
            <h3 className="plan-list__card-title">{plan.goal.event}</h3>
            <StatusBadge status={plan.status} />
          </div>

          <div className="plan-list__card-meta">
            <span>{plan.duration_weeks} weeks</span>
            <span>{plan.sessions_per_week} sessions/week</span>
            <time dateTime={plan.created_at}>
              {new Date(plan.created_at).toLocaleDateString()}
            </time>
          </div>

          <div className="plan-list__card-target">
            Target: {plan.goal.target_time}
          </div>

          <div className="plan-list__card-actions">
            {plan.status === 'draft' && (
              <button
                className="plan-list__btn plan-list__btn--activate"
                onClick={(e) => handleActivate(plan.plan_id, e)}
              >
                Activate
              </button>
            )}
            {plan.status === 'active' && (
              <button
                className="plan-list__btn plan-list__btn--archive"
                onClick={(e) => handleArchive(plan.plan_id, e)}
              >
                Archive
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: StructuredPlan['status'] }) {
  const classMap = {
    active: 'plan-list__badge--active',
    draft: 'plan-list__badge--draft',
    archived: 'plan-list__badge--archived',
  };

  return (
    <span className={`plan-list__badge ${classMap[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
