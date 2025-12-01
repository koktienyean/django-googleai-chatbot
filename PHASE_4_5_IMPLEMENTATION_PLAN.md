# Phase 4 & 5 Implementation Plan

**Date**: December 1, 2025
**Status**: Planning
**Duration**: Phases 4-5 combined

---

## Overview

Phase 4 & 5 extend the Django Gemini Chatbot with advanced features for notifications and analytics, building on the solid foundation created in Phases 1-3.

### Phase 4: Email Notifications & Recurring Tasks
- Email reminders for task deadlines
- Recurring task templates
- Notification preferences
- Task notification history

### Phase 5: Advanced Analytics & Reporting
- Productivity dashboard
- Task completion analytics
- Chat activity insights
- Performance metrics
- Export reports

---

## Phase 4: Email Notifications & Recurring Tasks

### Feature 1: Email Notification System

**Database Model: Notification**

```python
class Notification(models.Model):
    """Tracks notifications sent to users"""

    NOTIFICATION_TYPES = [
        ('deadline_reminder', 'Deadline Reminder'),
        ('task_due_today', 'Task Due Today'),
        ('task_overdue', 'Task Overdue'),
        ('task_completed', 'Task Completed'),
        ('recurring_created', 'Recurring Task Created'),
    ]

    user = ForeignKey(User)
    task = ForeignKey(Task, nullable=True)  # Can be null for non-task notifications
    notification_type = CharField(choices=NOTIFICATION_TYPES)
    subject = CharField(200)
    message = TextField()
    is_sent = BooleanField(default=False)
    sent_at = DateTimeField(nullable=True)
    read_at = DateTimeField(nullable=True)
    created_at = DateTimeField(auto_now_add=True)

    # For tracking retry attempts
    attempts = IntegerField(default=0)
    last_error = TextField(blank=True)
```

**Features:**
- Track notification delivery status
- Store notification history
- Support multiple notification types
- Enable reading/marking notifications
- Track retry attempts and errors

**API Endpoints:**

```
GET  /api/notifications/               → List user's notifications
GET  /api/notifications/<int:id>/      → Get notification details
POST /api/notifications/<int:id>/read/ → Mark as read
GET  /api/notifications/unread/        → Count unread notifications
DELETE /api/notifications/<int:id>/    → Delete notification
```

**Gemini Tools:**

```python
def get_notification_summary(user):
    """Get notification summary: unread count, recent notifications"""

def set_notification_preference(user, preference_type, enabled):
    """Enable/disable notifications: deadline_reminder, task_overdue, daily_digest"""

def get_notification_preferences(user):
    """Get user's notification preferences"""
```

---

### Feature 2: Deadline Reminder System

**NotificationPreference Model**

```python
class NotificationPreference(models.Model):
    """User's notification settings"""

    user = ForeignKey(User, on_delete=models.CASCADE, unique=True)
    deadline_reminder_enabled = BooleanField(default=True)
    reminder_days_before = IntegerField(default=1)  # Days before deadline
    reminder_time = TimeField(default='09:00')       # Time to send reminder
    overdue_reminder_enabled = BooleanField(default=True)
    daily_digest_enabled = BooleanField(default=False)
    digest_time = TimeField(default='08:00')
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Implementation:**

```python
# Background task to send deadline reminders (runs daily)
def send_deadline_reminders():
    """Check all tasks and send reminders based on user preferences"""
    # Get tasks due within reminder window
    # Check user notification preferences
    # Send email for each matching task
    # Create Notification record
    # Log delivery status

def send_overdue_notifications():
    """Send daily notifications for overdue tasks"""
    # Find all overdue tasks for user
    # Check if user wants overdue reminders
    # Send email
    # Create Notification record

def send_daily_digest():
    """Send daily summary of tasks and activity"""
    # Get user's task summary (pending, overdue, completed today)
    # Get recent chat activity
    # Compile into email digest
    # Send email
    # Create Notification record
```

**Email Templates:**

```
templates/emails/
├── deadline_reminder.txt
├── deadline_reminder.html
├── overdue_reminder.txt
├── overdue_reminder.html
├── daily_digest.txt
├── daily_digest.html
├── task_completed.txt
└── task_completed.html
```

---

### Feature 3: Recurring Tasks

**RecurringTaskTemplate Model**

```python
class RecurringTaskTemplate(models.Model):
    """Template for recurring tasks"""

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    user = ForeignKey(User, on_delete=models.CASCADE)
    title = CharField(200)
    description = TextField(blank=True)
    priority = CharField(max_length=20, choices=Task.PRIORITY_CHOICES)
    frequency = CharField(max_length=20, choices=FREQUENCY_CHOICES)

    # When to stop recurring
    start_date = DateTimeField()
    end_date = DateTimeField(nullable=True)  # None = infinite

    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    is_active = BooleanField(default=True)

    # Track next instance
    last_instance_created = DateTimeField(nullable=True)
    next_instance_date = DateTimeField()
```

**RecurringTaskInstance Model**

```python
class RecurringTaskInstance(models.Model):
    """Tracks individual instances of recurring tasks"""

    template = ForeignKey(RecurringTaskTemplate, on_delete=models.CASCADE)
    task = ForeignKey(Task, on_delete=models.CASCADE, unique=True)
    created_at = DateTimeField(auto_now_add=True)
    instance_number = IntegerField()  # 1st, 2nd, 3rd occurrence
```

**Gemini Tools:**

```python
def create_recurring_task(user, title, description, priority, frequency, start_date, end_date=None):
    """Create a recurring task template"""
    # Validates frequency
    # Sets next_instance_date
    # Creates RecurringTaskTemplate
    # Creates first instance Task

def list_recurring_tasks(user):
    """List all recurring task templates"""

def update_recurring_task(template_id, **kwargs):
    """Update recurring task template"""

def delete_recurring_task(template_id, delete_future=False):
    """Delete recurring task. If delete_future=True, deletes all future instances"""

def skip_recurring_instance(task_id):
    """Skip next instance of recurring task"""
```

**Implementation:**

```python
# Management command to generate recurring task instances
def generate_recurring_instances():
    """
    Daily task that:
    1. Finds all active RecurringTaskTemplates
    2. Checks if next_instance_date <= today
    3. Creates new Task instance
    4. Updates next_instance_date
    5. Creates RecurringTaskInstance record
    """
```

---

### Feature 4: Task Notifications on Status Change

**Django Signals Implementation:**

```python
@receiver(post_save, sender=Task)
def task_status_changed(sender, instance, created, **kwargs):
    """Send notification when task status changes"""
    if created:
        # Task just created - optional creation notification
        pass
    else:
        # Check if status actually changed
        previous = Task.objects.get(pk=instance.pk)
        if previous.status != instance.status:
            if instance.status == 'completed':
                # Send completion notification
                send_task_completion_notification(instance)
            elif instance.status == 'in_progress':
                # Optional: notify on progress start
                pass

@receiver(post_save, sender=Task)
def task_completed(sender, instance, **kwargs):
    """Auto-set completed_at when marking complete"""
    if instance.status == 'completed' and not instance.completed_at:
        instance.completed_at = timezone.now()
        instance.save()
```

---

## Phase 5: Advanced Analytics & Reporting

### Feature 1: Analytics Models

**TaskAnalytics Model**

```python
class TaskAnalytics(models.Model):
    """Daily task analytics snapshot for trending and reporting"""

    user = ForeignKey(User, on_delete=models.CASCADE)
    date = DateField(auto_now_add=True)

    # Counts
    total_tasks = IntegerField()
    pending_count = IntegerField()
    in_progress_count = IntegerField()
    completed_count = IntegerField()
    overdue_count = IntegerField()

    # Completion metrics
    completed_today = IntegerField()
    completion_rate = FloatField()  # % of tasks completed
    avg_completion_time = DurationField()  # Average days to complete

    # Priority breakdown
    urgent_count = IntegerField()
    high_count = IntegerField()
    medium_count = IntegerField()
    low_count = IntegerField()

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
```

**ChatAnalytics Model**

```python
class ChatAnalytics(models.Model):
    """Daily chat activity analytics"""

    user = ForeignKey(User, on_delete=models.CASCADE)
    date = DateField(auto_now_add=True)

    # Message counts
    total_messages = IntegerField()
    user_messages = IntegerField()
    ai_responses = IntegerField()
    total_sessions = IntegerField()

    # Activity
    active_sessions = IntegerField()
    avg_session_length = IntegerField()  # avg messages per session

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
```

**Implementation:**

```python
# Management command to generate daily analytics
def generate_daily_analytics():
    """
    Daily task that:
    1. For each user:
       a. Calculate task counts and metrics
       b. Calculate chat activity metrics
       c. Store in TaskAnalytics and ChatAnalytics
    2. Aggregate for trend reporting
    """
```

---

### Feature 2: Analytics Dashboard

**Dashboard Views:**

```python
@login_required
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    # Get data from TaskAnalytics and ChatAnalytics
    # Calculate key metrics
    # Prepare chart data
    # Return context with all analytics data

def task_completion_chart(request):
    """JSON endpoint for completion rate chart"""
    # 30-day completion trend
    # Returns data for line chart

def priority_distribution_chart(request):
    """JSON endpoint for priority distribution"""
    # Current breakdown by priority
    # Returns data for pie chart

def weekly_activity_chart(request):
    """JSON endpoint for weekly activity heatmap"""
    # Message count by day of week
    # Returns data for bar chart

def productivity_metrics(request):
    """JSON endpoint for productivity metrics"""
    # Average time to complete tasks
    # Completion rate
    # Task velocity (tasks created vs completed)
    # Returns JSON with metrics
```

**Dashboard UI Components:**

```html
templates/analytics.html:
├── Header (title, date range selector)
├── Key Metrics Row
│   ├── Total Tasks
│   ├── Completion Rate
│   ├── Overdue Count
│   └── Active Streak (days with activity)
├── Charts Row 1
│   ├── Task Completion Trend (line chart)
│   └── Priority Distribution (pie chart)
├── Charts Row 2
│   ├── Weekly Activity (bar chart)
│   └── Status Breakdown (stacked bar)
├── Insights Panel
│   ├── Top Priority (urgent tasks)
│   ├── Fastest Completed (shortest time-to-completion)
│   └── Slowest Tasks (still pending)
└── Export Options
    ├── Export as CSV
    ├── Export as PDF
    └── Share Report
```

---

### Feature 3: Productivity Insights

**Insights Generation:**

```python
def generate_insights(user):
    """Generate AI-powered insights from analytics"""
    insights = []

    # Insight 1: Completion rate trend
    completion_trend = get_completion_trend(user, days=7)
    if completion_trend['change'] > 0.1:
        insights.append({
            'type': 'positive',
            'title': 'Great progress!',
            'message': f'Your completion rate improved {completion_trend["change"]*100:.1f}% this week'
        })

    # Insight 2: Overdue tasks
    overdue_count = Task.objects.filter(user=user).filter(is_overdue=True).count()
    if overdue_count > 0:
        insights.append({
            'type': 'warning',
            'title': 'Overdue tasks',
            'message': f'You have {overdue_count} overdue tasks. Consider prioritizing them.'
        })

    # Insight 3: Best time to work
    best_time = get_peak_activity_time(user)
    insights.append({
        'type': 'info',
        'title': 'Your peak productivity time',
        'message': f'You\'re most active at {best_time}. Schedule important tasks then.'
    })

    return insights

def get_completion_trend(user, days=7):
    """Calculate completion rate trend"""

def get_peak_activity_time(user):
    """Find user's most active time of day"""
```

---

### Feature 4: Report Generation

**ReportTemplate Model**

```python
class Report(models.Model):
    """Generated reports for users"""

    REPORT_TYPES = [
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Report'),
    ]

    user = ForeignKey(User, on_delete=models.CASCADE)
    report_type = CharField(max_length=20, choices=REPORT_TYPES)
    title = CharField(200)
    start_date = DateField()
    end_date = DateField()
    content = TextField()  # HTML content
    file_path = FileField(upload_to='reports/%Y/%m/')  # PDF/CSV
    created_at = DateTimeField(auto_now_add=True)
    is_shared = BooleanField(default=False)
```

**Report Generation:**

```python
def generate_weekly_report(user):
    """Generate weekly report"""
    # Get analytics for past 7 days
    # Generate insights
    # Create charts as images
    # Compile HTML
    # Generate PDF
    # Save Report record
    # Send email with report

def generate_monthly_report(user):
    """Generate monthly report"""
    # Similar to weekly but for 30 days

def export_report_csv(report_id):
    """Export report as CSV"""

def export_report_pdf(report_id):
    """Export report as PDF"""
```

---

## API Endpoints Summary

### Phase 4 Endpoints

**Notifications:**
```
GET  /api/notifications/
GET  /api/notifications/<int:id>/
POST /api/notifications/<int:id>/read/
GET  /api/notifications/unread/
DELETE /api/notifications/<int:id>/
```

**Preferences:**
```
GET  /api/notification-preferences/
POST /api/notification-preferences/
```

**Recurring Tasks:**
```
POST /api/recurring-tasks/
GET  /api/recurring-tasks/
GET  /api/recurring-tasks/<int:id>/
PUT  /api/recurring-tasks/<int:id>/
DELETE /api/recurring-tasks/<int:id>/
POST /api/recurring-tasks/<int:id>/skip-next/
```

### Phase 5 Endpoints

**Analytics:**
```
GET  /api/analytics/dashboard/
GET  /api/analytics/task-completion-chart/
GET  /api/analytics/priority-distribution/
GET  /api/analytics/weekly-activity/
GET  /api/analytics/productivity-metrics/
GET  /api/analytics/insights/
```

**Reports:**
```
GET  /api/reports/
POST /api/reports/generate/
GET  /api/reports/<int:id>/
GET  /api/reports/<int:id>/download/
GET  /api/reports/<int:id>/share/
```

---

## Gemini Tools Summary

### Phase 4 Tools

1. **create_recurring_task(title, description, priority, frequency, start_date, end_date)**
2. **list_recurring_tasks()**
3. **update_recurring_task(template_id, **kwargs)**
4. **delete_recurring_task(template_id, delete_future)**
5. **skip_recurring_instance(task_id)**
6. **get_notification_summary()**
7. **set_notification_preference(preference_type, enabled)**
8. **get_notification_preferences()**

### Phase 5 Tools

1. **get_productivity_metrics()** - Returns completion rate, velocity, streaks
2. **get_task_insights()** - Returns AI-generated insights
3. **generate_weekly_report()** - Creates and sends weekly report
4. **generate_monthly_report()** - Creates and sends monthly report
5. **get_analytics_summary()** - Returns dashboard-ready analytics

---

## Testing Strategy

### Phase 4 Testing

**Notification System Tests:**
- ✅ Notification creation and storage
- ✅ Email sending (mock SMTP)
- ✅ Notification preferences
- ✅ Retry logic on delivery failure
- ✅ Notification history tracking

**Recurring Task Tests:**
- ✅ Template creation with frequency validation
- ✅ Instance generation at correct intervals
- ✅ Handling of end dates and limits
- ✅ Skipping instances
- ✅ Deletion of future instances

### Phase 5 Testing

**Analytics Tests:**
- ✅ Daily analytics generation
- ✅ Metric calculations accuracy
- ✅ Chart data formatting
- ✅ Trend calculation

**Report Tests:**
- ✅ Report generation (PDF/CSV)
- ✅ Report download functionality
- ✅ Report sharing via URL
- ✅ Email delivery

---

## Performance Considerations

**Database:**
- Add indexes on (user, -date) for analytics tables
- Partition TaskAnalytics by user for large datasets
- Cache dashboard data (1-hour TTL)

**Email:**
- Use Celery for async email sending
- Queue notifications in Redis
- Implement batch sending for efficiency

**Reporting:**
- Generate reports asynchronously
- Cache PDF generation
- Use task queue for heavy computations

---

## Security Considerations

**Notifications:**
- Only show user's own notifications
- Validate notification type before sending
- Rate-limit notification sending (prevent spam)
- Hash report share URLs

**Analytics:**
- Only show user's own analytics
- Validate date range inputs
- Prevent CSV injection in exports
- Sanitize HTML in report generation

**Recurring Tasks:**
- Validate frequency values
- Verify user owns template before deletion
- Validate date inputs

---

## Deployment Checklist

- [ ] Add email configuration to settings.py
- [ ] Create Notification, NotificationPreference, RecurringTaskTemplate, RecurringTaskInstance models
- [ ] Create TaskAnalytics and ChatAnalytics models
- [ ] Create email templates
- [ ] Create management commands for background tasks
- [ ] Create API endpoints
- [ ] Create Gemini tools
- [ ] Create dashboard UI
- [ ] Set up task scheduler (Celery + Beat or APScheduler)
- [ ] Configure SMTP for email
- [ ] Create test suite
- [ ] Documentation
- [ ] Git commit

---

## Estimated Development Time

- **Phase 4**: 12-16 hours
  - Email notification system: 6-8 hours
  - Recurring tasks: 4-6 hours
  - Testing: 2-3 hours

- **Phase 5**: 14-18 hours
  - Analytics models: 3-4 hours
  - Dashboard views: 5-6 hours
  - Report generation: 4-5 hours
  - Testing: 2-3 hours

**Total**: 26-34 hours

---

## Success Criteria

### Phase 4
- ✅ Users receive email reminders 24 hours before deadline
- ✅ Recurring tasks create new instances at correct intervals
- ✅ Notification preferences are respected
- ✅ All email templates are professional and readable
- ✅ Gemini tools work with natural language inputs
- ✅ 100% test pass rate

### Phase 5
- ✅ Dashboard loads in < 2 seconds
- ✅ Analytics accurate for 30-day period
- ✅ Reports generate in < 30 seconds
- ✅ Charts render correctly on desktop and mobile
- ✅ Insights are meaningful and actionable
- ✅ 100% test pass rate

---

**Next**: Begin Phase 4 Implementation

---

*Phase 4 & 5 Implementation Plan*
*December 1, 2025*
*Ready for Development*
