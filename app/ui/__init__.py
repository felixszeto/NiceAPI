from nicegui import ui, app
from sqlalchemy.orm import Session
from fastapi import Depends
from .common import apply_styles, set_ui_colors, set_language, logout
from .auth import login_page
from .dashboard import render_dashboard
from .providers import render_providers
from .groups import render_groups
from .logs import render_logs
from .keywords import render_keywords
from .api_keys import render_api_keys
from .settings import render_settings
from .remote import remote_page
from ..database import get_db
from ..language import get_text

def create_ui():
    @ui.page('/')
    def main_page(db: Session = Depends(get_db)):
        apply_styles()
        set_ui_colors()

        if not app.storage.user.get('authenticated', False):
            login_page()
            return

        # Main Layout for authenticated users
        with ui.left_drawer(value=True, elevated=False).props('bordered breakpoint=1023 width=280 show-if-above').classes('bg-white p-0 flex flex-col no-wrap') as drawer:
            with ui.column().classes('p-6 items-center w-full border-b'):
                ui.image('/images/favicon.png').classes('w-12 h-12 mb-2')
                ui.label('NiceAPI Admin').classes('text-xl font-bold text-slate-800')
                ui.label('v1.2.0').classes('text-xs text-slate-400')
            
            with ui.scroll_area().classes('flex-grow w-full custom-scrollbar'):
                with ui.tabs().props('vertical inline-label indicator-color="primary" active-color="primary" content-class="text-slate-600"').classes('w-full') as tabs:
                    dashboard_tab = ui.tab(get_text('dashboard'), icon='dashboard').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    providers_tab = ui.tab(get_text('providers'), icon='router').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    groups_tab = ui.tab(get_text('groups'), icon='workspaces').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    logs_tab = ui.tab(get_text('call_logs'), icon='history').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    errors_tab = ui.tab(get_text('failure_keywords'), icon='report_problem').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    api_keys_tab = ui.tab(get_text('api_keys'), icon='vpn_key').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                    settings_tab = ui.tab(get_text('settings'), icon='settings').classes('justify-start px-6 py-2 min-h-[48px] w-full')
            
            with ui.column().classes('p-4 w-full border-t gap-1'):
                with ui.button(icon='language').props('flat color="primary"').classes('w-full justify-start'):
                    ui.label('Language').classes('ml-2 text-sm')
                    with ui.menu():
                        ui.menu_item('English', on_click=lambda: set_language('en'))
                        ui.menu_item('中文(简体)', on_click=lambda: set_language('zh-CN'))
                        ui.menu_item('中文(繁體)', on_click=lambda: set_language('zh-TW'))
                        ui.menu_item('한국어', on_click=lambda: set_language('ko'))
                        ui.menu_item('日本語', on_click=lambda: set_language('ja'))
                ui.button(get_text('logout'), on_click=logout, icon='logout').props('flat color="negative"').classes('w-full justify-start text-sm')

        with ui.header(elevated=False).classes('bg-white border-b text-slate-800 p-2 md:p-4 flex items-center justify-between'):
            with ui.row().classes('items-center'):
                ui.button(on_click=lambda: drawer.toggle(), icon='menu').props('flat color="primary" round').classes('lg:hidden')
                ui.label(get_text('api_management')).classes('text-lg md:text-xl font-semibold ml-2')
            
            with ui.row().classes('items-center gap-4'):
                ui.icon('notifications', color='slate-400').classes('text-2xl cursor-pointer')
                ui.avatar(icon='person', color='primary').classes('cursor-pointer')

        with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full bg-transparent p-4 md:p-6'):
            with ui.tab_panel(dashboard_tab) as dashboard_panel:
                render_dashboard(db, ui.element('div').classes('w-full'), dashboard_panel)
            with ui.tab_panel(providers_tab) as providers_panel:
                render_providers(db, ui.element('div').classes('w-full'), providers_panel)
            with ui.tab_panel(groups_tab) as groups_panel:
                render_groups(db, ui.element('div').classes('w-full'), groups_panel)
            with ui.tab_panel(logs_tab) as logs_panel:
                render_logs(db, ui.element('div').classes('w-full'), logs_panel)
            with ui.tab_panel(errors_tab) as errors_panel:
                render_keywords(db, ui.element('div').classes('w-full'), errors_panel)
            with ui.tab_panel(api_keys_tab) as api_keys_panel:
                render_api_keys(db, ui.element('div').classes('w-full'), api_keys_panel)
            with ui.tab_panel(settings_tab) as settings_panel:
                render_settings(db, ui.element('div').classes('w-full'), settings_panel)

    # Register /remote page
    ui.page('/remote')(remote_page)