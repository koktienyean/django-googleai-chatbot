"""
Shared tool dispatch - routes a tool name + args to the correct function.
Used by all AI backends (Claude, Gemini, Ollama) so tool execution is in one place.
"""


def execute_tool(user, function_name, function_args):
    """Execute a tool by name and return the result dict.

    Args:
        user: Django User instance (for data scoping)
        function_name: Tool name string from AI response
        function_args: Dict of arguments from AI response

    Returns:
        dict with result data
    """
    # Import here to avoid circular imports (these live in views.py for now)
    from chatbot.views import (
        search_my_chats, get_chat_statistics, get_recent_conversations,
        search_by_date_range, get_session_summary, list_my_sessions,
        create_task, list_my_tasks, get_task_details,
        update_task_status, update_task_priority, delete_task,
        get_pending_tasks, get_task_summary,
        create_recurring_task_tool, list_recurring_tasks_tool,
        skip_recurring_instance_tool,
        get_notification_summary_tool, set_notification_preference_tool,
        get_productivity_metrics_tool, get_task_insights_tool,
        generate_weekly_report_tool,
    )

    # Chat history tools
    if function_name == 'search_chats_tool':
        return search_my_chats(user, function_args.get('keyword'), function_args.get('limit', 5))
    elif function_name == 'get_stats_tool':
        return get_chat_statistics(user)
    elif function_name == 'get_recent_tool':
        return get_recent_conversations(user, function_args.get('limit', 5))
    elif function_name == 'search_dates_tool':
        return search_by_date_range(user, function_args.get('start_date'), function_args.get('end_date'))
    elif function_name == 'get_session_tool':
        return get_session_summary(user, function_args.get('session_id'))
    elif function_name == 'list_sessions_tool':
        return list_my_sessions(user, function_args.get('limit', 10))

    # Task management tools
    elif function_name == 'create_task_tool':
        return create_task(user, function_args.get('title'), function_args.get('description', ''),
                          function_args.get('priority', 'medium'), function_args.get('due_date_str'))
    elif function_name == 'list_tasks_tool':
        return list_my_tasks(user, function_args.get('status', 'all'), function_args.get('limit', 10))
    elif function_name == 'get_task_details_tool':
        return get_task_details(user, function_args.get('task_id'))
    elif function_name == 'update_task_status_tool':
        return update_task_status(user, function_args.get('task_id'), function_args.get('status'))
    elif function_name == 'update_task_priority_tool':
        return update_task_priority(user, function_args.get('task_id'), function_args.get('priority'))
    elif function_name == 'delete_task_tool':
        return delete_task(user, function_args.get('task_id'))
    elif function_name == 'get_pending_tasks_tool':
        return get_pending_tasks(user, function_args.get('limit', 5))
    elif function_name == 'get_task_summary_tool':
        return get_task_summary(user)

    # Recurring tasks (Phase 4)
    # Handle both old wrapper names and new canonical names
    elif function_name in ('create_recurring_task_tool', 'create_recurring_task_tool_wrapper'):
        return create_recurring_task_tool(user, function_args.get('title'), function_args.get('description', ''),
                                         function_args.get('priority', 'medium'), function_args.get('frequency', 'weekly'),
                                         function_args.get('start_date_str'), function_args.get('end_date_str'))
    elif function_name in ('list_recurring_tasks_tool', 'list_recurring_tasks_tool_wrapper'):
        return list_recurring_tasks_tool(user)
    elif function_name in ('skip_recurring_instance_tool', 'skip_recurring_instance_tool_wrapper'):
        return skip_recurring_instance_tool(user, function_args.get('template_id'))

    # Notifications (Phase 4)
    elif function_name in ('get_notification_summary_tool', 'get_notification_summary_tool_wrapper'):
        return get_notification_summary_tool(user)
    elif function_name in ('set_notification_preference_tool', 'set_notification_preference_tool_wrapper'):
        return set_notification_preference_tool(user, function_args.get('preference_type'), function_args.get('enabled'))

    # Analytics (Phase 5)
    elif function_name in ('get_productivity_metrics_tool', 'get_productivity_metrics_tool_wrapper'):
        return get_productivity_metrics_tool(user)
    elif function_name in ('get_task_insights_tool', 'get_task_insights_tool_wrapper'):
        return get_task_insights_tool(user)
    elif function_name in ('generate_weekly_report_tool', 'generate_weekly_report_tool_wrapper'):
        return generate_weekly_report_tool(user)

    # Data Query & Reporting (Phase C)
    elif function_name == 'query_data_tool':
        from chatbot.tools.query_engine import execute_query
        return execute_query(
            user,
            function_args.get('data_type'),
            filters=function_args.get('filters'),
            aggregation=function_args.get('aggregation', 'none'),
            order_by=function_args.get('order_by', '-created_at'),
            limit=function_args.get('limit', 20),
        )
    elif function_name == 'generate_report_tool':
        from chatbot.tools.report_builder import ReportBuilder
        builder = ReportBuilder(user)
        return builder.generate_report(
            report_type=function_args.get('report_type'),
            data_type=function_args.get('data_type'),
            time_range=function_args.get('time_range', 'last_30_days'),
            output_format=function_args.get('format', 'markdown'),
        )

    # Skill & Flow Engine (Phase D)
    elif function_name == 'list_skills_tool':
        from chatbot.models import Skill
        skill_type = function_args.get('skill_type', 'all')
        qs = Skill.objects.filter(user=user)
        if skill_type != 'all':
            qs = qs.filter(skill_type=skill_type)
        return {
            'skills': list(qs.values(
                'id', 'name', 'description', 'skill_type', 'is_system',
                'version', 'avg_rating', 'total_executions', 'success_rate'
            ))
        }

    elif function_name == 'create_skill_tool':
        from chatbot.models import Skill
        skill, created = Skill.objects.get_or_create(
            user=user,
            name=function_args.get('name'),
            defaults={
                'description': function_args.get('description', ''),
                'skill_type': function_args.get('skill_type'),
                'config': function_args.get('config', {}),
            }
        )
        if not created:
            return {'status': 'exists', 'message': f'Skill "{skill.name}" already exists', 'skill_id': skill.id}
        return {'status': 'created', 'skill_id': skill.id, 'name': skill.name}

    elif function_name == 'list_flows_tool':
        from chatbot.models import Flow
        flows = Flow.objects.filter(user=user, is_active=True)
        result = []
        for f in flows:
            steps = list(f.steps.order_by('order').values('order', 'skill__name'))
            result.append({
                'id': f.id, 'name': f.name, 'description': f.description,
                'step_count': len(steps),
                'steps': [{'order': s['order'], 'skill': s['skill__name']} for s in steps],
            })
        return {'flows': result}

    elif function_name == 'create_flow_tool':
        from chatbot.models import Flow, FlowStep, Skill
        flow = Flow.objects.create(
            user=user,
            name=function_args.get('name'),
            description=function_args.get('description', ''),
        )
        steps_data = function_args.get('steps', [])
        created_steps = []
        for i, step_def in enumerate(steps_data):
            skill_name = step_def.get('skill_name', step_def.get('skill', ''))
            try:
                skill = Skill.objects.get(user=user, name=skill_name)
            except Skill.DoesNotExist:
                continue
            FlowStep.objects.create(
                flow=flow, skill=skill, order=i + 1,
                input_mapping=step_def.get('input_mapping', {}),
                config_override=step_def.get('config_override', {}),
                condition=step_def.get('condition', {}),
            )
            created_steps.append({'order': i + 1, 'skill': skill_name})
        return {'status': 'created', 'flow_id': flow.id, 'name': flow.name, 'steps': created_steps}

    elif function_name == 'run_flow_tool':
        from chatbot.models import Flow
        from chatbot.skills.flow_engine import FlowEngine
        flow_name = function_args.get('flow_name')
        context = function_args.get('context', {})
        try:
            flow = Flow.objects.get(user=user, name=flow_name, is_active=True)
        except Flow.DoesNotExist:
            return {'error': f'Flow "{flow_name}" not found'}
        engine = FlowEngine(user)
        execution = engine.execute_flow(flow, trigger_context=context)
        return {
            'execution_id': execution.id,
            'status': execution.status,
            'steps_completed': len([s for s in execution.step_results if s.get('status') == 'completed']),
            'total_steps': execution.total_steps,
            'step_results': execution.step_results,
            'error': execution.error_message or None,
        }

    elif function_name == 'submit_skill_feedback_tool':
        from chatbot.models import SkillExecutionLog, SkillFeedback
        try:
            log = SkillExecutionLog.objects.get(id=function_args.get('execution_log_id'), user=user)
        except SkillExecutionLog.DoesNotExist:
            return {'error': 'Execution log not found'}
        feedback, created = SkillFeedback.objects.get_or_create(
            user=user, execution_log=log,
            defaults={
                'skill': log.skill,
                'rating': function_args.get('rating'),
                'comment': function_args.get('comment', ''),
                'expected_output': function_args.get('expected_output', ''),
            }
        )
        if not created:
            return {'status': 'already_exists', 'feedback_id': feedback.id}
        log.skill.update_stats()
        return {'status': 'submitted', 'feedback_id': feedback.id, 'skill': log.skill.name}

    elif function_name == 'get_skill_stats_tool':
        from chatbot.models import Skill
        from chatbot.skills.improver import SkillImprover
        skill_name = function_args.get('skill_name')
        try:
            skill = Skill.objects.get(user=user, name=skill_name)
        except Skill.DoesNotExist:
            return {'error': f'Skill "{skill_name}" not found'}
        improver = SkillImprover(user)
        return improver.get_skill_stats(skill)

    elif function_name == 'improve_skill_tool':
        from chatbot.models import Skill
        from chatbot.skills.improver import SkillImprover
        skill_name = function_args.get('skill_name')
        try:
            skill = Skill.objects.get(user=user, name=skill_name)
        except Skill.DoesNotExist:
            return {'error': f'Skill "{skill_name}" not found'}
        improver = SkillImprover(user)
        return improver.suggest_improvement(skill)

    # External DB Query (SIG_Chart)
    elif function_name == 'get_db_schema_tool':
        from chatbot.tools.sig_query import get_schema
        return get_schema()
    elif function_name == 'get_sample_data_tool':
        from chatbot.tools.sig_query import get_sample_data
        return get_sample_data(function_args.get('table'), function_args.get('limit', 5))
    elif function_name == 'execute_sql_tool':
        from chatbot.tools.sig_query import execute_sql
        return execute_sql(function_args.get('sql'), function_args.get('limit', 100))

    else:
        return {'error': f'Unknown function: {function_name}'}
