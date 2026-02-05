from nicegui import ui
from app.language import get_text

def render_menu():
    with ui.column().classes('w-full items-center px-4 py-8 max-w-5xl mx-auto'):
        # Features Grid
        with ui.grid(columns='1 md:2 lg:3').classes('w-full gap-6'):
            
            # Dashboard
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-blue-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('dashboard', size='2rem').classes('text-blue-500')
                    ui.label(get_text("dashboard")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("dashboard_intro")).classes('text-slate-600 leading-relaxed')

            # Providers
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-emerald-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('settings_input_component', size='2rem').classes('text-emerald-500')
                    ui.label(get_text("providers")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("providers_intro")).classes('text-slate-600 leading-relaxed')

            # Groups
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-amber-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('groups', size='2rem').classes('text-amber-500')
                    ui.label(get_text("groups")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("groups_intro")).classes('text-slate-600 leading-relaxed')

            # Call Logs
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-indigo-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('list_alt', size='2rem').classes('text-indigo-500')
                    ui.label(get_text("call_logs")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("call_logs_intro")).classes('text-slate-600 leading-relaxed')

            # Failure Keywords
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-rose-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('rule', size='2rem').classes('text-rose-500')
                    ui.label(get_text("failure_keywords")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("keywords_intro")).classes('text-slate-600 leading-relaxed')

            # API Keys
            with ui.card().classes('p-6 hover:shadow-lg transition-shadow border-t-4 border-purple-500'):
                with ui.row().classes('items-center mb-4'):
                    ui.icon('vpn_key', size='2rem').classes('text-purple-500')
                    ui.label(get_text("api_keys")).classes('text-xl font-semibold ml-2')
                ui.label(get_text("api_keys_intro")).classes('text-slate-600 leading-relaxed')
