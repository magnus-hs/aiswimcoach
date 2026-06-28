import { useState, useEffect } from 'react';
import { TrainingGoalForm } from '../components/TrainingGoalForm';
import { TrainingPlanResult } from '../components/TrainingPlanResult';
import { generateTrainingPlan } from '../api/upload';
import { getUserSessions, getUserPlans, SavedPlan } from '../api/sessionService';
import { TrainingGoal, TrainingPlan } from '../types';
import './TrainingPlansPage.css';

/**
 * Training Plans page — displays goal form, generated plans, and saved plan history.
 * Uses the latest session metrics for plan generation.
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4
 */
export function TrainingPlansPage() {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedPlans, setSavedPlans] = useState<SavedPlan[]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [metrics, setMetrics] = useState<{
    pace: number;
    swolf: number;
    stroke_rate: number;
  }>({ pace: 120, swolf: 40, stroke_rate: 30 });

  useEffect(() => {
    async function loadLatestMetrics() {
      try {
        const sessions = await getUserSessions();
        if (sessions.length > 0) {
          const latest = sessions[0];
          setMetrics({
            pace: latest.average_pace_per_100m,
            swolf: latest.swolf_score,
            stroke_rate: latest.stroke_rate,
          });
        }
      } catch {
        // Use default metrics if sessions cannot be fetched
      }
    }
    loadLatestMetrics();
  }, []);

  useEffect(() => {
    async function loadSavedPlans() {
      try {
        const plans = await getUserPlans();
        setSavedPlans(plans);
      } catch {
        // Silently fail — saved plans are non-critical
      } finally {
        setPlansLoading(false);
      }
    }
    loadSavedPlans();
  }, []);

  const handleSubmit = async (goal: TrainingGoal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateTrainingPlan(metrics, goal);
      setPlan(result);
      // Refetch saved plans to include the newly generated one
      try {
        const plans = await getUserPlans();
        setSavedPlans(plans);
      } catch {
        // Non-critical
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to generate training plan.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="training-plans-page">
      <h1 className="training-plans-page__heading">Training Plans</h1>

      <div className="training-plans-page__card">
        <TrainingGoalForm onSubmit={handleSubmit} loading={loading} />
        {error && (
          <p className="training-plans-page__error" role="alert">
            {error}
          </p>
        )}
      </div>

      {plan && (
        <div className="training-plans-page__card">
          <TrainingPlanResult plan={plan} />
        </div>
      )}

      <section className="training-plans-page__saved" aria-label="Saved Plans">
        <h2 className="training-plans-page__section-heading">Saved Plans</h2>
        {plansLoading ? (
          <p className="training-plans-page__loading">Loading saved plans…</p>
        ) : savedPlans.length === 0 ? (
          <p className="training-plans-page__empty">
            No saved plans yet. Generate a training plan above to get started.
          </p>
        ) : (
          <div className="training-plans-page__plan-list">
            {savedPlans.map((savedPlan) => (
              <div key={savedPlan.plan_id} className="training-plans-page__plan-card">
                <div className="training-plans-page__plan-header">
                  <h3 className="training-plans-page__plan-title">
                    {savedPlan.plan.session_title}
                  </h3>
                  <time className="training-plans-page__plan-date" dateTime={savedPlan.created_at}>
                    {new Date(savedPlan.created_at).toLocaleDateString()}
                  </time>
                </div>
                <div className="training-plans-page__plan-meta">
                  <span className="training-plans-page__plan-event">
                    {savedPlan.goal.event}
                  </span>
                  <span className="training-plans-page__plan-target">
                    Target: {savedPlan.goal.target_time}
                  </span>
                  <span className="training-plans-page__plan-distance">
                    {savedPlan.plan.total_distance}m
                  </span>
                </div>
                {savedPlan.plan.goal_likelihood && (
                  <p className="training-plans-page__plan-likelihood">
                    {savedPlan.plan.goal_likelihood}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
