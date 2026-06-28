import { useState, useEffect } from 'react';
import { TrainingGoalForm } from '../components/TrainingGoalForm';
import { TrainingPlanResult } from '../components/TrainingPlanResult';
import { generateTrainingPlan } from '../api/upload';
import { getUserSessions } from '../api/sessionService';
import { TrainingGoal, TrainingPlan } from '../types';
import './TrainingPlansPage.css';

/**
 * Training Plans page — displays goal form and generated plans.
 * Uses the latest session metrics for plan generation.
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4
 */
export function TrainingPlansPage() {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  const handleSubmit = async (goal: TrainingGoal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateTrainingPlan(metrics, goal);
      setPlan(result);
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
    </div>
  );
}
