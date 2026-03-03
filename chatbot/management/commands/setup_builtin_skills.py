"""
Management command to seed built-in system skills for all users.
Usage: python manage.py setup_builtin_skills
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chatbot.models import Skill
from chatbot.skills.builtin_skills import BUILTIN_SKILLS


class Command(BaseCommand):
    help = 'Create built-in system skills for all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user', type=str, default=None,
            help='Only create skills for a specific username'
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete and recreate all system skills'
        )

    def handle(self, *args, **options):
        username = options.get('user')
        reset = options.get('reset', False)

        if username:
            users = User.objects.filter(username=username)
            if not users.exists():
                self.stderr.write(self.style.ERROR(f'User "{username}" not found'))
                return
        else:
            users = User.objects.all()

        if not users.exists():
            self.stderr.write(self.style.WARNING('No users found. Create a user first.'))
            return

        total_created = 0
        total_skipped = 0

        for user in users:
            if reset:
                deleted_count, _ = Skill.objects.filter(user=user, is_system=True).delete()
                if deleted_count:
                    self.stdout.write(f'  Deleted {deleted_count} system skills for {user.username}')

            for skill_def in BUILTIN_SKILLS:
                skill, created = Skill.objects.get_or_create(
                    user=user,
                    name=skill_def['name'],
                    defaults={
                        'description': skill_def['description'],
                        'skill_type': skill_def['skill_type'],
                        'config': skill_def['config'],
                        'input_schema': skill_def.get('input_schema', {}),
                        'output_schema': skill_def.get('output_schema', {}),
                        'is_system': True,
                    }
                )
                if created:
                    total_created += 1
                else:
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {total_created} skills created, {total_skipped} already existed '
            f'(across {users.count()} user(s))'
        ))
