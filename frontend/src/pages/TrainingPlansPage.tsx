import { Link } from 'react-router-dom';
import { PlanListView } from '../components/PlanListView';
import './TrainingPlansPage.css';

/**
 * Training Plans page — displays structured plan list with navigation
 * to create new plans and manage personal bests.
 * Validates: Requirements 5.1, 5.4, 5.5
 */
export function TrainingPlansPage() {
  return (
    <div className="training-plans-page">
      <div className="training-plans-page__header">
        <h1 className="training-plans-page__heading">Training Plans</h1>
        <div className="training-plans-page__actions">
          <Link to="/plans/new" className="training-plans-page__btn training-plans-page__btn--primary">
            + Create New Plan
          </Link>
          <Link to="/personal-bests" className="training-plans-page__btn training-plans-page__btn--secondary">
            🏆 Personal Bests
          </Link>
        </div>
      </div>

      <PlanListView />
    </div>
  );
}
