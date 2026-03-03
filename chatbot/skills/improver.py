"""
AI-powered skill improvement from user feedback.
Analyzes negative feedback patterns and suggests config/prompt improvements.
"""
from django.utils import timezone


class SkillImprover:
    """Analyze skill feedback and suggest improvements."""

    def __init__(self, user, ai_model='llama3.2'):
        self.user = user
        self.ai_model = ai_model

    def suggest_improvement(self, skill):
        """Analyze negative feedback and suggest config/prompt improvements."""
        from chatbot.models import SkillFeedback

        bad_feedback = SkillFeedback.objects.filter(
            skill=skill, rating__lte=2
        ).select_related('execution_log').order_by('-created_at')[:10]

        if not bad_feedback.exists():
            return {
                'status': 'no_issues',
                'message': f'No negative feedback found for "{skill.name}". Skill is performing well.',
            }

        # Build analysis prompt
        prompt = f"""Analyze this AI skill and its feedback to suggest improvements.

Skill: {skill.name}
Type: {skill.skill_type}
Description: {skill.description}
Current Config: {skill.config}
Version: {skill.version}
Avg Rating: {skill.avg_rating:.1f}/5
Success Rate: {skill.success_rate:.0f}%
Total Executions: {skill.total_executions}

Recent negative feedback ({bad_feedback.count()} entries):
"""
        for fb in bad_feedback:
            log = fb.execution_log
            prompt += f"""
---
Input: {log.input_data}
Output: {log.output_data}
Status: {log.status}
Rating: {fb.rating}/5
Comment: {fb.comment}
Expected: {fb.expected_output or 'Not specified'}
"""

        prompt += """
Based on the feedback, suggest specific changes to improve this skill:
1. What patterns do you see in the failures?
2. How should the config/prompt be updated?
3. Provide the improved config as a JSON object.

Be specific and actionable. Focus on the most impactful change."""

        from chatbot.views import ask_ai
        suggestion = ask_ai(prompt, model=self.ai_model, user=self.user)

        return {
            'status': 'suggestion_ready',
            'skill_name': skill.name,
            'current_version': skill.version,
            'feedback_count': bad_feedback.count(),
            'suggestion': suggestion,
        }

    def apply_improvement(self, skill, new_config):
        """Apply suggested improvement and bump version."""
        from chatbot.models import SkillFeedback

        skill.config = new_config
        skill.version += 1
        skill.last_improved_at = timezone.now()
        skill.save()

        # Mark related feedback as applied
        SkillFeedback.objects.filter(
            skill=skill, applied=False
        ).update(applied=True, applied_at=timezone.now())

        return {
            'status': 'applied',
            'skill_name': skill.name,
            'new_version': skill.version,
        }

    def get_skill_stats(self, skill):
        """Get comprehensive stats for a skill including feedback summary."""
        from chatbot.models import SkillFeedback, SkillExecutionLog
        from django.db.models import Avg, Count

        # Refresh stats
        skill.update_stats()

        # Feedback breakdown
        feedback_stats = SkillFeedback.objects.filter(skill=skill).aggregate(
            total=Count('id'),
            avg_rating=Avg('rating'),
        )

        rating_distribution = {}
        for i in range(1, 6):
            count = SkillFeedback.objects.filter(skill=skill, rating=i).count()
            rating_distribution[str(i)] = count

        # Recent errors
        recent_errors = list(
            SkillExecutionLog.objects.filter(skill=skill, status='error')
            .order_by('-executed_at')[:5]
            .values('error_message', 'executed_at', 'input_data')
        )
        # Serialize datetimes
        for err in recent_errors:
            if err.get('executed_at'):
                err['executed_at'] = err['executed_at'].isoformat()

        return {
            'skill_name': skill.name,
            'skill_type': skill.skill_type,
            'version': skill.version,
            'total_executions': skill.total_executions,
            'success_rate': skill.success_rate,
            'avg_rating': skill.avg_rating,
            'feedback_count': feedback_stats['total'] or 0,
            'rating_distribution': rating_distribution,
            'recent_errors': recent_errors,
            'last_improved_at': skill.last_improved_at.isoformat() if skill.last_improved_at else None,
        }
