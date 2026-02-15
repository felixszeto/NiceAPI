from nicegui import ui
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..language import get_text
from .common import loading_animation

def render_groups(db: Session, container: ui.element, panel: ui.tab_panel):
    def get_groups_with_providers():
        db.commit() # 結束當前事務，確保讀取到最新數據
        db.expire_all()
        groups = crud.get_groups(db)
        providers = crud.get_providers(db, limit=None)
        providers_dicts = [{key: getattr(p, key) for key in p.__table__.columns.keys()} for p in providers]
        group_data = []
        for group in groups:
            associations = db.query(models.ProviderGroupAssociation).filter_by(group_id=group.id).all()
            group_providers = {assoc.provider_id: {"priority": assoc.priority} for assoc in associations}
            group_data.append({'id': group.id, 'name': group.name, 'providers': group_providers})
        return group_data, providers_dicts

    def build_groups_view():
        groups_container.clear()
        group_data, all_providers = get_groups_with_providers()
        if not group_data:
            with groups_container: ui.label(get_text('no_groups_created'))
            return

        for group in group_data:
            with groups_container, ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label(group['name']).classes('text-h6')
                        ui.label(f"{get_text('id')}: {group['id']} | {len(group['providers'])} {get_text('providers')}").classes('text-caption text-gray-500')
                    ui.space()
                    with ui.row().classes('gap-2'):
                        ui.button(get_text('manage_providers'), icon='settings', on_click=lambda g=group: open_manage_dialog(g)).props('outline color="primary"')
                        ui.button(icon='delete', on_click=lambda g=group: open_delete_group_dialog(g['id'], g['name']), color='negative').props('flat round')
                if group['providers']:
                    with ui.row().classes('w-full mt-2 gap-2'):
                        sorted_pids = sorted(group['providers'].keys(), key=lambda x: group['providers'][x]['priority'])
                        for pid in sorted_pids[:10]:
                            p_obj = next((p for p in all_providers if p['id'] == pid), None)
                            if p_obj:
                                ui.badge(f"P{group['providers'][pid]['priority']}: {p_obj['name']}.{p_obj['model']}").props('color="blue-2" text-color="blue-9"').classes('px-2 py-1')
                        if len(sorted_pids) > 10: ui.badge(f"+ {len(sorted_pids)-10} ...").props('color="grey-4" text-color="grey-8"')

    async def open_manage_dialog(group):
        group_data_ref, all_providers = get_groups_with_providers()
        with ui.dialog() as manage_dialog, ui.card().style('width: 90vw; max-width: 1000px; max-height: 90vh; min-height: 500px;').classes('p-0 flex flex-col no-wrap'):
            with ui.row().classes('w-full items-center justify-between p-4 bg-gray-100 flex-shrink-0'):
                ui.label(f"{get_text('manage_providers')}: {group['name']}").classes('text-h6')
                ui.button(icon='close', on_click=manage_dialog.close).props('flat round')
            
            with ui.column().classes('w-full flex-grow overflow-hidden p-0 gap-0'):
                search_input = ui.input(placeholder=get_text('search_providers')).props('outlined dense icon="search"').classes('w-full px-4 py-2 bg-white flex-shrink-0')
                rows = []
                for p in all_providers:
                    pid = p['id']
                    raw_p = group['providers'].get(pid, {}).get('priority', 0)
                    rows.append({'id': pid, 'name': p['name'], 'model': p['model'], 'selected': pid in group['providers'], 'priority': raw_p if 1 <= raw_p <= 5 else 0})

                manage_search_state = {'v': ''}
                def update_view(search_val=None):
                    if search_val is not None: manage_search_state['v'] = str(search_val[0]) if isinstance(search_val, (list, tuple)) else str(search_val)
                    v = manage_search_state['v'].lower()
                    filtered = [r for r in rows if v in r['model'].lower() or v in r['name'].lower()]
                    extra = [r for r in rows if r['selected'] and not (v in r['model'].lower() or v in r['name'].lower())]
                    final = extra + filtered
                    final.sort(key=lambda r: (0 if r['selected'] else 1, r['priority'] if r['priority'] > 0 else 999, r['name']))
                    m_table.rows = final
                    m_table.update()

                with ui.element('div').classes('w-full flex-grow overflow-auto custom-scrollbar'):
                    m_table = ui.table(columns=[
                        {'name': 'model', 'label': get_text('model'), 'field': 'model', 'sortable': True, 'align': 'left', 'classes': 'w-[200px] break-all whitespace-normal'},
                        {'name': 'alias', 'label': get_text('alias'), 'field': 'name', 'sortable': True, 'align': 'left', 'classes': 'hidden', 'headerClasses': 'hidden'},
                        {'name': 'priority', 'label': get_text('priority'), 'field': 'priority', 'sortable': True, 'align': 'center', 'style': 'width: 320px'},
                    ], rows=rows, row_key='id', pagination={'rowsPerPage': 5}).classes('w-full px-2 shadow-none border-none')
                    
                    m_table.add_slot('body-cell-model', '''
                        <q-td :props="props" :class="props.row.selected ? 'bg-blue-1' : ''">
                            <div class="column cursor-pointer" @click="$parent.$emit('toggle_select', props.row)">
                                <div class="text-weight-bold" style="white-space: normal; word-break: break-all;">{{ props.row.model }}</div>
                                <div class="text-caption text-grey-6" style="white-space: normal; word-break: break-all;">{{ props.row.name }}</div>
                            </div>
                        </q-td>
                    ''')
                    m_table.add_slot('body-cell-priority', '''
                        <q-td :props="props" :class="props.row.selected ? 'bg-blue-1' : ''">
                            <div class="row q-gutter-x-sm justify-center no-wrap">
                                <div v-for="p in [1,2,3,4,5]" :key="p" class="column items-center">
                                    <div class="text-bold text-blue-9" style="font-size: 10px; margin-bottom: -4px">P{{p}}</div>
                                    <q-toggle :model-value="props.row.priority === p" @update:model-value="val => $parent.$emit('set_p', {row: props.row, val: val ? p : 0})" dense size="sm" color="primary" />
                                </div>
                            </div>
                        </q-td>
                    ''')

                    m_table.on('set_p', lambda e: handle_priority_change(e.args, rows, update_view))
                    m_table.on('toggle_select', lambda e: handle_toggle_select(e.args, rows, update_view))
                
                search_input.on('update:model-value', lambda e: update_view(e.args))
                update_view()

            with ui.row().classes('w-full justify-end p-4 bg-gray-50 flex-shrink-0 border-t'):
                async def save_management():
                    for row in rows:
                        pid = row['id']
                        if row['selected']: crud.add_provider_to_group(db, provider_id=pid, group_id=group['id'], priority=row['priority'] if row['priority'] > 0 else 99)
                        elif pid in group['providers']: crud.remove_provider_from_group(db, provider_id=pid, group_id=group['id'])
                    ui.notify(get_text('save_success'), color='positive')
                    manage_dialog.close()
                    await refresh_groups_view()
                ui.button(get_text('cancel'), on_click=manage_dialog.close).props('flat')
                ui.button(get_text('save'), on_click=save_management, color='primary').props('unelevated')
        manage_dialog.open()

    def handle_priority_change(args, rows, update_view):
        target = next(r for r in rows if r['id'] == args['row']['id'])
        val = args['val']
        if val > 0:
            for r in sorted([r for r in rows if r['id'] != target['id'] and 0 < r['priority'] <= 5 and r['priority'] >= val], key=lambda x: x['priority'], reverse=True):
                r['priority'] += 1
                if r['priority'] > 5: r['priority'] = 0; r['selected'] = False
            target['priority'] = val; target['selected'] = True
        else: target['priority'] = 0; target['selected'] = False
        update_view()

    def handle_toggle_select(row_data, rows, update_view):
        target = next(r for r in rows if r['id'] == row_data['id'])
        target['selected'] = not target['selected']
        if not target['selected']: target['priority'] = 0
        update_view()

    async def open_delete_group_dialog(group_id, group_name):
        with ui.dialog() as delete_dialog, ui.card():
            ui.label(get_text('delete_group_confirm').format(name=group_name))
            with ui.row().classes('w-full justify-end mt-4'):
                async def handle_delete():
                    crud.delete_group(db, group_id); ui.notify(get_text('group_deleted').format(name=group_name), color='negative'); delete_dialog.close(); await refresh_groups_view()
                ui.button(get_text('cancel'), on_click=delete_dialog.close).props('flat')
                ui.button(get_text('delete'), on_click=handle_delete, color='negative')
        delete_dialog.open()

    async def refresh_groups_view():
        async with loading_animation(): build_groups_view()
        ui.notify(get_text('groups_view_refreshed'), color='positive')

    with container:
        with ui.row().classes('w-full items-center'):
            ui.label(get_text('provider_groups')).classes('text-h6')
        ui.label(get_text('groups_description')).classes('mb-4')
        with ui.dialog() as add_group_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[250px]'):
            ui.label(get_text('create_new_group')).classes('text-h6')
            name_input = ui.input(get_text('group_name')).props('filled').classes('w-full')
            async def handle_add_group():
                if not name_input.value: ui.notify(get_text('group_name_empty_error'), color='negative'); return
                if crud.get_group_by_name(db, name_input.value): ui.notify(get_text('group_exists_error').format(name=name_input.value), color='negative'); return
                crud.create_group(db, schemas.GroupCreate(name=name_input.value)); ui.notify(get_text('group_created').format(name=name_input.value), color='positive'); add_group_dialog.close(); await refresh_groups_view()
            with ui.row():
                ui.button(get_text('create'), on_click=handle_add_group, color='primary')
                ui.button(get_text('cancel'), on_click=add_group_dialog.close)
        ui.button(get_text('create_group'), on_click=add_group_dialog.open, color='primary')
        groups_container = ui.column().classes('w-full mt-4')
        panel.on('show', refresh_groups_view)
        build_groups_view()