# Plan 03: AI Skill & Flow Engine

**Status**: Planning
**Priority**: High
**Depends on**: 01-ollama-integration, 02-data-query-reporting

---

## Goal

Allow users to **define reusable AI skills** (atomic actions the AI can perform) and **chain them into flows** (sequential pipelines that execute step-by-step). This turns the chatbot from a Q&A tool into a **task automation engine**.

## Concept

### Skill = Single Action
A skill is one atomic thing the AI can do:
- "Summarize text"
- "Query overdue tasks"
- "Draft an email"
- "Classify priority"
- "Extract key dates from text"

### Flow = Sequence of Skills
A flow chains skills together, passing output from one step as input to the next:
```
Flow: "Daily Review"
  Step 1: Query overdue tasks        -> [list of tasks]
  Step 2: Summarize task status      -> [summary text]
  Step 3: Identify top 3 priorities  -> [priority list]
  Step 4: Generate action plan       -> [plan text]
  Step 5: Present final report       -> [formatted output]
```

## Data Model

### New Models

```python
# chatbot/models.py

class Skill(models.Model):
    """A reusable AI skill - an atomic action the AI can perform"""

    SKILL_TYPES = [
        ('query', 'Data Query'),          # Query Django data
        ('transform', 'Data Transform'),   # Transform/process data
        ('generate', 'AI Generate'),       # Generate text via LLM
        ('action', 'System Action'),       # Perform a system action (create task, etc.)
        ('condition', 'Condition Check'),   # Evaluate a condition (for branching)
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    skill_type = models.CharField(max_length=20, choices=SKILL_TYPES)

    # Skill configuration
    config = models.JSONField(default=dict, help_text="""
        For 'query': {data_type, filters, aggregation}
        For 'transform': {operation: 'summarize'|'extract'|'classify'|'format'}
        For 'generate': {prompt_template, model}
        For 'action': {action_type: 'create_task'|'update_task'|'send_notification'}
        For 'condition': {check_type, threshold}
    """)

    # Input/output schema for chaining
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)

    # Whether this is a system-provided skill or user-created
    is_system = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')

    def __str__(self):
        return f'{self.name} ({self.get_skill_type_display()})'


class Flow(models.Model):
    """A sequential pipeline of skills"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flows')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Optional: trigger conditions
    trigger = models.JSONField(default=dict, blank=True, help_text="""
        {type: 'manual'|'scheduled'|'event', schedule: '0 9 * * *', event: 'task_created'}
    """)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.steps.count()} steps)'


class FlowStep(models.Model):
    """A single step in a flow, linked to a skill"""

    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='steps')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='flow_steps')
    order = models.IntegerField()

    # How to map output from previous step to input of this step
    input_mapping = models.JSONField(default=dict, blank=True, help_text="""
        Maps previous step outputs to this step's inputs.
        Example: {"text_to_summarize": "$previous.output"}
    """)

    # Override skill config for this specific step
    config_override = models.JSONField(default=dict, blank=True)

    # Condition: only run this step if condition is met
    condition = models.JSONField(default=dict, blank=True, help_text="""
        Example: {"field": "$previous.count", "operator": ">", "value": 0}
    """)

    class Meta:
        ordering = ['order']
        unique_together = ('flow', 'order')

    def __str__(self):
        return f'Step {self.order}: {self.skill.name}'


class FlowExecution(models.Model):
    """Tracks a single execution of a flow"""

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='executions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    current_step = models.IntegerField(default=0)
    total_steps = models.IntegerField()

    # Store input/output for each step
    step_results = models.JSONField(default=list, help_text="""
        [{step: 1, skill: 'query_tasks', status: 'completed', output: {...}}, ...]
    """)

    # Trigger context
    triggered_by = models.CharField(max_length=50, default='manual')
    trigger_context = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Link to chat session where flow was triggered
    chat_session = models.ForeignKey(ChatSession, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.flow.name} - {self.get_status_display()}'
```

## Implementation Plan

### Phase 1: Skill System

**1.1 System-provided skills (built-in)**

Create default skills that mirror existing tool functions:

| Skill Name | Type | Description |
|------------|------|-------------|
| `query_tasks` | query | Query tasks with filters |
| `query_chats` | query | Search chat history |
| `task_summary` | query | Get task counts by status |
| `summarize_text` | generate | Summarize given text using AI |
| `classify_priority` | generate | Classify priority from text |
| `extract_dates` | transform | Extract dates from text |
| `create_task` | action | Create a new task |
| `update_task` | action | Update task status/priority |
| `check_count` | condition | Check if count > threshold |

**1.2 Skill executor**

```python
# chatbot/skills/executor.py

class SkillExecutor:
    def __init__(self, user, ai_model='llama3.2'):
        self.user = user
        self.ai_model = ai_model

    def execute(self, skill, input_data=None):
        """Execute a single skill and return result"""

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

    def _execute_query(self, skill, input_data):
        config = {**skill.config, **(input_data or {})}
        return execute_query(self.user, **config)

    def _execute_generate(self, skill, input_data):
        prompt = skill.config.get('prompt_template', '')
        # Substitute variables from input_data
        for key, value in (input_data or {}).items():
            prompt = prompt.replace(f'${{{key}}}', str(value))
        model = skill.config.get('model', self.ai_model)
        return ask_ai(prompt, model=model, user=self.user)

    def _execute_action(self, skill, input_data):
        action = skill.config.get('action_type')
        if action == 'create_task':
            return create_task(self.user, **input_data)
        elif action == 'update_task':
            return update_task_status(self.user, **input_data)
        # ... etc

    def _execute_condition(self, skill, input_data):
        field = skill.config.get('field')
        operator = skill.config.get('operator')
        threshold = skill.config.get('threshold')
        value = input_data.get(field, 0)
        if operator == '>': return {'result': value > threshold, 'value': value}
        if operator == '<': return {'result': value < threshold, 'value': value}
        if operator == '==': return {'result': value == threshold, 'value': value}
        return {'result': False}
```

### Phase 2: Flow Engine

**2.1 Flow executor**

```python
# chatbot/skills/flow_engine.py

class FlowEngine:
    def __init__(self, user, ai_model='llama3.2'):
        self.user = user
        self.skill_executor = SkillExecutor(user, ai_model)

    def execute_flow(self, flow, trigger_context=None):
        """Execute a flow step by step"""

        # Create execution record
        steps = flow.steps.all().order_by('order')
        execution = FlowExecution.objects.create(
            flow=flow,
            user=self.user,
            total_steps=steps.count(),
            triggered_by='manual',
            trigger_context=trigger_context or {}
        )

        previous_output = trigger_context or {}
        step_results = []

        for step in steps:
            execution.current_step = step.order
            execution.save()

            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, previous_output):
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'skipped',
                    'reason': 'Condition not met'
                })
                continue

            # Map inputs from previous output
            input_data = self._map_inputs(step.input_mapping, previous_output)

            # Merge with config overrides
            if step.config_override:
                input_data.update(step.config_override)

            try:
                output = self.skill_executor.execute(step.skill, input_data)
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'completed',
                    'output': output
                })
                previous_output = output if isinstance(output, dict) else {'output': output}
            except Exception as e:
                step_results.append({
                    'step': step.order,
                    'skill': step.skill.name,
                    'status': 'failed',
                    'error': str(e)
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
        """Map previous step output to current step input using mapping rules"""
        result = {}
        for target_key, source_expr in mapping.items():
            if isinstance(source_expr, str) and source_expr.startswith('$previous.'):
                field = source_expr.replace('$previous.', '')
                result[target_key] = previous_output.get(field)
            else:
                result[target_key] = source_expr
        return result

    def _evaluate_condition(self, condition, previous_output):
        """Evaluate a step condition"""
        field = condition.get('field', '')
        if field.startswith('$previous.'):
            field = field.replace('$previous.', '')
            value = previous_output.get(field, 0)
        else:
            value = condition.get('value', 0)
        operator = condition.get('operator', '==')
        threshold = condition.get('threshold', 0)

        if operator == '>': return value > threshold
        if operator == '<': return value < threshold
        if operator == '>=': return value >= threshold
        if operator == '==': return value == threshold
        if operator == '!=': return value != threshold
        return True
```

### Phase 3: AI-Powered Flow Creation via Chat

Users can create skills and flows through natural language:

```
User: "Create a flow called 'Morning Review' that:
       1. Gets my overdue tasks
       2. Summarizes them
       3. Suggests priorities for today"

AI: [calls create_flow_tool with steps mapped to skills]
AI: "Created flow 'Morning Review' with 3 steps. Run it anytime by saying 'run Morning Review'."

User: "Run Morning Review"
AI: [executes flow step-by-step, shows progress]
AI: "Flow complete! Here's your morning review:
     - 3 overdue tasks found
     - Summary: ...
     - Suggested priorities: ..."
```

**3.1 New AI tools for skill/flow management**

```python
tools = [
    {
        "name": "create_skill_tool",
        "description": "Create a reusable AI skill",
        "input_schema": {
            "properties": {
                "name": {"type": "string"},
                "skill_type": {"type": "string", "enum": ["query", "transform", "generate", "action", "condition"]},
                "config": {"type": "object"},
                "description": {"type": "string"}
            }
        }
    },
    {
        "name": "create_flow_tool",
        "description": "Create a sequential flow from existing skills",
        "input_schema": {
            "properties": {
                "name": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill_name": {"type": "string"},
                            "input_mapping": {"type": "object"},
                            "condition": {"type": "object"}
                        }
                    }
                }
            }
        }
    },
    {
        "name": "run_flow_tool",
        "description": "Execute a named flow",
        "input_schema": {
            "properties": {
                "flow_name": {"type": "string"},
                "context": {"type": "object"}
            },
            "required": ["flow_name"]
        }
    },
    {
        "name": "list_flows_tool",
        "description": "List all user's flows",
        "input_schema": {"properties": {}}
    },
    {
        "name": "list_skills_tool",
        "description": "List all available skills",
        "input_schema": {"properties": {}}
    }
]
```

### Phase 4: Scheduled Flows (Optional)

Allow flows to run on a schedule using Django management commands + cron:

```python
# management/commands/run_scheduled_flows.py
# Triggered by cron: */15 * * * * python manage.py run_scheduled_flows

class Command(BaseCommand):
    def handle(self, *args, **options):
        now = timezone.now()
        due_flows = Flow.objects.filter(
            is_active=True,
            trigger__type='scheduled',
            # parse cron and check if due
        )
        for flow in due_flows:
            engine = FlowEngine(flow.user)
            engine.execute_flow(flow)
```

---

## Example Flows

### Flow 1: Daily Task Review
```json
{
    "name": "Daily Task Review",
    "steps": [
        {"skill": "query_tasks", "config": {"filters": {"status": "pending"}, "aggregation": "group_by_priority"}},
        {"skill": "query_tasks", "config": {"filters": {"status": "pending", "is_overdue": true}}},
        {"skill": "summarize_text", "input_mapping": {"text": "$previous.output"}},
        {"skill": "classify_priority", "input_mapping": {"tasks": "$previous.output"}}
    ]
}
```

### Flow 2: Weekly Report Generation
```json
{
    "name": "Weekly Report",
    "steps": [
        {"skill": "task_summary"},
        {"skill": "query_tasks", "config": {"filters": {"status": "completed", "date_from": "last_week"}}},
        {"skill": "query_chats", "config": {"filters": {"date_from": "last_week"}, "aggregation": "count"}},
        {"skill": "summarize_text", "input_mapping": {"text": "$previous.output"}, "config": {"prompt_template": "Generate a weekly productivity report from: ${text}"}}
    ]
}
```

### Flow 3: Smart Task Triage
```json
{
    "name": "Smart Triage",
    "steps": [
        {"skill": "query_tasks", "config": {"filters": {"status": "pending"}}},
        {"skill": "check_count", "config": {"field": "count", "operator": ">", "threshold": 0}},
        {"skill": "classify_priority", "input_mapping": {"tasks": "$previous.output"}},
        {"skill": "update_task", "input_mapping": {"updates": "$previous.output"}}
    ]
}
```

---

## Phase 5: Execution Logging & Observability

Every skill call is recorded so both user and AI can review what happened, spot patterns, and improve.

### 5.1 New Model: SkillExecutionLog

```python
class SkillExecutionLog(models.Model):
    """Records every single skill call with full input/output for review"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_logs')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='execution_logs')

    # What was asked and what came back
    input_data = models.JSONField(default=dict, help_text="The input passed to the skill")
    output_data = models.JSONField(default=dict, help_text="The result returned by the skill")

    # Execution context
    flow_execution = models.ForeignKey(FlowExecution, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='skill_logs', help_text="If run as part of a flow")
    chat_session = models.ForeignKey(ChatSession, null=True, blank=True, on_delete=models.SET_NULL)
    model_used = models.CharField(max_length=100, blank=True, help_text="AI model used (if generate type)")

    # Performance
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'), ('error', 'Error'), ('timeout', 'Timeout')
    ], default='success')
    duration_ms = models.IntegerField(default=0, help_text="Execution time in milliseconds")
    error_message = models.TextField(blank=True)

    # Timestamps
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['user', '-executed_at']),
            models.Index(fields=['skill', '-executed_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.skill.name} - {self.status} - {self.executed_at:%Y-%m-%d %H:%M}'
```

### 5.2 Logging in SkillExecutor

```python
# chatbot/skills/executor.py - updated
import time

class SkillExecutor:
    def execute(self, skill, input_data=None):
        start = time.time()
        log = SkillExecutionLog(
            user=self.user,
            skill=skill,
            input_data=input_data or {},
            model_used=self.ai_model if skill.skill_type == 'generate' else '',
        )
        try:
            output = self._dispatch(skill, input_data)
            log.output_data = output if isinstance(output, dict) else {'output': str(output)}
            log.status = 'success'
            log.duration_ms = int((time.time() - start) * 1000)
            log.save()
            return output
        except Exception as e:
            log.status = 'error'
            log.error_message = str(e)
            log.duration_ms = int((time.time() - start) * 1000)
            log.save()
            raise
```

---

## Phase 6: User Feedback & Self-Improvement

Users can rate skill outputs and give feedback. The system uses this to improve skill prompts and configs over time.

### 6.1 New Model: SkillFeedback

```python
class SkillFeedback(models.Model):
    """User feedback on a skill execution - drives self-improvement"""

    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_feedback')
    execution_log = models.OneToOneField(SkillExecutionLog, on_delete=models.CASCADE,
                                          related_name='feedback')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='feedback')

    # User rating and comment
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, help_text="What was wrong or could be better?")

    # Suggested correction
    expected_output = models.TextField(blank=True,
        help_text="What should the output have been? (optional)")

    # Did this feedback lead to a skill update?
    applied = models.BooleanField(default=False,
        help_text="Whether this feedback was used to update the skill")
    applied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['skill', '-created_at']),
            models.Index(fields=['skill', 'rating']),
            models.Index(fields=['applied']),
        ]

    def __str__(self):
        return f'{self.skill.name} - {self.get_rating_display()} - {self.user.username}'
```

### 6.2 Skill Improvement Stats (computed fields on Skill)

```python
# Add to Skill model
class Skill(models.Model):
    # ... existing fields ...

    # Improvement tracking
    version = models.IntegerField(default=1, help_text="Increments when skill config is updated from feedback")
    avg_rating = models.FloatField(default=0.0, help_text="Cached average feedback rating")
    total_executions = models.IntegerField(default=0, help_text="Cached total execution count")
    success_rate = models.FloatField(default=0.0, help_text="Cached success rate percentage")
    last_improved_at = models.DateTimeField(null=True, blank=True)

    def update_stats(self):
        """Recalculate cached stats from logs and feedback"""
        from django.db.models import Avg, Count, Q
        logs = self.execution_logs.all()
        self.total_executions = logs.count()
        if self.total_executions > 0:
            self.success_rate = logs.filter(status='success').count() / self.total_executions * 100
        feedback = self.feedback.all()
        if feedback.exists():
            self.avg_rating = feedback.aggregate(avg=Avg('rating'))['avg'] or 0.0
        self.save()
```

### 6.3 Self-Improvement Flow (AI-assisted)

When a skill has low ratings, the AI can suggest improvements:

```python
# chatbot/skills/improver.py

class SkillImprover:
    def __init__(self, user, ai_model='llama3.2'):
        self.user = user
        self.ai_model = ai_model

    def suggest_improvement(self, skill):
        """Analyze feedback and suggest config/prompt improvements"""
        # Get recent negative feedback
        bad_feedback = SkillFeedback.objects.filter(
            skill=skill, rating__lte=2
        ).order_by('-created_at')[:10]

        if not bad_feedback.exists():
            return None

        # Build analysis prompt
        prompt = f"""Analyze this AI skill and its feedback to suggest improvements.

Skill: {skill.name}
Type: {skill.skill_type}
Current Config: {skill.config}
Version: {skill.version}
Avg Rating: {skill.avg_rating:.1f}/5
Success Rate: {skill.success_rate:.0f}%

Recent negative feedback:
"""
        for fb in bad_feedback:
            log = fb.execution_log
            prompt += f"""
---
Input: {log.input_data}
Output: {log.output_data}
Rating: {fb.rating}/5
Comment: {fb.comment}
Expected: {fb.expected_output or 'Not specified'}
"""

        prompt += """
Based on the feedback, suggest specific changes to improve this skill:
1. What patterns do you see in the failures?
2. How should the config/prompt be updated?
3. Return the improved config as JSON."""

        return ask_ai(prompt, model=self.ai_model, user=self.user)

    def apply_improvement(self, skill, new_config):
        """Apply suggested improvement and bump version"""
        skill.config = new_config
        skill.version += 1
        skill.last_improved_at = timezone.now()
        skill.save()

        # Mark related feedback as applied
        SkillFeedback.objects.filter(
            skill=skill, applied=False
        ).update(applied=True, applied_at=timezone.now())
```

### 6.4 AI Tools for Feedback & Improvement

```python
tools = [
    {
        "name": "submit_skill_feedback_tool",
        "description": "Submit feedback on a skill execution result",
        "input_schema": {
            "properties": {
                "execution_log_id": {"type": "integer"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "comment": {"type": "string"},
                "expected_output": {"type": "string"}
            },
            "required": ["execution_log_id", "rating"]
        }
    },
    {
        "name": "get_skill_stats_tool",
        "description": "Get execution stats and feedback summary for a skill",
        "input_schema": {
            "properties": {
                "skill_name": {"type": "string"}
            },
            "required": ["skill_name"]
        }
    },
    {
        "name": "improve_skill_tool",
        "description": "Analyze feedback and suggest improvements for a skill",
        "input_schema": {
            "properties": {
                "skill_name": {"type": "string"},
                "auto_apply": {"type": "boolean", "default": false}
            },
            "required": ["skill_name"]
        }
    }
]
```

---

## Skills Page Design (`templates/skills.html`)

### Layout: 3-Panel Dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│  Skills & Flows Dashboard                    [+ New Skill] [+ New Flow]  │
├──────────────────┬───────────────────────────┬───────────────────┤
│                  │                           │                   │
│  SKILL LIST      │  SKILL DETAIL / EDITOR    │  EXECUTION LOG    │
│  (left panel)    │  (center panel)           │  (right panel)    │
│                  │                           │                   │
│  ┌────────────┐  │  Skill: "Summarize Text"  │  Recent Runs:     │
│  │ query_tasks│  │  Type: generate           │  ┌─────────────┐  │
│  │ ★★★★☆ 4.2 │  │  Version: 3               │  │ 14:23 ✓     │  │
│  ├────────────┤  │  Executions: 47           │  │ In: {text..} │  │
│  │ summarize  │  │  Success Rate: 94%        │  │ Out: {sum..} │  │
│  │ ★★★☆☆ 3.1 │  │  Avg Rating: ★★★☆☆ 3.1   │  │ [👍] [👎]    │  │
│  ├────────────┤  │                           │  ├─────────────┤  │
│  │ classify   │  │  ┌─ Config ─────────────┐ │  │ 14:20 ✓     │  │
│  │ ★★★★★ 4.8 │  │  │ prompt_template:     │ │  │ In: {text..} │  │
│  ├────────────┤  │  │ "Summarize the       │ │  │ Out: {sum..} │  │
│  │ create_task│  │  │  following: ${text}"  │ │  │ [👍] [👎]    │  │
│  │ ★★★★☆ 4.0 │  │  │ model: "llama3.2"    │ │  ├─────────────┤  │
│  └────────────┘  │  └──────────────────────┘ │  │ 14:18 ✗     │  │
│                  │                           │  │ Error: ...   │  │
│  ── FLOWS ──     │  [Save] [Test] [Improve]  │  │ Duration: 2s │  │
│  ┌────────────┐  │                           │  └─────────────┘  │
│  │ Daily      │  │  ┌─ Improvement Hints ──┐ │                   │
│  │ Review     │  │  │ 3 negative feedbacks  │ │  ── FEEDBACK ──   │
│  │ 5 steps    │  │  │ found. Users say      │ │  Avg: ★★★☆☆ 3.1  │
│  ├────────────┤  │  │ summaries are too     │ │  Total: 12 ratings│
│  │ Weekly     │  │  │ short. Suggest:       │ │                   │
│  │ Report     │  │  │ update prompt to add  │ │  Recent:          │
│  │ 4 steps    │  │  │ "detailed" keyword.   │ │  ★★☆☆☆ "too short"│
│  └────────────┘  │  │ [Apply Fix] [Dismiss] │ │  ★★★★☆ "good"     │
│                  │  └──────────────────────┘ │  ★☆☆☆☆ "wrong fmt" │
│                  │                           │                   │
└──────────────────┴───────────────────────────┴───────────────────┘
```

### Left Panel: Skill & Flow List
- Lists all skills (system + user-created) with name, type icon, avg rating stars
- Lists all flows with name and step count
- Click to select -> loads detail in center panel
- Filter tabs: All | Query | Generate | Transform | Action
- Sort by: Name | Rating | Executions | Recent

### Center Panel: Skill Detail / Editor
- **View mode**: Shows skill name, type, version, stats (executions, success rate, avg rating)
- **Edit mode**: Edit config JSON, prompt template, description
- **Test button**: Run skill with sample input, shows output inline
- **Improve button**: Triggers AI analysis of negative feedback, shows suggestion
- **Apply Fix button**: Applies AI-suggested improvement, bumps version
- For flows: Shows step list as visual pipeline with arrows between steps

### Right Panel: Execution Log + Feedback
- Chronological list of recent executions for selected skill
- Each log entry shows:
  - Timestamp + status icon (✓ success, ✗ error, ⏱ timeout)
  - Collapsible input/output data (JSON formatted)
  - Duration in ms
  - Feedback buttons: thumbs up / thumbs down / star rating
  - If feedback given: shows rating + comment
- Filter: All | Success | Error | Low-rated

### Flow Execution View (`templates/flow_run.html`)
```
┌──────────────────────────────────────────────────────┐
│  Flow: "Daily Task Review"        Status: Running    │
│  Started: 14:23:05               Step: 3 of 5       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Step 1: query_tasks ──────────────── ✓ Complete     │
│  ├─ Input: {status: "pending"}                       │
│  ├─ Output: [{task: "Fix bug", priority: "high"}...] │
│  ├─ Duration: 45ms                                   │
│  └─ [👍 5] [👎]                                      │
│       │                                              │
│       ▼                                              │
│  Step 2: query_tasks (overdue) ────── ✓ Complete     │
│  ├─ Input: {status: "pending", is_overdue: true}     │
│  ├─ Output: [{task: "Deploy v2", days_overdue: 3}]   │
│  ├─ Duration: 38ms                                   │
│  └─ [👍 4] [👎]                                      │
│       │                                              │
│       ▼                                              │
│  Step 3: summarize_text ──────────── ⏳ Running...   │
│  ├─ Input: {text: "$previous.output"}                │
│  └─ [spinner animation]                              │
│       │                                              │
│       ▼                                              │
│  Step 4: classify_priority ───────── ○ Pending       │
│       │                                              │
│       ▼                                              │
│  Step 5: generate_action_plan ────── ○ Pending       │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [Cancel Flow]                    [Rate All Steps]   │
└──────────────────────────────────────────────────────┘
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `chatbot/models.py` | Add `Skill`, `Flow`, `FlowStep`, `FlowExecution`, `SkillExecutionLog`, `SkillFeedback` models |
| `chatbot/skills/__init__.py` (new) | Skills package |
| `chatbot/skills/executor.py` (new) | Skill executor with automatic logging |
| `chatbot/skills/flow_engine.py` (new) | Flow engine |
| `chatbot/skills/builtin_skills.py` (new) | System-provided skill definitions |
| `chatbot/skills/improver.py` (new) | AI-powered skill improvement from feedback |
| `chatbot/tools/definitions.py` | Add skill/flow/feedback management tools |
| `chatbot/tools/executors.py` | Wire up skill/flow/feedback tools |
| `chatbot/urls.py` | Add `/api/skills/`, `/api/flows/`, `/api/flows/<id>/run/`, `/api/skill-logs/`, `/api/skill-feedback/` |
| `chatbot/views.py` | Add skill/flow/feedback API views |
| `chatbot/admin.py` | Register Skill, Flow, FlowStep, FlowExecution, SkillExecutionLog, SkillFeedback |
| `chatbot/management/commands/` (new) | Scheduled flow runner, setup_builtin_skills |
| `templates/skills.html` (new) | 3-panel skill/flow management dashboard |
| `templates/flow_run.html` (new) | Flow execution progress with step feedback |

## Risks & Considerations

1. **Complexity** - Flow engine is the most complex feature. Start with linear flows only (no branching/loops)
2. **Infinite loops** - Flows that create tasks which trigger flows. Need execution depth limits
3. **Error handling** - If step 3 of 5 fails, what happens? Options: stop, skip, retry
4. **Security** - Skills should only access the user's own data. No cross-user queries
5. **Performance** - Long flows with AI calls at each step could be slow. Consider async execution
6. **LLM reliability** - AI-generated flow definitions may be malformed. Validate before saving
7. **Dependency** - Requires Plan 01 (Ollama) for local execution and Plan 02 (query engine) for data skills
8. **Log volume** - Execution logs can grow fast. Consider retention policy (auto-delete logs older than 90 days)
9. **Feedback bias** - Users tend to only give feedback when things go wrong. Track "no feedback" as implicit positive
10. **Auto-improvement safety** - AI-suggested improvements should always require user approval before applying

## Implementation Order

```
Phase 1: Models + Skill executor + built-in skills     (foundation)
Phase 2: Flow engine + flow executor                    (core feature)
Phase 3: AI tools for creating/running flows via chat   (UX)
Phase 4: Scheduled flows                                (automation)
Phase 5: Execution logging + observability              (visibility)
Phase 6: User feedback + self-improvement               (learning loop)
```
