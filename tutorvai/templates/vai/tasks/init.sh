# Assign themes only if no other theme exists yet
./manage.py lms shell -c "
import sys
from django.contrib.sites.models import Site
def assign_theme(domain):
    site, _ = Site.objects.get_or_create(domain=domain)
    if not site.themes.exists():
        site.themes.create(theme_dir_name='vai')

assign_theme('{{ LMS_HOST }}')
assign_theme('{{ LMS_HOST }}')
assign_theme('{{ LMS_HOST }}:8000')
assign_theme('{{ CMS_HOST }}')
assign_theme('{{ CMS_HOST }}:8001')
assign_theme('{{ PREVIEW_LMS_HOST }}')
assign_theme('{{ PREVIEW_LMS_HOST }}:8000')
"

# Run AI Extensions migrations if the app is installed
./manage.py lms migrate openedx_ai_extensions --run-syncdb 2>/dev/null || echo "AI Extensions migrations skipped (not installed)"

# Create VAI AI textbook assistant profile and scope (idempotent)
./manage.py lms shell -c "
try:
    import json
    from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope

    profile, created = AIWorkflowProfile.objects.get_or_create(
        slug='vai-textbook-assistant',
        defaults={
            'description': 'VAI veterinary textbook and course assistant with MCP search tools',
            'base_filepath': 'examples/openai/chat.json',
            'content_patch': json.dumps({
                'orchestrator_class': 'ThreadedLLMResponse',
                'processor_config': {
                    'OpenEdXProcessor': {
                        'function': 'get_location_content',
                        'retrieval_mode': 'unit',
                    },
                    'LLMProcessor': {
                        'function': 'chat_with_context',
                        'provider': 'openai',
                        'stream': True,
                        'mcp_configs': ['vai_knowledge'],
                        'enabled_tools': ['get_location_content', 'get_context'],
                    },
                },
                'actuator_config': {
                    'UIComponents': {
                        'request': {
                            'component': 'AISidebarResponse',
                            'config': {
                                'buttonText': 'Ask about this unit',
                                'customMessage': 'Ask a question about this lesson or any VAI textbook',
                            },
                        },
                        'response': {
                            'component': 'AISidebarResponse',
                        },
                    },
                },
            }),
        },
    )
    if created:
        print('Created AI profile: vai-textbook-assistant')
    else:
        print('AI profile already exists: vai-textbook-assistant')

    # Create a universal scope (all courses, all units) if none exists
    scope, s_created = AIWorkflowScope.objects.get_or_create(
        profile=profile,
        ui_slot_selector_id='ai-assist-button',
        location_regex='.*',
        course_id=None,
        defaults={'enabled': True},
    )
    if s_created:
        print('Created AI scope: all courses, ai-assist-button')
    else:
        print('AI scope already exists')

except ImportError:
    print('AI Extensions not installed, skipping profile setup')
except Exception as e:
    print(f'AI Extensions setup error (non-fatal): {e}')
" 2>/dev/null || echo "AI Extensions profile setup skipped"
