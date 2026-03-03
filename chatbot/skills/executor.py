"""
Skill executor - runs a single skill and logs the execution.
Supports: query, transform, generate, action, condition skill types.
"""
import time


class SkillExecutor:
    """Execute a skill with automatic logging to SkillExecutionLog."""

    def __init__(self, user, ai_model='llama3.2', flow_execution=None, chat_session=None):
        self.user = user
        self.ai_model = ai_model
        self.flow_execution = flow_execution
        self.chat_session = chat_session

    def execute(self, skill, input_data=None):
        """Execute a skill, log the result, and return output."""
        from chatbot.models import SkillExecutionLog

        start = time.time()
        log = SkillExecutionLog(
            user=self.user,
            skill=skill,
            input_data=input_data or {},
            flow_execution=self.flow_execution,
            chat_session=self.chat_session,
            model_used=self.ai_model if skill.skill_type == 'generate' else '',
        )

        try:
            output = self._dispatch(skill, input_data)
            log.output_data = output if isinstance(output, dict) else {'output': str(output)}
            log.status = 'success'
            log.duration_ms = int((time.time() - start) * 1000)
            log.save()

            # Update cached stats
            skill.total_executions = (skill.total_executions or 0) + 1
            skill.save(update_fields=['total_executions'])

            return output
        except Exception as e:
            log.status = 'error'
            log.error_message = str(e)
            log.duration_ms = int((time.time() - start) * 1000)
            log.save()

            skill.total_executions = (skill.total_executions or 0) + 1
            skill.save(update_fields=['total_executions'])
            raise

    def _dispatch(self, skill, input_data):
        """Route to the correct executor based on skill type."""
        if skill.skill_type == 'query':
            return self._execute_query(skill, input_data)
        elif skill.skill_type == 'transform':
            return self._execute_transform(skill, input_data)
        elif skill.skill_type == 'generate':
            return self._execute_generate(skill, input_data)
        elif skill.skill_type == 'action':
            return self._execute_action(skill, input_data)
        elif skill.skill_type == 'condition':
            return self._execute_condition(skill, input_data)
        else:
            raise ValueError(f"Unknown skill type: {skill.skill_type}")

    def _execute_query(self, skill, input_data):
        """Execute a data query skill."""
        from chatbot.tools.query_engine import execute_query

        config = dict(skill.config)
        if input_data:
            # Allow input_data to override config
            if 'filters' in input_data:
                config['filters'] = input_data['filters']
            if 'aggregation' in input_data:
                config['aggregation'] = input_data['aggregation']
            if 'limit' in input_data:
                config['limit'] = input_data['limit']

        return execute_query(
            self.user,
            data_type=config.get('data_type', 'tasks'),
            filters=config.get('filters'),
            aggregation=config.get('aggregation', 'none'),
            order_by=config.get('order_by', '-created_at'),
            limit=config.get('limit', 20),
        )

    def _execute_transform(self, skill, input_data):
        """Execute a data transformation skill (via AI)."""
        operation = skill.config.get('operation', 'summarize')
        text = (input_data or {}).get('text', str(input_data))

        from chatbot.views import ask_ai
        prompt = f"Perform the following operation on this data: {operation}\n\nData:\n{text}"
        return {'output': ask_ai(prompt, model=self.ai_model, user=self.user)}

    def _execute_generate(self, skill, input_data):
        """Execute an AI generation skill."""
        from chatbot.views import ask_ai

        prompt = skill.config.get('prompt_template', '')
        # Substitute variables from input_data
        for key, value in (input_data or {}).items():
            prompt = prompt.replace(f'${{{key}}}', str(value))

        model = skill.config.get('model', self.ai_model)
        result = ask_ai(prompt, model=model, user=self.user)
        return {'output': result}

    def _execute_action(self, skill, input_data):
        """Execute a system action skill."""
        action = skill.config.get('action_type')
        args = input_data or {}

        if action == 'create_task':
            from chatbot.views import create_task
            return create_task(
                self.user,
                args.get('title', 'Untitled'),
                args.get('description', ''),
                args.get('priority', 'medium'),
                args.get('due_date_str'),
            )
        elif action == 'update_task':
            from chatbot.views import update_task_status, update_task_priority
            result = {}
            if 'status' in args:
                result.update(update_task_status(self.user, args['task_id'], args['status']))
            if 'priority' in args:
                result.update(update_task_priority(self.user, args['task_id'], args['priority']))
            return result
        else:
            raise ValueError(f"Unknown action type: {action}")

    def _execute_condition(self, skill, input_data):
        """Evaluate a condition and return boolean result."""
        config = skill.config
        field = config.get('field', 'count')
        operator = config.get('operator', '>')
        threshold = config.get('threshold', 0)

        value = (input_data or {}).get(field, 0)
        if isinstance(value, str):
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0

        if operator == '>':
            result = value > threshold
        elif operator == '<':
            result = value < threshold
        elif operator == '>=':
            result = value >= threshold
        elif operator == '<=':
            result = value <= threshold
        elif operator == '==':
            result = value == threshold
        elif operator == '!=':
            result = value != threshold
        else:
            result = False

        return {'result': result, 'value': value, 'threshold': threshold}
