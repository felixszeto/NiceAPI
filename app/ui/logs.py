from nicegui import ui
from sqlalchemy.orm import Session
import json
import re
from .. import crud
from ..language import get_text
from .common import loading_animation

def render_logs(db: Session, container: ui.element, panel: ui.tab_panel):
    def get_logs_with_provider_info(filter_mode='all'):
        db.commit()
        db.expire_all()
        filter_success = {'successful': True, 'failed': False}.get(filter_mode)
        logs = crud.get_call_logs(db, limit=50, filter_success=filter_success)
        log_data = []
        for log in logs:
            data = {key: getattr(log, key) for key in log.__table__.columns.keys()}
            # Prefer data from details table, fallback to legacy columns
            data['request_body'] = log.details.request_body if log.details else log.request_body
            data['response_body'] = log.details.response_body if log.details else log.response_body
            
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

    with container:
        with ui.row().classes('w-full items-center mb-4'):
            ui.label(get_text('call_logs')).classes('text-h6')
            ui.space()
            ui.button(get_text('refresh_logs'), on_click=refresh_logs_table, icon='refresh', color='primary').props('flat')
        
        with ui.tabs().classes('mb-4') as log_filter_tabs:
            ui.tab('all', label=get_text('all_requests'))
            ui.tab('successful', label=get_text('successful_requests'))
            ui.tab('failed', label=get_text('failed_requests'))
        log_filter_tabs.on('update:model-value', lambda: logs_table.update_rows(get_logs_with_provider_info(log_filter_tabs.value)))

        # Dialog for error details
        with ui.dialog() as error_dialog, ui.card().style('min-width: 400px;'):
            ui.label(get_text('error_details')).classes('text-h6')
            error_display = ui.label('').classes('w-full whitespace-pre-wrap border p-4 rounded')
            with ui.row().classes('w-full justify-end'):
                ui.button(get_text('close'), on_click=error_dialog.close)

        # Dialog for call details
        with ui.dialog() as response_dialog, ui.card().classes('w-[95vw] max-w-none h-[95vh] overflow-auto'):
            with ui.row().classes('w-full no-wrap justify-between items-center mb-2 sticky top-0 bg-white z-10'):
                ui.label(get_text('call_details')).classes('text-h6')
                ui.button(icon='close', on_click=response_dialog.close).props('flat round dense')
            
            with ui.column().classes('w-full gap-6'):
                # Request Section
                with ui.expansion(get_text('request_body'), icon='payload').classes('w-full bg-blue-50/30 rounded border'):
                    req_body_area = ui.label('').classes('w-full whitespace-pre-wrap break-all font-mono text-sm bg-white p-4 border-t')
                
                with ui.card().classes('w-full p-4'):
                    ui.label(get_text('request_text')).classes('text-h6 font-bold mb-2 text-blue-800')
                    req_text_area = ui.label('').classes('w-full whitespace-pre-wrap break-all text-base bg-white p-4 border rounded')

                # Response Section
                with ui.expansion(get_text('response_body'), icon='output').classes('w-full bg-green-50/30 rounded border'):
                    resp_body_area = ui.label('').classes('w-full whitespace-pre-wrap break-all font-mono text-sm bg-white p-4 border-t')
                
                with ui.card().classes('w-full p-4'):
                    ui.label(get_text('response_text')).classes('text-h6 font-bold mb-2 text-green-800')
                    resp_text_area = ui.label('').classes('w-full whitespace-pre-wrap break-all text-base bg-white p-4 border rounded')

        def format_body(body_str):
            if not body_str: return "No content."
            try: return json.dumps(json.loads(body_str), indent=2, ensure_ascii=False)
            except: return body_str

        def extract_text(body_str, is_req=True):
            if not body_str: return ""
            try:
                data = json.loads(body_str)
                if is_req: return "\n".join([f"[{m.get('role', 'user')}]: {m.get('content', '')}" for m in data.get('messages', [])])
                choices = data.get('choices', [])
                if choices:
                    msg = choices[0].get('message', {})
                    if msg: return msg.get('content', "")
                return ""
            except:
                if not is_req:
                    matches = re.findall(r'"content":\s*"([^"]*)"', body_str)
                    if matches: return "".join(matches).replace('\\n', '\n').replace('\\"', '"')
                return body_str

        def show_details(row):
            req_body_area.text = format_body(row.get('request_body'))
            resp_body_area.text = format_body(row.get('response_body'))
            req_text_area.text = extract_text(row.get('request_body'), True)
            resp_text_area.text = extract_text(row.get('response_body'), False)
            response_dialog.open()

        logs_table = ui.table(columns=[
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
        ], rows=get_logs_with_provider_info(), row_key='id').classes('w-full')

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
        logs_table.add_slot('body-cell-cost', '''
            <q-td :props="props">
                {{ props.row.cost !== null ? props.row.cost.toFixed(6) : 'N/A' }}
            </q-td>
        ''')
        logs_table.on('view_log', lambda e: show_details(e.args))
        logs_table.on('view_error', lambda e: (setattr(error_display, 'text', e.args.get('error_message') or "No error message."), error_dialog.open()))
        panel.on('show', refresh_logs_table)