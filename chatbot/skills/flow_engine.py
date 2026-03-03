"""
Flow engine - executes a sequence of skills (a Flow) step by step.
Handles input mapping between steps, conditions, and error tracking.
"""
from django.utils import timezone


class FlowEngine:
    """Execute a flow (sequence of skills) and track progress."""

    def __init__(self, user, ai_model='llama3.2'):
        self.user = user
        self.ai_model = ai_model

    def execute_flow(self, flow, trigger_context=None, chat_session=None):
        """Execute a flow step by step. Returns FlowExecution record."""
        from chatbot.models import FlowExecution
        from .executor import SkillExecutor

        steps = flow.steps.all().order_by('order')
        execution = FlowExecution.objects.create(
            flow=flow,
            user=self.user,
            total_steps=steps.count(),
            triggered_by='manual',
            trigger_context=trigger_context or {},
            chat_session=chat_session,
        )

        executor = SkillExecutor(
            self.user,
            ai_model=self.ai_model,
            flow_execution=execution,
            chat_session=chat_session,
        )

        previous_output = trigger_context or {}
        step_results = []

        for step in steps:
            execution.current_step = step.order
            execution.save()

            # Check condition (skip if not met)
            if step.condition and not self._evaluate_condition(step.condition, previous_output):
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'skipped',
                    'reason': 'Condition not met',
                })
                continue

            # Map inputs from previous step output
            input_data = self._map_inputs(step.input_mapping, previous_output)

            # Merge with config overrides
            if step.config_override:
                input_data.update(step.config_override)

            try:
                output = executor.execute(step.skill, input_data)
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'completed',
                    'output': output if isinstance(output, (dict, list)) else str(output),
                })
                previous_output = output if isinstance(output, dict) else {'output': output}
            except Exception as e:
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'failed',
                    'error': str(e),
                })
                execution.status = 'failed'
                execution.error_message = str(e)
                execution.step_results = step_results
                execution.save()
                return execution

        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.step_results = step_results
        execution.save()
        return execution

    def _map_inputs(self, mapping, previous_output):
        """Map previous step output to current step input using mapping rules."""
        if not mapping:
            return dict(previous_output) if isinstance(previous_output, dict) else {}

        result = {}
        for target_key, source_expr in mapping.items():
            if isinstance(source_expr, str) and source_expr.startswith('$previous.'):
                field = source_expr[len('$previous.'):]
                if isinstance(previous_output, dict):
                    result[target_key] = previous_output.get(field)
                else:
                    result[target_key] = previous_output
            elif isinstance(source_expr, str) and source_expr == '$previous':
                result[target_key] = previous_output
            else:
                result[target_key] = source_expr
        return result

    def _evaluate_condition(self, condition, previous_output):
        """Evaluate a step condition against previous output."""
        field_expr = condition.get('field', '')
        operator = condition.get('operator', '==')
        threshold = condition.get('value', condition.get('threshold', 0))

        # Resolve field value
        if isinstance(field_expr, str) and field_expr.startswith('$previous.'):
            field_name = field_expr[len('$previous.'):]
            value = previous_output.get(field_name, 0) if isinstance(previous_output, dict) else 0
        else:
            value = field_expr

        # Convert to numeric if possible
        try:
            value = float(value)
            threshold = float(threshold)
        except (ValueError, TypeError):
            pass

        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return True
