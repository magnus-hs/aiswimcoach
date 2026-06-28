import { useNavigate } from 'react-router-dom';
import { StructuredPlanForm } from '../components/StructuredPlanForm';
import { StructuredPlan } from '../api/planService';
import './NewPlanPage.css';

/**
 * Page wrapper for the structured plan generation form.
 * On successful generation, navigates to the new plan's detail view.
 */
export function NewPlanPage() {
  const navigate = useNavigate();

  const handlePlanGenerated = (plan: StructuredPlan) => {
    navigate(`/plans/${plan.plan_id}`);
  };

  return (
    <div className="new-plan-page">
      <div className="new-plan-page__card">
        <StructuredPlanForm onPlanGenerated={handlePlanGenerated} />
      </div>
    </div>
  );
}
