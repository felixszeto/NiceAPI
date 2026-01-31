from nicegui import ui, app
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from fastapi import Depends, Request
import requests
import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from .database import SessionLocal, get_db
from . import crud, models, schemas
from .language import get_text

# Load environment variables
load_dotenv()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

def create_ui():

    @ui.page('/')
    def main_page(db: Session = Depends(get_db)):
        ui.add_head_html('''
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            :root {
                --primary: #2563eb;
                --bg-main: #f8fafc;
                --card-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
                --card-hover: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                background-color: var(--bg-main) !important;
            }

            .nicegui-content {
                padding: 0 !important;
            }

            .glass-card {
                background: rgba(255, 255, 255, 0.8) !important;
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px !important;
                box-shadow: var(--card-shadow) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .glass-card:hover {
                box-shadow: var(--card-hover) !important;
                transform: translateY(-2px);
            }

            .sidebar-active {
                background: rgba(37, 99, 235, 0.1) !important;
                color: var(--primary) !important;
                border-right: 3px solid var(--primary);
            }

            .custom-scrollbar::-webkit-scrollbar { width: 6px; }
            .custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
            .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
            
            .q-table th {
                font-weight: 600 !important;
                color: #64748b !important;
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 0.05em;
            }

            .q-table td {
                color: #334155 !important;
            }

            .status-badge {
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 0.75rem;
            }
            
            .q-dialog__backdrop {
                background: rgba(15, 23, 42, 0.5) !important;
                backdrop-filter: blur(4px);
            }

            .header-gradient {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
            }

            .ellipsis {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            @media (max-width: 600px) {
                .q-dialog__inner--minimized > div {
                    max-width: 95vw !important;
                    width: 95vw !important;
                }
                .mobile-hide {
                    display: none !important;
                }
            }
            </style>
        ''')
        @asynccontextmanager
        async def loading_animation():
            with ui.dialog() as dialog, ui.card().classes('bg-transparent shadow-none'):
                ui.spinner('puff', color='white', size='xl')
            
            dialog.open()
            dialog.props('persistent')
            try:
                await asyncio.sleep(0.05) # time for dialog to show
                yield
                await asyncio.sleep(0.3) # user-requested delay
            finally:
                dialog.close()

        # If the user is not authenticated, redirect to the login page.
        ui.colors(
            primary='#2F6BFF',
            secondary='#5C8FFF',
            accent='#14B8A6',
            positive='#10B981',
            negative='#EF4444',
            info='#3B82F6',
            warning='#F59E0B'
        )
        def set_language(lang: str):
            app.storage.user['lang'] = lang
            ui.navigate.reload()

        if app.storage.user.get('authenticated', False):
            # This is the main content of the application.
            # It's only shown if the user is authenticated.
            
            def get_all_providers_as_dict(search_query=None):
                providers = crud.get_providers(db)
                rows = [
                    {key: getattr(p, key) for key in p.__table__.columns.keys()}
                    for p in providers
                ]
                if search_query:
                    q = search_query.lower()
                    rows = [r for r in rows if q in r['name'].lower() or q in r['model'].lower()]
                return rows

            # 用於追蹤主頁面的搜尋關鍵字，解決 NiceGUI 狀態更新與元件值不同步導致的搜尋延後問題
            provider_search_state = {'v': ''}

            def refresh_providers_table(search_val=None):
                if search_val is not None:
                    # 來自事件觸發，立即更新狀態（處理 GenericEventArguments 的 args list）
                    if isinstance(search_val, (list, tuple)) and len(search_val) > 0:
                        search_val = search_val[0]
                    provider_search_state['v'] = str(search_val)
                v = provider_search_state['v']
                table.rows = get_all_providers_as_dict(search_query=v)
                table.update()

            def logout():
                app.storage.user['authenticated'] = False
                ui.navigate.reload()

            with ui.left_drawer(value=True, elevated=False).props('bordered breakpoint=1023 width=280 show-if-above').classes('bg-white p-0 flex flex-col no-wrap') as drawer:
                # Top Logo Section
                with ui.column().classes('p-6 items-center w-full border-b'):
                    ui.image('/images/favicon.png').classes('w-12 h-12 mb-2')
                    ui.label('NiceAPI Admin').classes('text-xl font-bold text-slate-800')
                    ui.label('v1.2.0').classes('text-xs text-slate-400')
                
                # Scrollable Navigation Section
                with ui.scroll_area().classes('flex-grow w-full custom-scrollbar'):
                    with ui.tabs().props('vertical inline-label indicator-color="primary" active-color="primary" content-class="text-slate-600"').classes('w-full') as tabs:
                        dashboard_tab = ui.tab(get_text('dashboard'), icon='dashboard').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        providers_tab = ui.tab(get_text('providers'), icon='router').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        groups_tab = ui.tab(get_text('groups'), icon='workspaces').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        logs_tab = ui.tab(get_text('call_logs'), icon='history').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        errors_tab = ui.tab(get_text('failure_keywords'), icon='report_problem').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        api_keys_tab = ui.tab(get_text('api_keys'), icon='vpn_key').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                        settings_tab = ui.tab(get_text('settings'), icon='settings').classes('justify-start px-6 py-2 min-h-[48px] w-full')
                
                # Bottom Action Section
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
                with ui.tab_panel(dashboard_tab):
                    def build_dashboard(container):
                        with container:
                            with ui.element('div').classes('flex flex-wrap w-full gap-6'):
                                # Quick Stats
                                with ui.row().classes('w-full gap-6 mb-2'):
                                    def stat_card(label, value, icon, color):
                                        with ui.card().classes('flex-grow glass-card p-0 overflow-hidden'):
                                            with ui.row().classes('no-wrap items-stretch'):
                                                with ui.column().classes(f'bg-{color}-500 p-4 justify-center items-center self-stretch'):
                                                    ui.icon(icon, color='white').classes('text-2xl')
                                                with ui.column().classes('p-4 justify-center'):
                                                    ui.label(label).classes('text-xs text-slate-500 font-medium')
                                                    ui.label(value).classes('text-2xl font-bold text-slate-800')
                                    
                                    db.expire_all()
                                    # 只統計有分配到 provider 的請求（即 server 真正嘗試請求 API 的記錄）
                                    logs_recent = [l for l in crud.get_call_logs(db, limit=1000) if l.provider_id is not None]
                                    total_calls = len(logs_recent)
                                    success_rate = sum(1 for l in logs_recent if l.is_success) / total_calls * 100 if total_calls > 0 else 0
                                    total_tokens = sum(l.total_tokens or 0 for l in logs_recent)
                                    
                                    stat_card(get_text('api_calls'), str(total_calls), 'bolt', 'blue')
                                    stat_card(get_text('api_call_success_rate'), f'{success_rate:.1f}%', 'check_circle', 'green')
                                    stat_card(get_text('total_tokens'), f'{total_tokens:,}', 'toll', 'orange')
                                    stat_card(get_text('api_keys'), str(len(crud.get_api_keys(db))), 'vpn_key', 'purple')

                                # Chart 1: Model Usage Distribution
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] glass-card p-6'):
                                    ui.label(get_text('model_usage_distribution')).classes('text-lg font-bold text-slate-700 mb-4')
                                    with ui.element('div').classes('w-full h-64'):
                                        db.expire_all()
                                        logs = [l for l in crud.get_call_logs(db, limit=1000) if l.provider_id is not None]
                                        model_counts = {}
                                        for log in logs:
                                            if log.provider and log.provider.model:
                                                model_name = log.provider.model
                                                model_counts[model_name] = model_counts.get(model_name, 0) + 1
                                        
                                        chart_data = [{'name': k, 'value': v} for k,v in model_counts.items()]
                                        if chart_data:
                                            ui.echart({
                                                'tooltip': {'trigger': 'item'},
                                                'legend': {'orient': 'vertical', 'left': 'left'},
                                                'color': ['#2F6BFF', '#14B8A6', '#3B82F6', '#5C8FFF', '#F59E0B', '#6B7280'],
                                                'series': [{
                                                    'name': get_text('api_calls'),
                                                    'type': 'pie',
                                                    'radius': '70%',
                                                    'data': chart_data,
                                                    'emphasis': {
                                                        'itemStyle': {
                                                            'shadowBlur': 10,
                                                            'shadowOffsetX': 0,
                                                            'shadowColor': 'rgba(0, 0, 0, 0.5)'
                                                        }
                                                    }
                                                }]
                                            })
                                        else:
                                            ui.label(get_text('no_api_call_data')).classes('flex-center')

                                # Chart 2: Daily API Calls
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] glass-card p-6'):
                                    ui.label(get_text('daily_api_calls')).classes('text-lg font-bold text-slate-700 mb-4')
                                    with ui.element('div').classes('w-full h-64'):
                                        from datetime import datetime, timedelta
                                        import pytz

                                        TAIPEI_TZ = pytz.timezone('Asia/Taipei')
                                        logs = [l for l in crud.get_call_logs(db, limit=5000) if l.provider_id is not None] # Fetch more for historical data
                                        daily_counts = {}
                                        for i in range(7):
                                            date = (datetime.now(TAIPEI_TZ) - timedelta(days=i)).strftime('%Y-%m-%d')
                                            daily_counts[date] = 0
                                        
                                        for log in logs:
                                            date_str = log.request_timestamp.astimezone(TAIPEI_TZ).strftime('%Y-%m-%d')
                                            if date_str in daily_counts:
                                                daily_counts[date_str] += 1
                                        
                                        sorted_dates = sorted(daily_counts.keys())
                                        chart_data = [daily_counts[d] for d in sorted_dates]

                                        if any(c > 0 for c in chart_data):
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_dates},
                                                'yAxis': {'type': 'value'},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}]
                                            })
                                        else:
                                            ui.label(get_text('no_recent_api_call_data')).classes('flex-center')

                                # Chart 3: API Call Success Rate
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('api_call_success_rate')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = [l for l in crud.get_call_logs(db, limit=1000) if l.provider_id is not None]
                                        success_count = sum(1 for log in logs if log.is_success)
                                        failure_count = len(logs) - success_count
                                        
                                        if logs:
                                            ui.echart({
                                                'tooltip': {'trigger': 'item'},
                                                'legend': {'top': '5%', 'left': 'center'},
                                                'color': ['#10B981', '#EF4444'],
                                                'series': [{
                                                    'name': get_text('api_call_success_rate'),
                                                    'type': 'pie',
                                                    'radius': ['40%', '70%'],
                                                    'avoidLabelOverlap': False,
                                                    'label': {'show': False, 'position': 'center'},
                                                    'emphasis': {'label': {'show': True, 'fontSize': '20', 'fontWeight': 'bold'}},
                                                    'labelLine': {'show': False},
                                                    'data': [
                                                        {'value': success_count, 'name': get_text('successful')},
                                                        {'value': failure_count, 'name': get_text('failed')}
                                                    ]
                                                }]
                                            })
                                        else:
                                            ui.label(get_text('no_api_call_data')).classes('flex-center')

                                # Chart 4: Average Response Time by Model
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('avg_response_time_ms')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = crud.get_call_logs(db, limit=100) # Analyze recent calls
                                        model_times = {}
                                        model_counts = {}
                                        for log in logs:
                                            if log.is_success and log.response_time_ms is not None:
                                                model = log.provider.model
                                                model_times[model] = model_times.get(model, 0) + log.response_time_ms
                                                model_counts[model] = model_counts.get(model, 0) + 1
                                        
                                        avg_times = {m: model_times[m]/model_counts[m] for m in model_times}
                                        sorted_models = sorted(avg_times.keys())
                                        chart_data = [round(avg_times[m]) for m in sorted_models]

                                        if chart_data:
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_models, 'axisLabel': {'interval': 0, 'rotate': 30}},
                                                'yAxis': {'type': 'value'},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}],
                                                'tooltip': {'trigger': 'axis'}
                                            })
                                        else:
                                            ui.label(get_text('no_successful_calls_with_response_time')).classes('flex-center')
                                
                                # Chart 5: API Endpoint Success Rate
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('api_endpoint_success_rate')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = crud.get_call_logs(db, limit=1000)
                                        endpoint_stats = {}
                                        for log in logs:
                                            if log.provider:
                                                try:
                                                    # Parse the URL and get the netloc (domain)
                                                    parsed_url = urlparse(log.provider.api_endpoint)
                                                    endpoint = parsed_url.netloc
                                                except Exception:
                                                    endpoint = log.provider.api_endpoint # Fallback

                                                if endpoint not in endpoint_stats:
                                                    endpoint_stats[endpoint] = {'success': 0, 'total': 0}
                                                endpoint_stats[endpoint]['total'] += 1
                                                if log.is_success:
                                                    endpoint_stats[endpoint]['success'] += 1
                                        
                                        endpoint_rates = {e: (s['success']/s['total'])*100 for e, s in endpoint_stats.items() if s['total'] > 0}
                                        sorted_endpoints = sorted(endpoint_rates.keys())
                                        chart_data = [round(endpoint_rates[e]) for e in sorted_endpoints]

                                        if chart_data:
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_endpoints, 'axisLabel': {'interval': 0, 'rotate': 15}},
                                                'yAxis': {'type': 'value', 'min': 0, 'max': 100, 'axisLabel': {'formatter': '{value} %'}},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}],
                                                'tooltip': {'trigger': 'axis', 'formatter': '{b}: {c}%'}
                                            })
                                        else:
                                            ui.label(get_text('no_data_for_endpoint_success_rate')).classes('flex-center')

                                # Chart 6: Average Response Time by Endpoint
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('avg_response_time_by_endpoint_ms')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = crud.get_call_logs(db, limit=1000)
                                        endpoint_times = {}
                                        endpoint_counts = {}
                                        for log in logs:
                                            if log.provider and log.is_success and log.response_time_ms is not None:
                                                try:
                                                    # Parse the URL and get the netloc (domain)
                                                    parsed_url = urlparse(log.provider.api_endpoint)
                                                    endpoint = parsed_url.netloc
                                                except Exception:
                                                    endpoint = log.provider.api_endpoint # Fallback
                                                    
                                                endpoint_times[endpoint] = endpoint_times.get(endpoint, 0) + log.response_time_ms
                                                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
                                        
                                        avg_times = {e: endpoint_times[e]/endpoint_counts[e] for e in endpoint_times}
                                        sorted_endpoints = sorted(avg_times.keys())
                                        chart_data = [round(avg_times[e]) for e in sorted_endpoints]

                                        if chart_data:
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_endpoints, 'axisLabel': {'interval': 0, 'rotate': 15}},
                                                'yAxis': {'type': 'value'},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}],
                                                'tooltip': {'trigger': 'axis'}
                                            })
                                        else:
                                            ui.label(get_text('no_successful_calls_with_response_time')).classes('flex-center')
                               
                                # Chart 7: Total API Calls by Endpoint
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('total_api_calls_by_endpoint')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = crud.get_call_logs(db, limit=1000)
                                        endpoint_counts = {}
                                        for log in logs:
                                            if log.provider:
                                                try:
                                                    parsed_url = urlparse(log.provider.api_endpoint)
                                                    endpoint = parsed_url.netloc
                                                except Exception:
                                                    endpoint = log.provider.api_endpoint # Fallback
                                                
                                                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

                                        sorted_endpoints = sorted(endpoint_counts.keys())
                                        chart_data = [endpoint_counts[e] for e in sorted_endpoints]

                                        if chart_data:
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_endpoints, 'axisLabel': {'interval': 0, 'rotate': 15}},
                                                'yAxis': {'type': 'value'},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}],
                                                'tooltip': {'trigger': 'axis'}
                                            })
                                        else:
                                            ui.label(get_text('no_api_call_data')).classes('flex-center')
                                
                                # Chart 8: Total Cost by Model
                                with ui.element('div').classes('w-full md:w-[calc(50%-0.75rem)] border rounded-lg p-4 shadow-md bg-white'):
                                    ui.label(get_text('total_cost_by_model')).classes('text-h6')
                                    with ui.element('div').classes('w-full h-64'):
                                        logs = crud.get_call_logs(db, limit=1000)
                                        model_costs = {}
                                        for log in logs:
                                            if log.provider and log.provider.model and log.cost is not None:
                                                model_name = log.provider.model
                                                model_costs[model_name] = model_costs.get(model_name, 0) + log.cost
                                        
                                        sorted_models = sorted(model_costs.keys())
                                        chart_data = [round(model_costs[m], 4) for m in sorted_models]

                                        if chart_data:
                                            ui.echart({
                                                'xAxis': {'type': 'category', 'data': sorted_models, 'axisLabel': {'interval': 0, 'rotate': 30}},
                                                'yAxis': {'type': 'value'},
                                                'series': [{'data': chart_data, 'type': 'bar', 'itemStyle': {'color': '#2F6BFF'}}],
                                                'tooltip': {'trigger': 'axis', 'formatter': '{b}: ${c}'}
                                            })
                                        else:
                                            ui.label(get_text('no_cost_data')).classes('flex-center')

                    async def refresh_dashboard():
                        async with loading_animation():
                            dashboard_container.clear()
                            build_dashboard(dashboard_container)
                        ui.notify(get_text('dashboard_refreshed'), color='positive')

                    with ui.row().classes('w-full items-center mb-4'):
                        ui.label(get_text('dashboard')).classes('text-h6')
                        ui.space()
                        ui.button(get_text('refresh_data'), on_click=refresh_dashboard, icon='refresh', color='primary').props('flat')
                    dashboard_container = ui.element('div').classes('w-full')
                    build_dashboard(dashboard_container)

                with ui.tab_panel(providers_tab):
                    async def refresh_providers_table_async():
                        async with loading_animation():
                            refresh_providers_table()
                        ui.notify(get_text('providers_refreshed'), color='positive')

                    with ui.row().classes('w-full items-center mb-4 gap-4'):
                        ui.label(get_text('providers')).classes('text-h6')
                        ui.space()
                        with ui.row().classes('items-center gap-2'):
                            provider_search_filter = ui.input(placeholder=get_text('search_models')).props('outlined dense icon="search"').classes('w-64').on('update:model-value', lambda e: refresh_providers_table(e.args))
                        
                        async def open_sync_models_dialog():
                            providers = crud.get_providers(db)
                            # Unique by endpoint + key
                            unique_sync_targets = {}
                            for p in providers:
                                target_key = (p.api_endpoint, p.api_key)
                                if target_key not in unique_sync_targets:
                                    unique_sync_targets[target_key] = p.name
                            
                            # Use dict for options to be safe with NiceGUI
                            options = {}
                            for (endpoint, key), name in unique_sync_targets.items():
                                # Encode key/endpoint into a string since dict keys must be hashable
                                # Display as: [Alias] ([masked key])
                                options[f"{endpoint}|{key}"] = f"{name} [{endpoint}] ({key[:5]}...{key[-4:]})"

                            if not options:
                                ui.notify("No providers available to sync.", color='warning')
                                return

                            with ui.dialog() as sync_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
                                ui.label(get_text('select_providers_to_sync')).classes('text-h6')
                                
                                # Multi-select for targets
                                target_select = ui.select(
                                    options=options,
                                    multiple=True,
                                    label=get_text('providers')
                                ).props('filled use-chips').classes('w-full')
                                
                                with ui.row():
                                    def select_all():
                                        target_select.value = list(options.keys())
                                    ui.button(get_text('select_all'), on_click=select_all).props('flat')

                                async def handle_sync():
                                    if not target_select.value:
                                        ui.notify("Please select at least one provider to sync.", color='warning')
                                        return
                                    
                                    sync_dialog.close()
                                    async with loading_animation():
                                        try:
                                            added_total = 0
                                            deactivated_total = 0
                                            
                                            for target_val in target_select.value:
                                                endpoint, api_key = target_val.split('|', 1)
                                                # Fetch models from endpoint
                                                base_url = endpoint.split('/v1/chat/completions')[0]
                                                models_url = f"{base_url.rstrip('/')}/v1/models"
                                                
                                                import httpx
                                                async with httpx.AsyncClient() as client:
                                                    try:
                                                        response = await client.get(models_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
                                                        if response.status_code == 200:
                                                            remote_models_data = response.json()
                                                            remote_model_ids = [m['id'] for m in remote_models_data.get('data', [])]
                                                            
                                                            # Get current models in DB for this endpoint + key
                                                            db_providers = db.query(models.ApiProvider).filter(
                                                                models.ApiProvider.api_endpoint == endpoint,
                                                                models.ApiProvider.api_key == api_key
                                                            ).all()
                                                            db_model_map = {p.model: p for p in db_providers}
                                                            
                                                            # 4.1 如有未存在的models則新增
                                                            # Requirement: endpoint + key + model 三者完全符合才算重複
                                                            for model_id in remote_model_ids:
                                                                # Check if this exact triplet exists in the database
                                                                triplet_exists = db.query(models.ApiProvider).filter(
                                                                    models.ApiProvider.api_endpoint == endpoint,
                                                                    models.ApiProvider.api_key == api_key,
                                                                    models.ApiProvider.model == model_id
                                                                ).first()
                                                                
                                                                if not triplet_exists:
                                                                    template = db_providers[0] if db_providers else None
                                                                    new_provider = schemas.ApiProviderCreate(
                                                                        name=template.name if template else model_id,
                                                                        api_endpoint=endpoint,
                                                                        api_key=api_key,
                                                                        model=model_id,
                                                                        price_per_million_tokens=template.price_per_million_tokens if template else 0,
                                                                        type=template.type if template else 'per_token',
                                                                        is_active=True
                                                                    )
                                                                    crud.create_provider(db, new_provider)
                                                                    added_total += 1
                                                            
                                                            # 4.3 models列表沒有但db有則把db內該條記錄的is_active設定為0
                                                            for m_id, p_obj in db_model_map.items():
                                                                if m_id not in remote_model_ids and p_obj.is_active:
                                                                    crud.update_provider(db, p_obj.id, {"is_active": False})
                                                                    deactivated_total += 1
                                                    except Exception as e:
                                                        ui.notify(f"Error syncing {endpoint}: {e}", color='negative')
                                            
                                            ui.notify(get_text('sync_models_completed').format(added=added_total, deactivated=deactivated_total), color='positive')
                                            refresh_providers_table()
                                        except Exception as e:
                                            ui.notify(get_text('sync_error').format(error=str(e)), color='negative')

                                with ui.row():
                                    ui.button(get_text('sync'), on_click=handle_sync, color='primary')
                                    ui.button(get_text('cancel'), on_click=sync_dialog.close)
                            
                            sync_dialog.open()

                    # Add Provider Dialog (Combined Single & Batch)
                    with ui.dialog() as add_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[500px]'):
                        add_dialog.props('persistent')
                        with ui.tabs().classes('w-full') as add_tabs:
                            batch_tab = ui.tab(get_text('add_provider'))
                            single_tab = ui.tab(get_text('add_single_model'))
                        
                        with ui.tab_panels(add_tabs, value=batch_tab).classes('w-full'):
                            with ui.tab_panel(batch_tab):
                                with ui.column().classes('w-full'):
                                    base_url_input = ui.input(get_text('base_url'), placeholder=get_text('base_url_hint')).props('filled').classes('w-full')
                                    api_key_input = ui.input(get_text('api_key'), placeholder='sk-xxxxxxxxxxxxxxxxxxxx', password=True).props('filled').classes('w-full')
                                    alias_input = ui.input(get_text('alias_optional'), placeholder=get_text('alias_hint')).props('filled').classes('w-full')
                                    default_type_select = ui.select(['per_token', 'per_call'], value='per_token', label=get_text('default_type')).props('filled').classes('w-full')
                                    with ui.row().classes('w-full no-wrap'):
                                        filter_mode_select = ui.select(['None', 'Include', 'Exclude'], value='None', label=get_text('filter_mode')).props('filled').classes('w-1/3')
                                        filter_keyword_input = ui.input(get_text('model_name_filter'), placeholder=get_text('filter_hint')).props('filled').classes('flex-grow')
                                    
                                    with ui.element('div').classes('w-full relative h-6') as progress_container:
                                        progress = ui.linear_progress(value=0, show_value=False).props('rounded size="25px" color="positive" striped').classes('w-full h-full')
                                        progress_label = ui.label('0.0%').classes('absolute-full flex flex-center text-white font-medium')
                                    progress_container.visible = False
                                    
                                    with ui.row().classes('w-full justify-end mt-4'):
                                        ui.button(get_text('cancel'), on_click=add_dialog.close).props('flat')
                                        ui.button(get_text('import'), on_click=lambda: handle_import(), color='primary')

                            with ui.tab_panel(single_tab):
                                with ui.column().classes('w-full'):
                                    name_input = ui.input(get_text('name'), placeholder=get_text('provider_name_hint')).props('filled').classes('w-full')
                                    endpoint_input = ui.input(get_text('api_endpoint'), placeholder=get_text('endpoint_hint')).props('filled').classes('w-full')
                                    key_input = ui.input(get_text('api_key'), placeholder='sk-xxxxxxxxxxxxxxxxxxxx', password=True).props('filled').classes('w-full')
                                    model_input = ui.input(get_text('model'), placeholder=get_text('model_hint')).props('filled').classes('w-full')
                                    price_input = ui.number(get_text('price_per_million_tokens'), placeholder=get_text('price_hint')).props('filled').classes('w-full')
                                    type_select = ui.select(['per_token', 'per_call'], value='per_token', label=get_text('type')).props('filled').classes('w-full')
                                    active_toggle = ui.switch(get_text('active'), value=True)
                                    
                                    with ui.row().classes('w-full justify-end mt-4'):
                                        ui.button(get_text('cancel'), on_click=add_dialog.close).props('flat')
                                        ui.button(get_text('add'), on_click=lambda: handle_add_single(), color='primary')
                        
                        def handle_add_single():
                            # Validation
                            if not name_input.value or not endpoint_input.value or not key_input.value or not model_input.value:
                                ui.notify("Please fill in all required fields (Name, Endpoint, Key, Model).", color='warning')
                                return

                            url = endpoint_input.value.strip()
                            if url.endswith('/v1') or url.endswith('/v1/'):
                                final_endpoint = f"{url.rstrip('/')}/chat/completions"
                                ui.notify(f"Endpoint auto-completed to: {final_endpoint}", color='info')
                            else:
                                parsed = urlparse(url)
                                if not parsed.path or parsed.path == '/':
                                    final_endpoint = f"{url.rstrip('/')}/v1/chat/completions"
                                    ui.notify(f"Endpoint auto-completed to: {final_endpoint}", color='info')
                                else:
                                    final_endpoint = url

                            provider_data = schemas.ApiProviderCreate(
                                name=name_input.value,
                                api_endpoint=final_endpoint,
                                api_key=key_input.value,
                                model=model_input.value,
                                price_per_million_tokens=price_input.value,
                                type=type_select.value,
                                is_active=active_toggle.value
                            )
                            crud.create_provider(db, provider_data)
                            ui.notify(get_text('provider_added').format(name=name_input.value), color='positive')
                            refresh_providers_table()
                            add_dialog.close()

                        async def handle_import():
                            # Validation
                            if not base_url_input.value or not api_key_input.value:
                                ui.notify("Please fill in both Base URL and API Key.", color='warning')
                                return

                            progress_container.visible = True
                            progress.value = 0
                            progress_label.text = '0.0%'
                            
                            try:
                                api_url = "http://127.0.0.1:8001/api/import-models/"
                                payload = {
                                    "base_url": base_url_input.value,
                                    "api_key": api_key_input.value,
                                    "alias": alias_input.value,
                                    "default_type": default_type_select.value,
                                    "filter_mode": filter_mode_select.value,
                                    "filter_keyword": filter_keyword_input.value
                                }
                                
                                import httpx
                                async with httpx.AsyncClient() as client:
                                    async with client.stream("POST", api_url, json=payload, timeout=None) as response:
                                        if response.status_code != 200:
                                            error_detail = (await response.aread()).decode()
                                            ui.notify(f"Error: {error_detail}", color='negative')
                                            progress_container.visible = False
                                            return

                                        total = 0
                                        imported_count = 0
                                        async for line in response.aiter_lines():
                                            if line.startswith('data:'):
                                                data = line[len('data:'):].strip()
                                                if data.startswith('TOTAL='):
                                                    total = int(data.split('=')[1])
                                                    ui.notify(f'Found {total} models. Starting import...')
                                                elif data.startswith('PROGRESS='):
                                                    imported_count = int(data.split('=')[1])
                                                    if total > 0:
                                                        progress_value = imported_count / total
                                                        progress.value = progress_value
                                                        progress_label.text = f'{progress_value * 100:.1f}%'
                                                elif data.startswith('DONE='):
                                                    final_message = data.split('=', 1)[1]
                                                    ui.notify(final_message, color='positive')
                                                    refresh_providers_table()
                                                    await asyncio.sleep(1)
                                                    add_dialog.close()
                                                elif data.startswith('ERROR='):
                                                    error_message = data.split('=', 1)[1]
                                                    ui.notify(error_message, color='negative')

                            except httpx.ConnectError as e:
                                ui.notify(f"Connection Error: Could not connect to the backend API at {api_url}. Is the server running?", color='negative')
                            except Exception as e:
                                ui.notify(f"An unexpected error occurred: {e}", color='negative')
                            finally:
                                progress_container.visible = False
                                progress.value = 0
                                progress_label.text = '0.0%'



                    def open_quick_remove_dialog():
                        with ui.dialog() as dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[250px]'):
                            ui.label(get_text('quick_remove_by_api_key')).classes('text-h6')

                            def get_keys_with_alias():
                                providers = crud.get_providers(db)
                                key_info = {}
                                for p in providers:
                                    # Create a unique display based on both Alias and masked api_key
                                    display_val = f"{p.name} [{p.api_endpoint}] ({p.api_key[:5]}...{p.api_key[-4:]})"
                                    key_info[p.api_key] = display_val
                                
                                return key_info

                            def handle_quick_remove(key_select):
                                key = key_select.value
                                if not key:
                                    ui.notify('An API Key must be selected.', color='negative')
                                    return
                                
                                deleted_count = crud.delete_providers_by_key(db, key)
                                ui.notify(f'Removed {deleted_count} providers with the selected key.', color='positive')
                                refresh_providers_table()
                                dialog.close()

                            qr_key_select = ui.select(options=get_keys_with_alias(), label=get_text('api_key')).props('filled').classes('w-full')

                            with ui.row():
                                ui.button(get_text('remove'), on_click=lambda: handle_quick_remove(qr_key_select), color='negative')
                                ui.button(get_text('cancel'), on_click=dialog.close)
                        dialog.open()

                    columns = [
                        {'name': 'id', 'label': get_text('id'), 'field': 'id', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'model', 'label': get_text('model'), 'field': 'model', 'sortable': True, 'align': 'left', 'classes': 'max-w-[150px] md:max-w-none ellipsis'},
                        {'name': 'name', 'label': get_text('alias'), 'field': 'name', 'sortable': True, 'align': 'left', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'price_per_million_tokens', 'label': get_text('price_dollar_per_1m'), 'field': 'price_per_million_tokens', 'sortable': True},
                        {'name': 'is_active', 'label': get_text('active'), 'field': 'is_active', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
                    ]
                    
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.button(get_text('add_provider'), on_click=add_dialog.open, color='primary', icon='add').props('unelevated')
                        ui.button(get_text('sync_models'), on_click=open_sync_models_dialog, icon='sync', color='primary').props('outline')
                        ui.button(get_text('refresh_providers'), on_click=refresh_providers_table_async, icon='refresh', color='primary').props('flat')
                        ui.button(get_text('quick_remove'), on_click=open_quick_remove_dialog, color='negative', icon='delete_sweep').props('flat')
                    
                    table = ui.table(columns=columns, rows=get_all_providers_as_dict(), row_key='id', pagination=20).classes('w-full mt-4')
                    
                    table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn @click="$parent.$emit('edit', props.row)" icon="edit" flat dense color="primary" />
                            <q-btn @click="$parent.$emit('delete', props.row)" icon="delete" flat dense color="negative" />
                        </q-td>
                    ''')

                    with ui.dialog() as edit_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[500px]'):
                        ui.label(get_text('edit_provider')).classes('text-h6')
                        edit_id = ui.label()
                        with ui.column().classes('w-full'):
                            edit_name_input = ui.input(get_text('name')).props('filled').classes('w-full')
                            edit_endpoint_input = ui.input(get_text('api_endpoint')).props('filled').classes('w-full')
                            edit_key_input = ui.input(get_text('api_key'), password=True).props('filled').classes('w-full')
                            edit_model_input = ui.input(get_text('model')).props('filled').classes('w-full')
                            edit_price_input = ui.number(get_text('price_per_million_tokens')).props('filled').classes('w-full')
                            edit_type_select = ui.select(['per_token', 'per_call'], label=get_text('type')).props('filled').classes('w-full')
                            edit_active_toggle = ui.switch(get_text('active'))

                        def handle_edit():
                            url = edit_endpoint_input.value.strip()
                            if url.endswith('/v1') or url.endswith('/v1/'):
                                final_endpoint = f"{url.rstrip('/')}/chat/completions"
                                ui.notify(f"Endpoint auto-completed to: {final_endpoint}", color='info')
                            else:
                                parsed = urlparse(url)
                                if not parsed.path or parsed.path == '/':
                                    final_endpoint = f"{url.rstrip('/')}/v1/chat/completions"
                                    ui.notify(f"Endpoint auto-completed to: {final_endpoint}", color='info')
                                else:
                                    final_endpoint = url
                            
                            provider_data = {
                                "name": edit_name_input.value,
                                "api_endpoint": final_endpoint,
                                "model": edit_model_input.value,
                                "price_per_million_tokens": edit_price_input.value,
                                "type": edit_type_select.value,
                                "is_active": edit_active_toggle.value
                            }
                            if edit_key_input.value:
                                provider_data['api_key'] = edit_key_input.value

                            crud.update_provider(db, edit_id.text, provider_data)
                            ui.notify(get_text('provider_updated').format(name=edit_name_input.value), color='positive')
                            refresh_providers_table()
                            edit_dialog.close()

                        with ui.row():
                            ui.button(get_text('save'), on_click=handle_edit, color='primary')
                            ui.button(get_text('cancel'), on_click=edit_dialog.close)

                    def open_edit_dialog(e):
                        row = e.args
                        edit_id.text = row['id']
                        edit_name_input.value = row['name']
                        edit_endpoint_input.value = row['api_endpoint']
                        edit_key_input.value = ''
                        edit_key_input.props('placeholder="Enter new key to change"')
                        edit_model_input.value = row['model']
                        edit_price_input.value = row['price_per_million_tokens']
                        edit_type_select.value = row['type']
                        edit_active_toggle.value = row['is_active']
                        edit_dialog.open()

                    async def open_delete_dialog(e):
                        row = e.args
                        with ui.dialog() as delete_dialog, ui.card().style('width: 60vw; max-width: 800px;'):
                            ui.label(get_text('delete_provider_confirm').format(name=row['name']))
                            with ui.row():
                                def handle_delete():
                                    crud.delete_provider(db, row['id'])
                                    ui.notify(get_text('provider_deleted').format(name=row['name']), color='negative')
                                    refresh_providers_table()
                                    delete_dialog.close()
                                ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                                ui.button(get_text('cancel'), on_click=delete_dialog.close)
                        await delete_dialog

                    table.on('edit', open_edit_dialog)
                    table.on('delete', open_delete_dialog)

                with ui.tab_panel(groups_tab) as panel:

                    def get_groups_with_providers():
                        db.expire_all()
                        groups = crud.get_groups(db)
                        providers = crud.get_providers(db)
                        
                        # Convert providers to dictionaries to avoid DetachedInstanceError
                        providers_dicts = [
                            {key: getattr(p, key) for key in p.__table__.columns.keys()}
                            for p in providers
                        ]
                        
                        group_data = []
                        for group in groups:
                            associations = db.query(models.provider_group_association).filter_by(group_id=group.id).all()
                            group_providers = {assoc.provider_id: {"priority": assoc.priority} for assoc in associations}
                            group_data.append({'id': group.id, 'name': group.name, 'providers': group_providers})
                        return group_data, providers_dicts

                    def build_groups_view(name_filter=None, endpoint_filter=None):
                        groups_container.clear()
                        group_data, all_providers = get_groups_with_providers()

                        if not group_data:
                            with groups_container:
                                ui.label(get_text('no_groups_created'))
                            return

                        async def open_manage_dialog(group):
                            with ui.dialog() as manage_dialog, ui.card().style('width: 90vw; max-width: 1000px; max-height: 90vh; min-height: 500px;').classes('p-0 flex flex-col no-wrap'):
                                # --- FIXED HEADER ---
                                with ui.row().classes('w-full items-center justify-between p-4 bg-gray-100 flex-shrink-0'):
                                    ui.label(f"{get_text('manage_providers')}: {group['name']}").classes('text-h6')
                                    ui.button(icon='close', on_click=manage_dialog.close).props('flat round')
                                
                                # --- SCROLLABLE CONTENT AREA ---
                                with ui.column().classes('w-full flex-grow overflow-hidden p-0 gap-0'):
                                    search_input = ui.input(placeholder=get_text('search_providers')).props('outlined dense icon="search"').classes('w-full px-4 py-2 bg-white flex-shrink-0')
                                    
                                    with ui.column().classes('w-full overflow-auto'):
                                        table_columns = [
                                            # Use 'model' as the primary field for the name column to enable model-based filtering
                                            {'name': 'model', 'label': get_text('model'), 'field': 'model', 'sortable': True, 'align': 'left', 'classes': 'w-[200px] break-all whitespace-normal'},
                                            # Hidden alias column to enable filtering by alias
                                            {'name': 'alias', 'label': get_text('alias'), 'field': 'name', 'sortable': True, 'align': 'left', 'classes': 'hidden', 'headerClasses': 'hidden'},
                                            {'name': 'priority', 'label': get_text('priority'), 'field': 'priority', 'sortable': True, 'align': 'center', 'style': 'width: 320px'},
                                        ]

                                        # Prepare rows with smart sorting logic
                                        rows = []
                                        for p in all_providers:
                                            pid = p['id']
                                            is_selected = pid in group['providers']
                                            raw_p = group['providers'].get(pid, {}).get('priority', 0)
                                            priority = raw_p if 1 <= raw_p <= 5 else 0
                                            rows.append({
                                                'id': pid,
                                                'name': p['name'],
                                                'model': p['model'],
                                                'selected': is_selected,
                                                'priority': priority
                                            })

                                        # 用於管理供應商彈窗的內部搜尋狀態，解決搜尋結果延後一個動作的問題
                                        manage_search_state = {'v': ''}

                                        def update_view(search_val=None):
                                            if search_val is not None:
                                                # 如果是事件傳入的值，立即更新快取狀態（處理 GenericEventArguments 的 args list）
                                                if isinstance(search_val, (list, tuple)) and len(search_val) > 0:
                                                    search_val = search_val[0]
                                                manage_search_state['v'] = str(search_val)
                                            
                                            v = manage_search_state['v'].lower()
                                            
                                            # 1. 先過濾符合搜尋條件的行
                                            filtered_rows = [
                                                r for r in rows
                                                if v in r['model'].lower() or v in r['name'].lower()
                                            ]
                                            
                                            # 2. 獲取搜尋結果中的 ID 集合
                                            filtered_ids = {r['id'] for r in filtered_rows}
                                            
                                            # 3. 找出「已被選擇」但「不在搜尋結果中」的行（用於強制置頂）
                                            extra_selected = [r for r in rows if r['selected'] and r['id'] not in filtered_ids]
                                            
                                            # 4. 合併結果：置頂行 + 搜尋結果行
                                            final_rows = extra_selected + filtered_rows
                                            
                                            # 5. 統一排序：已選擇優先，其次按優先級，最後按名稱
                                            final_rows.sort(key=lambda r: (0 if r['selected'] else 1, r['priority'] if r['priority'] > 0 else 999, r['name']))
                                            
                                            m_table.rows = final_rows
                                            m_table.update()

                                        # Table inside scrollable column
                                        m_table = ui.table(columns=table_columns, rows=rows, row_key='id', pagination={'rowsPerPage': 50}).classes('w-full px-2 shadow-none border-none')
                                        search_input.on('update:model-value', lambda e: update_view(e.args))

                                        # Highlight row if selected and handle name click for general selection
                                        m_table.add_slot('body-cell-model', '''
                                            <q-td :props="props" :class="props.row.selected ? 'bg-blue-1' : ''">
                                                <div class="column cursor-pointer" @click="$parent.$emit('toggle_select', props.row)">
                                                    <div class="text-weight-bold" style="white-space: normal; word-break: break-all;">{{ props.row.model }}</div>
                                                    <div class="text-caption text-grey-6" style="white-space: normal; word-break: break-all;">{{ props.row.name }}</div>
                                                </div>
                                            </q-td>
                                        ''')

                                        # 5 Mutually exclusive priority toggle buttons
                                        m_table.add_slot('body-cell-priority', '''
                                            <q-td :props="props" :class="props.row.selected ? 'bg-blue-1' : ''">
                                                <div class="row q-gutter-x-sm justify-center no-wrap">
                                                    <div v-for="p in [1,2,3,4,5]" :key="p" class="column items-center">
                                                        <div class="text-bold text-blue-9" style="font-size: 10px; margin-bottom: -4px">P{{p}}</div>
                                                        <q-toggle
                                                            :model-value="props.row.priority === p"
                                                            @update:model-value="val => $parent.$emit('set_p', {row: props.row, val: val ? p : 0})"
                                                            dense
                                                            size="sm"
                                                            color="primary"
                                                        />
                                                    </div>
                                                </div>
                                            </q-td>
                                        ''')

                                        def handle_priority_change(e):
                                            args = e.args
                                            row_data = args['row']
                                            val = args['val']
                                            target_row = next((r for r in rows if r['id'] == row_data['id']), None)
                                            if not target_row: return
                                            if val > 0:
                                                to_shift = [r for r in rows if r['id'] != target_row['id'] and 0 < r['priority'] <= 5 and r['priority'] >= val]
                                                to_shift.sort(key=lambda x: x['priority'], reverse=True)
                                                for r in to_shift:
                                                    r['priority'] += 1
                                                    if r['priority'] > 5:
                                                        r['priority'] = 0
                                                        r['selected'] = False # Unselect if pushed out of P5
                                                target_row['priority'] = val
                                                target_row['selected'] = True
                                            else:
                                                target_row['priority'] = 0
                                                target_row['selected'] = False # Remove highlight when turned off
                                            update_view()

                                        def handle_toggle_select(e):
                                            row_data = e.args
                                            target_row = next((r for r in rows if r['id'] == row_data['id']), None)
                                            if target_row:
                                                target_row['selected'] = not target_row['selected']
                                                if not target_row['selected']:
                                                    target_row['priority'] = 0
                                                update_view()

                                        m_table.on('set_p', handle_priority_change)
                                        m_table.on('toggle_select', handle_toggle_select)
                                        update_view()

                                # --- FIXED FOOTER ---
                                with ui.row().classes('w-full justify-end p-4 bg-gray-50 flex-shrink-0 border-t'):
                                    async def save_management():
                                        changes = False
                                        for row in rows:
                                            pid = row['id']
                                            was_selected = pid in group['providers']
                                            is_now_selected = row['selected']
                                            new_p = row['priority'] if row['priority'] > 0 else 99
                                            old_p = group['providers'].get(pid, {}).get('priority')
                                            if is_now_selected:
                                                if not was_selected or new_p != old_p:
                                                    crud.add_provider_to_group(db, provider_id=pid, group_id=group['id'], priority=new_p)
                                                    changes = True
                                            elif was_selected:
                                                crud.remove_provider_from_group(db, provider_id=pid, group_id=group['id'])
                                                changes = True
                                        if changes:
                                            ui.notify(get_text('save_success'), color='positive')
                                            manage_dialog.close()
                                            await refresh_groups_view()

                                    ui.button(get_text('cancel'), on_click=manage_dialog.close).props('flat')
                                    ui.button(get_text('save'), on_click=save_management, color='primary').props('unelevated')
                            
                            manage_dialog.open()

                        async def open_delete_group_dialog(group_id, group_name):
                            with ui.dialog() as delete_dialog, ui.card():
                                ui.label(get_text('delete_group_confirm').format(name=group_name))
                                with ui.row().classes('w-full justify-end mt-4'):
                                    async def handle_delete():
                                        crud.delete_group(db, group_id)
                                        ui.notify(get_text('group_deleted').format(name=group_name), color='negative')
                                        delete_dialog.close()
                                        await refresh_groups_view()
                                    ui.button(get_text('cancel'), on_click=delete_dialog.close).props('flat')
                                    ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                            await delete_dialog

                        with groups_container:
                            for group in group_data:
                                with ui.card().classes('w-full mb-4 p-4'):
                                    with ui.row().classes('w-full items-center'):
                                        with ui.column().classes('gap-0'):
                                            ui.label(group['name']).classes('text-h6')
                                            member_count = len(group['providers'])
                                            ui.label(f"{get_text('id')}: {group['id']} | {member_count} {get_text('providers')}").classes('text-caption text-gray-500')
                                        ui.space()
                                        with ui.row().classes('gap-2'):
                                            ui.button(get_text('manage_providers'), icon='settings', on_click=lambda g=group: open_manage_dialog(g)).props('outline color="primary"')
                                            ui.button(icon='delete', on_click=lambda g=group: open_delete_group_dialog(g['id'], g['name']), color='negative').props('flat round')
                                    
                                    if group['providers']:
                                        with ui.row().classes('w-full mt-2 gap-2'):
                                            # Show top 10 models as badges
                                            sorted_pids = sorted(group['providers'].keys(), key=lambda x: group['providers'][x]['priority'])
                                            for pid in sorted_pids[:10]:
                                                p_obj = next((p for p in all_providers if p['id'] == pid), None)
                                                if p_obj:
                                                    priority = group['providers'][pid]['priority']
                                                    ui.badge(f"P{priority}: {p_obj['name']}.{p_obj['model']}").props('color="blue-2" text-color="blue-9"').classes('px-2 py-1')
                                            if len(sorted_pids) > 10:
                                                ui.badge(f"+ {len(sorted_pids)-10} ...").props('color="grey-4" text-color="grey-8"')

                    async def refresh_groups_view():
                        async with loading_animation():
                            build_groups_view()
                        ui.notify(get_text('groups_view_refreshed'), color='positive')

                    # --- Static UI Elements ---
                    panel.on('show', refresh_groups_view)
                    with ui.row().classes('w-full items-center'):
                        ui.label(get_text('provider_groups')).classes('text-h6')
                        ui.space()
                        ui.button(get_text('refresh_groups'), on_click=refresh_groups_view, icon='refresh', color='primary').props('flat')
                    
                    ui.label(get_text('groups_description')).classes('mb-4')

                    with ui.dialog() as add_group_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[250px]'):
                        ui.label(get_text('create_new_group')).classes('text-h6')
                        group_name_input = ui.input(get_text('group_name')).props('filled').classes('w-full')
                        async def handle_add_group():
                            if not group_name_input.value:
                                ui.notify(get_text('group_name_empty_error'), color='negative')
                                return
                            if crud.get_group_by_name(db, group_name_input.value):
                                ui.notify(get_text('group_exists_error').format(name=group_name_input.value), color='negative')
                                return
                            crud.create_group(db, schemas.GroupCreate(name=group_name_input.value))
                            ui.notify(get_text('group_created').format(name=group_name_input.value), color='positive')
                            add_group_dialog.close()
                            await refresh_groups_view()
                        with ui.row():
                            ui.button(get_text('create'), on_click=handle_add_group, color='primary')
                            ui.button(get_text('cancel'), on_click=add_group_dialog.close)
                    
                    ui.button(get_text('create_group'), on_click=add_group_dialog.open, color='primary')

                    # --- Dynamic Content Area ---
                    groups_container = ui.column().classes('w-full mt-4')
                    build_groups_view()


                with ui.tab_panel(logs_tab):
                    def get_logs_with_provider_info(filter_mode='all'):
                        db.expire_all()
                        filter_success = None
                        if filter_mode == 'successful':
                            filter_success = True
                        elif filter_mode == 'failed':
                            filter_success = False
                        
                        logs = crud.get_call_logs(db, limit=500, filter_success=filter_success)
                        log_data = []
                        for log in logs:
                            data = {key: getattr(log, key) for key in log.__table__.columns.keys()}
                            data['api_endpoint'] = log.provider.api_endpoint if log.provider else "N/A"
                            data['model'] = log.provider.model if log.provider else (log.request_body.split('"model": "')[1].split('"')[0] if log.request_body and '"model": "' in log.request_body else "N/A")
                            data['api_key_display'] = f"{log.api_key.key[:5]}...{log.api_key.key[-4:]}" if log.api_key else "N/A"
                            if data.get('request_timestamp'):
                                data['request_timestamp'] = data['request_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                            log_data.append(data)
                        return log_data

                    async def refresh_logs_table():
                        async with loading_animation():
                            logs_table.update_rows(get_logs_with_provider_info(log_filter_tabs.value))
                        ui.notify(get_text('logs_refreshed'), color='positive')

                    with ui.row().classes('w-full items-center'):
                        ui.label(get_text('call_logs')).classes('text-h6')
                        ui.space()
                        ui.button(get_text('refresh_logs'), on_click=refresh_logs_table, icon='refresh', color='primary').props('flat')
                    
                    with ui.tabs().classes('mb-4') as log_filter_tabs:
                        ui.tab('all', label=get_text('all_requests'))
                        ui.tab('successful', label=get_text('successful_requests'))
                        ui.tab('failed', label=get_text('failed_requests'))
                    log_filter_tabs.on('update:model-value', lambda: logs_table.update_rows(get_logs_with_provider_info(log_filter_tabs.value)))

                    log_columns = [
                        {'name': 'id', 'label': get_text('id'), 'field': 'id', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'api_key_display', 'label': get_text('api_key'), 'field': 'api_key_display', 'sortable': True, 'align': 'left', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'model', 'label': get_text('model'), 'field': 'model', 'sortable': True, 'align': 'left', 'classes': 'max-w-[120px] md:max-w-none ellipsis'},
                        {'name': 'request_timestamp', 'label': get_text('timestamp'), 'field': 'request_timestamp', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'is_success', 'label': get_text('success'), 'field': 'is_success'},
                        {'name': 'status_code', 'label': get_text('status'), 'field': 'status_code', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'response_time_ms', 'label': get_text('response_time_ms'), 'field': 'response_time_ms', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'total_tokens', 'label': get_text('total_tokens'), 'field': 'total_tokens', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'cost', 'label': get_text('cost'), 'field': 'cost', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'error_message', 'label': get_text('error'), 'field': 'error_message', 'style': 'max-width: 100px;', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
                    ]


                    import json
                    import re

                    # Dialog for error details
                    with ui.dialog() as error_dialog, ui.card().style('min-width: 400px;'):
                        ui.label(get_text('error_details')).classes('text-h6')
                        error_display = ui.label('').classes('w-full whitespace-pre-wrap border p-4 rounded')
                        with ui.row().classes('w-full justify-end'):
                            ui.button(get_text('close'), on_click=error_dialog.close)

                    def show_error_dialog(e):
                        row_data = e.args
                        error_display.text = row_data.get('error_message') or "No error message."
                        error_dialog.open()

                    # Dialog to display the request and response details
                    with ui.dialog() as response_dialog, ui.card().classes('w-[95vw] md:w-[98vw] max-w-none h-[90vh] md:h-[95vh] overflow-auto'):
                        with ui.row().classes('w-full no-wrap justify-between items-center mb-2'):
                            ui.label(get_text('call_details')).classes('text-h6')
                            ui.button(icon='close', on_click=response_dialog.close).props('flat round dense')

                        with ui.element('div').classes('flex flex-col md:grid md:grid-cols-2 w-full gap-4'):
                            # Request Section
                            with ui.column().classes('w-full gap-4'):
                                with ui.card().classes('w-full p-4'):
                                    ui.label(get_text('request_body')).classes('text-subtitle1 font-bold mb-2')
                                    request_content_area = ui.code('').classes('w-full max-h-[30vh] md:max-h-[35vh] overflow-auto bg-gray-900 text-white p-2 rounded font-mono text-xs')
                                with ui.card().classes('w-full p-4'):
                                    ui.label(get_text('request_text')).classes('text-subtitle1 font-bold mb-2')
                                    request_text_area = ui.label('').classes('w-full max-h-[30vh] md:max-h-[35vh] overflow-auto border p-2 rounded whitespace-pre-wrap text-sm bg-gray-50')
                            
                            # Response Section
                            with ui.column().classes('w-full gap-4'):
                                with ui.card().classes('w-full p-4'):
                                    ui.label(get_text('response_body')).classes('text-subtitle1 font-bold mb-2')
                                    response_content_area = ui.code('').classes('w-full max-h-[30vh] md:max-h-[35vh] overflow-auto bg-gray-900 text-white p-2 rounded font-mono text-xs')
                                with ui.card().classes('w-full p-4'):
                                    ui.label(get_text('response_text')).classes('text-subtitle1 font-bold mb-2')
                                    response_text_area = ui.label('').classes('w-full max-h-[30vh] md:max-h-[35vh] overflow-auto border p-2 rounded whitespace-pre-wrap text-sm bg-gray-50')

                    def show_response_body(e):
                        row_data = e.args
                        
                        def format_body(body_str):
                            if not body_str: return "No content."
                            try:
                                parsed = json.loads(body_str)
                                return json.dumps(parsed, indent=2, ensure_ascii=False)
                            except: return body_str

                        def extract_text(body_str, is_req=True):
                            if not body_str: return ""
                            try:
                                data = json.loads(body_str)
                                if is_req:
                                    msgs = data.get('messages', [])
                                    return "\n".join([f"[{m.get('role', 'user')}]: {m.get('content', '')}" for m in msgs])
                                else:
                                    choices = data.get('choices', [])
                                    if choices:
                                        msg = choices[0].get('message', {})
                                        if msg: return msg.get('content', "")
                                    return ""
                            except:
                                if not is_req:
                                    # Handle streaming SSE content extraction
                                    content_matches = re.findall(r'"content":\s*"([^"]*)"', body_str)
                                    if content_matches:
                                        return "".join(content_matches).replace('\\n', '\n').replace('\\"', '"')
                                return body_str

                        request_content_area.content = format_body(row_data.get('request_body'))
                        response_content_area.content = format_body(row_data.get('response_body'))
                        request_text_area.text = extract_text(row_data.get('request_body'), True)
                        response_text_area.text = extract_text(row_data.get('response_body'), False)
                        
                        request_content_area.update()
                        response_content_area.update()
                        response_dialog.open()

                    logs_table = ui.table(
                        columns=log_columns,
                        rows=get_logs_with_provider_info(),
                        row_key='id'
                    ).classes('w-full')

                    logs_table.add_slot('body-cell-error_message', f'''
                        <q-td :props="props">
                            <q-btn v-if="props.row.error_message" @click="$parent.$emit('view_error', props.row)"
                                   flat dense color="negative" label="{get_text('details')}" />
                            <span v-else>-</span>
                        </q-td>
                    ''')
                    
                    logs_table.add_slot('body-cell-actions', f'''
                        <q-td :props="props">
                            <q-btn @click="$parent.$emit('view_log', props.row)" icon="visibility" flat dense color="primary">
                                <q-tooltip>{get_text('view')}</q-tooltip>
                            </q-btn>
                        </q-td>
                    ''')

                    logs_table.on('view_log', show_response_body)
                    logs_table.on('view_error', show_error_dialog)

                    logs_table.add_slot('body-cell-cost', '''
                        <q-td :props="props">
                            {{ props.row.cost !== null ? props.row.cost.toFixed(6) : 'N/A' }}
                        </q-td>
                    ''')

                with ui.tab_panel(errors_tab):
                    async def refresh_keywords_table_async():
                        async with loading_animation():
                            keywords_table.update_rows([{key: getattr(kw, key) for key in kw.__table__.columns.keys()} for kw in crud.get_error_keywords(db)])
                        ui.notify(get_text('keywords_refreshed'), color='positive')

                    def refresh_keywords_table():
                        keywords_table.update_rows([{key: getattr(kw, key) for key in kw.__table__.columns.keys()} for kw in crud.get_error_keywords(db)])

                    with ui.row().classes('w-full items-center'):
                        ui.label(get_text('failure_keywords')).classes('text-h6')
                        ui.space()
                        ui.button(get_text('refresh_keywords'), on_click=refresh_keywords_table_async, icon='refresh', color='primary').props('flat')
                    
                    ui.label(get_text('failure_keywords_description')).classes('mb-4')

                    with ui.dialog() as add_keyword_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
                        ui.label(get_text('add_failure_keyword')).classes('text-h6')
                        with ui.column().classes('w-full'):
                            keyword_input = ui.input(get_text('keyword_case_insensitive')).props('filled').classes('w-full')
                            desc_input = ui.input(get_text('description')).props('filled').classes('w-full')
                        
                        def handle_add_keyword():
                            keyword_data = schemas.ErrorKeywordCreate(keyword=keyword_input.value, description=desc_input.value)
                            crud.create_error_keyword(db, keyword_data)
                            ui.notify(get_text('keyword_added').format(keyword=keyword_input.value), color='positive')
                            refresh_keywords_table()
                            add_keyword_dialog.close()

                        with ui.row():
                            ui.button(get_text('add'), on_click=handle_add_keyword, color='primary')
                            ui.button(get_text('cancel'), on_click=add_keyword_dialog.close)

                    keyword_columns = [
                        {'name': 'id', 'label': get_text('id'), 'field': 'id', 'sortable': True},
                        {'name': 'keyword', 'label': get_text('keyword'), 'field': 'keyword', 'sortable': True},
                        {'name': 'description', 'label': get_text('description'), 'field': 'description'},
                        {'name': 'is_active', 'label': get_text('active'), 'field': 'is_active'},
                        {'name': 'last_triggered', 'label': get_text('last_triggered'), 'field': 'last_triggered', 'sortable': True},
                        {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
                    ]

                    ui.button(get_text('add_keyword'), on_click=add_keyword_dialog.open, color='primary').classes('mb-4')
                    keywords_table = ui.table(columns=keyword_columns, rows=[{key: getattr(kw, key) for key in kw.__table__.columns.keys()} for kw in crud.get_error_keywords(db)], row_key='id').classes('w-full')
                    
                    keywords_table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn @click="$parent.$emit('delete_keyword', props.row)" icon="delete" flat dense color="negative" />
                        </q-td>
                    ''')

                    async def open_delete_keyword_dialog(e):
                        row = e.args
                        with ui.dialog() as delete_dialog, ui.card().style('width: 60vw; max-width: 800px;'):
                            ui.label(get_text('delete_keyword_confirm').format(keyword=row['keyword']))
                            with ui.row():
                                def handle_delete():
                                    crud.delete_error_keyword(db, row['id'])
                                    ui.notify(get_text('keyword_deleted').format(keyword=row['keyword']), color='negative')
                                    refresh_keywords_table()
                                    delete_dialog.close()
                                ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                                ui.button(get_text('cancel'), on_click=delete_dialog.close)
                        await delete_dialog

                    keywords_table.on('delete_keyword', open_delete_keyword_dialog)
                with ui.tab_panel(api_keys_tab):
                    def get_all_api_keys():
                        db.expire_all()
                        keys = crud.get_api_keys(db)
                        return [
                            {
                                "id": key.id,
                                "key_display": f"{key.key[:5]}...{key.key[-4:]}",
                                "key": key.key,
                                "is_active": key.is_active,
                                "created_at": key.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                "last_used_at": key.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if key.last_used_at else get_text('never'),
                                "groups": ", ".join([g.name for g in key.groups]),
                                "group_ids": [g.id for g in key.groups],
                                "call_count": key.call_count
                            } for key in keys
                        ]

                    columns = [
                        {'name': 'key_display', 'label': get_text('key'), 'field': 'key_display', 'align': 'left'},
                        {'name': 'is_active', 'label': get_text('active'), 'field': 'is_active', 'sortable': True},
                        {'name': 'groups', 'label': get_text('groups'), 'field': 'groups', 'align': 'left', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'call_count', 'label': get_text('api_calls'), 'field': 'call_count', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'created_at', 'label': get_text('created_at'), 'field': 'created_at', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'last_used_at', 'label': get_text('last_used'), 'field': 'last_used_at', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
                        {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
                    ]
                    def refresh_keys_table():
                        keys_table.update_rows(get_all_api_keys())

                    async def refresh_keys_table_async():
                        async with loading_animation():
                            refresh_keys_table()
                        ui.notify(get_text('api_keys_refreshed'), color='positive')

                    with ui.row().classes('w-full items-center mb-4'):
                        ui.label(get_text('api_keys')).classes('text-h6')
                        ui.space()
                        ui.button(get_text('refresh_api_keys'), on_click=refresh_keys_table_async, icon='refresh', color='primary').props('flat')

                    # This dialog is for showing the newly generated key
                    with ui.dialog() as show_key_dialog, ui.card().style('min-width: 400px;'):
                        ui.label(get_text('api_key_generated_successfully')).classes('text-h6')
                        ui.label(get_text('copy_key_instruction')).classes('text-sm text-gray-500')
                        
                        def copy_key():
                            ui.run_javascript(f"navigator.clipboard.writeText('{key_display_label.value}')")
                            ui.notify(get_text('copied_to_clipboard'), color='positive')

                        with ui.row().classes('w-full no-wrap items-center'):
                            key_display_label = ui.input(label=get_text('your_new_api_key')).props('readonly filled').classes('flex-grow')
                            ui.button(icon='content_copy', on_click=copy_key).props('flat dense')

                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button(get_text('close'), on_click=show_key_dialog.close, color='primary')

                    # This dialog is for creating a new key
                    with ui.dialog() as add_key_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px] pb-12'):
                        ui.label(get_text('create_new_api_key')).classes('text-h6')
                        with ui.column().classes('w-full'):
                            async def refresh_group_options():
                                async with loading_animation():
                                    db.expire_all() # Ensure fresh data from DB
                                    all_group_names = [g.name for g in crud.get_groups(db)]
                                    group_select.options = all_group_names
                                    group_select.update()
                                ui.notify(get_text('group_list_refreshed'), color='info')

                            with ui.row().classes('w-full no-wrap items-center'):
                                all_group_names = [g.name for g in crud.get_groups(db)]
                                group_select = ui.select(all_group_names, multiple=True, label=get_text('assign_to_groups')).props('filled').classes('flex-grow')
                                ui.button(icon='refresh', on_click=refresh_group_options).props('flat dense color=primary')

                        def handle_add_key():
                            if not group_select.value:
                                ui.notify(get_text('assign_to_at_least_one_group_error'), color='negative')
                                return
                            
                            group_ids = [g.id for g in crud.get_groups(db) if g.name in group_select.value]
                            key_data = schemas.APIKeyCreate(group_ids=group_ids)
                            new_key = crud.create_api_key(db, key_data)
                            
                            key_display_label.value = new_key.key
                            show_key_dialog.open()

                            ui.notify(get_text('api_key_created'), color='positive')
                            refresh_keys_table()
                            add_key_dialog.close()

                        with ui.row():
                            ui.button(get_text('create'), on_click=handle_add_key, color='primary')
                            ui.button(get_text('cancel'), on_click=add_key_dialog.close)
                    
                    ui.button(get_text('create_api_key'), on_click=add_key_dialog.open, color='primary').classes('mb-4')
                    
                    keys_table = ui.table(columns=columns, rows=[], row_key='id').classes('w-full')
                    keys_table.add_slot('body-cell-key_display', f'''
                        <q-td :props="props">
                            <div class="row items-center no-wrap">
                                <span>{{{{ props.row.key_display }}}}</span>
                                <q-btn @click="$parent.$emit('view-key', props.row.key)" icon="visibility" flat dense color="primary" class="cursor-pointer">
                                    <q-tooltip>{get_text('view_key')}</q-tooltip>
                                </q-btn>
                                <q-btn @click="$parent.$emit('copy-key', props.row.key)" icon="content_copy" flat dense color="primary" class="cursor-pointer">
                                    <q-tooltip>{get_text('copy_tooltip')}</q-tooltip>
                                </q-btn>
                            </div>
                        </q-td>
                    ''')
                    keys_table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn @click="$parent.$emit('edit_key', props.row)" icon="edit" flat dense color="primary" />
                            <q-btn @click="$parent.$emit('open_remote', props.row.key)" icon="open_in_new" flat dense color="info">
                                <q-tooltip>Open Remote Management</q-tooltip>
                            </q-btn>
                            <q-btn @click="$parent.$emit('toggle_key', props.row)" :icon="props.row.is_active ? 'toggle_on' : 'toggle_off'" flat dense :color="props.row.is_active ? 'positive' : 'grey'" />
                            <q-btn @click="$parent.$emit('delete_key', props.row)" icon="delete" flat dense color="negative" />
                        </q-td>
                    ''')

                    with ui.dialog() as edit_key_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
                        ui.label(get_text('edit_api_key')).classes('text-h6')
                        edit_key_id = ui.label()
                        with ui.column().classes('w-full'):
                            async def refresh_edit_group_options():
                                async with loading_animation():
                                    db.expire_all()
                                    all_group_names = [g.name for g in crud.get_groups(db)]
                                    edit_group_select.options = all_group_names
                                    edit_group_select.update()
                                ui.notify(get_text('group_list_refreshed'), color='info')

                            with ui.row().classes('w-full no-wrap items-center'):
                                all_groups_edit = [g.name for g in crud.get_groups(db)]
                                edit_group_select = ui.select(all_groups_edit, multiple=True, label=get_text('assigned_groups')).props('filled').classes('flex-grow')
                                ui.button(icon='refresh', on_click=refresh_edit_group_options).props('flat dense color=primary')

                        def handle_edit_key():
                            group_ids = [g.id for g in crud.get_groups(db) if g.name in edit_group_select.value]
                            update_data = schemas.APIKeyUpdate(group_ids=group_ids)
                            crud.update_api_key(db, int(edit_key_id.text), update_data)
                            ui.notify(get_text('api_key_updated'), color='positive')
                            refresh_keys_table()
                            edit_key_dialog.close()

                        with ui.row():
                            ui.button(get_text('save'), on_click=handle_edit_key, color='primary')
                            ui.button(get_text('cancel'), on_click=edit_key_dialog.close)

                    def open_edit_key_dialog(e):
                        row = e.args
                        edit_key_id.text = str(row['id'])
                        group_names = [g.name for g in crud.get_groups(db) if g.id in row['group_ids']]
                        edit_group_select.value = group_names
                        edit_key_dialog.open()

                    def handle_toggle_key(e):
                        row = e.args
                        update_data = schemas.APIKeyUpdate(is_active=not row['is_active'])
                        crud.update_api_key(db, row['id'], update_data)
                        ui.notify(get_text('api_key_status_changed'), color='positive')
                        refresh_keys_table()

                    async def open_delete_key_dialog(e):
                        row = e.args
                        with ui.dialog() as delete_dialog, ui.card():
                            ui.label(get_text('delete_api_key_confirm').format(key_display=row['key_display']))
                            with ui.row():
                                def perform_delete():
                                    crud.delete_api_key(db, row['id'])
                                    ui.notify(get_text('api_key_deleted'), color='negative')
                                    refresh_keys_table()
                                    delete_dialog.close()
                                ui.button(get_text('delete'), on_click=perform_delete, color='negative')
                                ui.button(get_text('cancel'), on_click=delete_dialog.close)
                        await delete_dialog

                    def handle_copy_key(e):
                        key_to_copy = e.args
                        ui.run_javascript(f"navigator.clipboard.writeText('{key_to_copy}')")
                        ui.notify(get_text('copied_to_clipboard'), color='positive')

                    def handle_view_key(e):
                        key = e.args
                        ui.notify(f"Key: {key}", color='info', duration=10)

                    def handle_open_remote(e):
                        key = e.args
                        ui.navigate.to(f'/remote?key={key}', new_tab=True)

                    keys_table.on('view-key', handle_view_key)
                    keys_table.on('copy-key', handle_copy_key)
                    keys_table.on('open_remote', handle_open_remote)
                    keys_table.on('edit_key', open_edit_key_dialog)
                    keys_table.on('toggle_key', handle_toggle_key)
                    keys_table.on('delete_key', open_delete_key_dialog)

                    refresh_keys_table()

                with ui.tab_panel(settings_tab):
                    with ui.row().classes('w-full items-center'):
                        ui.label(get_text('settings')).classes('text-h6')
                    
                    with ui.card().classes('w-full mt-4'):
                        ui.label(get_text('failover_settings')).classes('text-lg font-medium')
                        ui.label(get_text('failover_description')).classes('text-sm text-gray-500 mb-4')
                        
                        # Fetch current settings or use defaults
                        failover_count_setting = crud.get_setting(db, 'failover_threshold_count')
                        failover_period_setting = crud.get_setting(db, 'failover_threshold_period_minutes')
                        
                        failover_count_input = ui.number(
                            label=get_text('failure_count_threshold'),
                            value=int(failover_count_setting.value) if failover_count_setting else 2,
                            min=1
                        ).props('filled')
                        
                        failover_period_input = ui.number(
                            label=get_text('failure_period_minutes'),
                            value=int(failover_period_setting.value) if failover_period_setting else 5,
                            min=1
                        ).props('filled')

                        def save_settings():
                            try:
                                crud.update_setting(db, 'failover_threshold_count', str(int(failover_count_input.value)))
                                crud.update_setting(db, 'failover_threshold_period_minutes', str(int(failover_period_input.value)))
                                ui.notify(get_text('settings_saved'), color='positive')
                            except Exception as e:
                                ui.notify(f"Error saving settings: {e}", color='negative')

                        ui.button(get_text('save'), on_click=save_settings, color='primary').classes('mt-4')

        else:
            # If the user is not authenticated, show the new login page.
            async def try_login():
                """Try to log the user in and display errors on failure."""
                username.error = None
                password.error = None

                if not username.value or not password.value:
                    if not username.value:
                        username.error = 'Please enter a username'
                    if not password.value:
                        password.error = 'Please enter a password'
                    ui.notify('Please fill in all fields', color='warning', position='top')
                    return

                if username.value == ADMIN_USERNAME and password.value == ADMIN_PASSWORD:
                    app.storage.user['authenticated'] = True
                    ui.notify('Login successful!', color='positive', position='top')
                    await asyncio.sleep(1)
                    ui.navigate.reload()
                else:
                    username.error = 'Incorrect username or password'
                    password.error = 'Incorrect username or password'
                    password.value = ''
                    ui.notify('Login failed, please check your username and password', color='negative', position='top')

            # Add custom fonts and styling to the page head
            ui.add_head_html('''
                <style>
                    @import url('/css/css2?family=Noto+Sans:wght@300;400;500;700&display=swap');
                    body { font-family: 'Noto Sans', sans-serif; }
                    .nicegui-content { padding: 0 !important; }
                    .login-bg {
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 100%;
                        overflow: hidden;
                        z-index: 0;
                    }
                    .login-bg canvas {
                        width: 100% !important;
                        height: 100% !important;
                    }
                    .brand-content { z-index: 1; }
                </style>
            ''')

            # Set page background
            ui.query('body').style(f'background-color: #F3F4F6;')

            with ui.element('div').classes('flex w-screen h-screen overflow-y-hidden relative'):
                # Left Panel (Login Form) - 40% width
                with ui.element('div').classes('w-full lg:w-[40%] h-full bg-[#111827] flex flex-col justify-center items-center p-8 relative'):
                    with ui.element('div').classes('absolute top-4 right-4 z-10'):
                        with ui.button(icon='language').props('flat text-color="white"'):
                            with ui.menu():
                                ui.menu_item('English', on_click=lambda: set_language('en'))
                                ui.menu_item('中文(简体)', on_click=lambda: set_language('zh-CN'))
                                ui.menu_item('中文(繁體)', on_click=lambda: set_language('zh-TW'))
                                ui.menu_item('한국어', on_click=lambda: set_language('ko'))
                                ui.menu_item('日本語', on_click=lambda: set_language('ja'))
                    with ui.card().classes('w-full max-w-md p-8 rounded-lg shadow-xl bg-transparent text-white'):
                        # Brand Logo and Title
                        with ui.element('div').classes('flex flex-col items-center text-center mb-8 w-full brand-content'):
                            ui.image('/images/favicon.png').classes('w-16 h-16')
                            ui.label(get_text('niceapi_title')).classes('text-5xl font-bold mt-4')
                            ui.label(get_text('niceapi_subtitle')).classes('text-xl font-light text-gray-300 mt-2')

                        # Username Input
                        username = ui.input(placeholder=get_text('username')) \
                            .props('outlined dense dark color="white" bg-color="rgba(255, 255, 255, 0.1)"') \
                            .classes('w-full text-lg')
                        with username.add_slot('prepend'):
                            ui.icon('o_person', color='white').classes('flex-center')
                        username.on('update:model-value', lambda: setattr(username, 'error', None))
                        username.on('keydown.enter', try_login)

                        # Password Input
                        password = ui.input(placeholder=get_text('password'), password=True) \
                            .props('outlined dense dark color="white" bg-color="rgba(255, 255, 255, 0.1)"') \
                            .classes('w-full mt-4 text-lg')
                        with password.add_slot('prepend'):
                            ui.icon('o_lock', color='white').classes('flex-center')
                        password.on('update:model-value', lambda: setattr(password, 'error', None))
                        password.on('keydown.enter', try_login)

                        # Login Button
                        ui.button(get_text('login'), on_click=try_login).props('color="primary" text-color="white" size="lg"').classes('w-full mt-8 py-3 text-lg font-bold')
                        
                        # Footer
                        with ui.row().classes('w-full justify-center mt-12'):
                            ui.label(get_text('copyright')).classes('text-xs text-gray-400')
                
                # Right Panel (Image) - 60% width, hidden on small screens
                with ui.element('div').classes('w-full lg:w-[60%] h-full lg:flex'):
                    ui.image('/images/bg.png').classes('w-full h-full object-cover')
            
            # JavaScript for the animated background
            ui.add_body_html(f'''
                <script src="/js/three.min.js"></script>
                <script>
                    document.addEventListener('DOMContentLoaded', () => {{
                        const container = document.querySelector('.login-bg');
                        if (!container) return;

                        const scene = new THREE.Scene();
                        const camera = new THREE.PerspectiveCamera(75, container.offsetWidth / container.offsetHeight, 0.1, 1000);
                        const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
                        renderer.setSize(container.offsetWidth, container.offsetHeight);
                        container.appendChild(renderer.domElement);

                        const particles = [];
                        const particleCount = 150;

                        for (let i = 0; i < particleCount; i++) {{
                            const geometry = new THREE.SphereGeometry(Math.random() * 0.03, 8, 8);
                            const material = new THREE.MeshBasicMaterial({{ color: 0xFFFFFF, transparent: true, opacity: Math.random() * 0.5 + 0.2 }});
                            const particle = new THREE.Mesh(geometry, material);
                            
                            particle.position.x = (Math.random() - 0.5) * 10;
                            particle.position.y = (Math.random() - 0.5) * 10;
                            particle.position.z = (Math.random() - 0.5) * 10;
                            
                            particle.velocity = new THREE.Vector3(
                                (Math.random() - 0.5) * 0.005,
                                (Math.random() - 0.5) * 0.005,
                                (Math.random() - 0.5) * 0.005
                            );
                            
                            particles.push(particle);
                            scene.add(particle);
                        }}
                        
                        camera.position.z = 5;

                        function animate() {{
                            requestAnimationFrame(animate);

                            particles.forEach(p => {{
                                p.position.add(p.velocity);

                                if (p.position.x < -5 || p.position.x > 5) p.velocity.x = -p.velocity.x;
                                if (p.position.y < -5 || p.position.y > 5) p.velocity.y = -p.velocity.y;
                                if (p.position.z < -5 || p.position.z > 5) p.velocity.z = -p.velocity.z;
                            }});

                            renderer.render(scene, camera);
                        }}

                        animate();

                        window.addEventListener('resize', () => {{
                            camera.aspect = container.offsetWidth / container.offsetHeight;
                            camera.updateProjectionMatrix();
                            renderer.setSize(container.offsetWidth, container.offsetHeight);
                        }});
                    }});
                </script>
            ''')
    
    @ui.page('/remote')
    async def remote_page(request: Request, db: Session = Depends(get_db)):
        # Try to get key from URL or Session Storage
        url_key = request.query_params.get('key')
        api_key_str = url_key or app.storage.user.get('remote_api_key')

        if not api_key_str:
            with ui.column().classes('w-full h-screen flex-center'):
                ui.label("Invalid Access: Key is required").classes('text-h4 text-red')
            return

        api_key_obj = crud.get_api_key_by_key(db, api_key_str)
        if not api_key_obj or not api_key_obj.is_active:
            # If stored key is invalid, clear it
            if not url_key:
                app.storage.user.pop('remote_api_key', None)
            with ui.column().classes('w-full h-screen flex-center'):
                ui.label("Invalid or Inactive API Key").classes('text-h4 text-red')
            return

        # If URL key is valid, store it for future sessions
        if url_key:
            app.storage.user['remote_api_key'] = url_key

        ui.add_head_html('''
            <style>
            .model-card {
                user-select: none;
                transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.3s ease;
                position: relative;
                z-index: 1;
            }
            .model-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                z-index: 2;
            }
            .moving-up {
                z-index: 10 !important;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2) !important;
            }
            </style>
            <script>
            async function animateToTop(cardId, containerId) {
                const card = document.getElementById(cardId);
                const container = document.getElementById(containerId);
                if (!card || !container) return;
                
                const cards = Array.from(container.querySelectorAll('.model-card'));
                const firstCard = cards[0];
                if (!firstCard || firstCard === card) return;
                
                const cardRect = card.getBoundingClientRect();
                const firstRect = firstCard.getBoundingClientRect();
                const diffY = firstRect.top - cardRect.top;
                
                card.classList.add('moving-up');
                card.style.transform = `translateY(${diffY}px)`;
                
                // Shift other cards down that are above the clicked card
                cards.forEach(c => {
                    const cRect = c.getBoundingClientRect();
                    if (c !== card && cRect.top < cardRect.top) {
                        c.style.transform = `translateY(${cardRect.height + 8}px)`; // height + gap
                    }
                });

                return new Promise(resolve => setTimeout(resolve, 450));
            }
            </script>
        ''')

        ui.colors(primary='#2F6BFF')

        with ui.header(elevated=True).style('background-color: #111827').classes('p-4'):
            ui.label(f"{get_text('api_management')} - {get_text('remote')}").classes('text-h5')

        container = ui.column().classes('w-full p-4 max-w-4xl mx-auto')

        async def refresh_remote_view():
            container.clear()
            db.expire_all()
            
            # Re-fetch to get latest data
            current_key = crud.get_api_key_by_key(db, api_key_str)
            
            with container:
                if not current_key.groups:
                    ui.label("No groups assigned to this API Key.").classes('text-h6 text-grey-6 flex-center mt-10')
                    return

                for group in current_key.groups:
                    with ui.card().classes('w-full mb-6 p-4 shadow-md'):
                        with ui.row().classes('w-full items-center mb-4 border-b pb-2'):
                            ui.icon('group', color='primary', size='md')
                            ui.label(group.name).classes('text-h6 font-bold')
                            ui.space()
                            ui.badge(f"ID: {group.id}").props('color="blue-1" text-color="blue-9"')
                        
                        # Get associations to get priorities
                        associations = db.query(models.provider_group_association).filter_by(group_id=group.id).all()
                        associations.sort(key=lambda x: x.priority)
                        
                        if not associations:
                            ui.label("No models in this group.").classes('text-italic text-grey-6')
                            continue

                        # Container for items
                        item_col = ui.column().classes('w-full gap-2')
                        container_id = f"group-list-{group.id}"
                        item_col.props(f'id="{container_id}"')
                        
                        with item_col:
                            for i, assoc in enumerate(associations):
                                provider = db.query(models.ApiProvider).filter_by(id=assoc.provider_id).first()
                                if not provider: continue
                                
                                card_id = f"card-{group.id}-{provider.id}"
                                # Make the card clickable to set as top
                                card = ui.card().classes('w-full p-0 mb-1 shadow-sm border overflow-hidden model-card cursor-pointer')
                                card.props(f'id="{card_id}"')
                                
                                async def handle_click(g_id=group.id, p_id=provider.id, assocs=associations, c_id=card_id, ct_id=container_id, idx=i):
                                    if idx == 0: return # Already top
                                    await ui.run_javascript(f'animateToTop("{c_id}", "{ct_id}")', timeout=1.0)
                                    await move_to_top(g_id, p_id, assocs)

                                card.on('click', handle_click)
                                with card:
                                    with ui.row().classes('w-full items-center no-wrap'):
                                        # Sequence number
                                        with ui.element('div').classes('p-4 bg-gray-50 border-r flex flex-center h-full w-14'):
                                            ui.label(str(i + 1)).classes('text-h6 text-grey-6 font-bold seq-label')
                                        
                                        # Content
                                        with ui.column().classes('gap-0 flex-grow p-3'):
                                            # Model as primary
                                            ui.label(provider.model).classes('text-subtitle1 font-medium')
                                            # Alias (Name) as secondary gray
                                            ui.label(provider.name).classes('text-caption text-grey-5')
                                        
                                        # Status Indicator (Only show for Top item)
                                        with ui.row().classes('items-center p-3 w-16 justify-center'):
                                            if i == 0:
                                                ui.icon('check_circle', color='positive', size='md')
                                            else:
                                                ui.element('div').classes('w-6 h-6') # Empty space for alignment
                                            
                                            # Removed Px badge as requested

                        async def move_to_top(group_id, provider_id, current_associations):
                            # Current pids in order
                            pids = [a.provider_id for a in current_associations]
                            if provider_id in pids:
                                pids.remove(provider_id)
                                pids.insert(0, provider_id)
                                
                                for idx, pid in enumerate(pids):
                                    crud.add_provider_to_group(db, provider_id=pid, group_id=group_id, priority=idx+1)
                                
                                ui.notify(get_text('save_success'), color='positive')
                                await refresh_remote_view()


        await refresh_remote_view()

    # The db session is now managed by FastAPI's dependency injection,
    # so the app.on_shutdown hook is no longer needed.
    # app.on_shutdown(db.close)