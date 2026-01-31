from nicegui import ui
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from urllib.parse import urlparse
from .. import crud, models
from ..language import get_text
from .common import loading_animation

def render_dashboard(db: Session, container: ui.element, panel: ui.tab_panel):
    def stat_card(label, value, icon, color):
        with ui.card().classes('flex-grow glass-card p-0 overflow-hidden'):
            with ui.row().classes('no-wrap items-stretch'):
                with ui.column().classes(f'bg-{color}-500 p-4 justify-center items-center self-stretch'):
                    ui.icon(icon, color='white').classes('text-2xl')
                with ui.column().classes('p-4 justify-center'):
                    ui.label(label).classes('text-xs text-slate-500 font-medium')
                    ui.label(value).classes('text-2xl font-bold text-slate-800')

    def build_dashboard_content():
        with container:
            with ui.element('div').classes('flex flex-wrap w-full gap-6'):
                # Quick Stats
                with ui.row().classes('w-full gap-6 mb-2'):
                    db.expire_all()
                    # 只統計有分配到 provider 的請求
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
                        TAIPEI_TZ = pytz.timezone('Asia/Taipei')
                        logs = [l for l in crud.get_call_logs(db, limit=5000) if l.provider_id is not None]
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
                        logs = crud.get_call_logs(db, limit=100)
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
                                    parsed_url = urlparse(log.provider.api_endpoint)
                                    endpoint = parsed_url.netloc
                                except Exception:
                                    endpoint = log.provider.api_endpoint
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
                                    parsed_url = urlparse(log.provider.api_endpoint)
                                    endpoint = parsed_url.netloc
                                except Exception:
                                    endpoint = log.provider.api_endpoint
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
                                    endpoint = log.provider.api_endpoint
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
            container.clear()
            build_dashboard_content()
        ui.notify(get_text('dashboard_refreshed'), color='positive')

    with ui.row().classes('w-full items-center mb-4'):
        ui.label(get_text('dashboard')).classes('text-h6')
        ui.space()
        ui.button(get_text('refresh_data'), on_click=refresh_dashboard, icon='refresh', color='primary').props('flat')
    
    panel.on('show', refresh_dashboard)
    build_dashboard_content()