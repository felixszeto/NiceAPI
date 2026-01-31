from nicegui import ui
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..language import get_text
from .common import loading_animation

def render_api_keys(db: Session, container: ui.element, panel: ui.tab_panel):
    def get_all_api_keys():
        db.expire_all()
        keys = crud.get_api_keys(db)
        return [{
            "id": key.id,
            "key_display": f"{key.key[:5]}...{key.key[-4:]}",
            "key": key.key,
            "is_active": key.is_active,
            "created_at": key.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_used_at": key.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if key.last_used_at else get_text('never'),
            "groups": ", ".join([g.name for g in key.groups]),
            "group_ids": [g.id for g in key.groups],
            "call_count": key.call_count
        } for key in keys]

    def refresh_keys_table():
        keys_table.update_rows(get_all_api_keys())

    async def refresh_keys_table_async():
        async with loading_animation():
            refresh_keys_table()
        ui.notify(get_text('api_keys_refreshed'), color='positive')

    with container:
        with ui.row().classes('w-full items-center mb-4'):
            ui.label(get_text('api_keys')).classes('text-h6')
            ui.space()
            ui.button(get_text('refresh_api_keys'), on_click=refresh_keys_table_async, icon='refresh', color='primary').props('flat')

        # Generate Key Success Dialog
        with ui.dialog() as show_key_dialog, ui.card().style('min-width: 400px;'):
            ui.label(get_text('api_key_generated_successfully')).classes('text-h6')
            ui.label(get_text('copy_key_instruction')).classes('text-sm text-gray-500')
            key_display_label = ui.input(label=get_text('your_new_api_key')).props('readonly filled').classes('w-full')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(get_text('close'), on_click=show_key_dialog.close, color='primary')

        # Add Key Dialog
        with ui.dialog() as add_key_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px] pb-12'):
            ui.label(get_text('create_new_api_key')).classes('text-h6')
            
            async def refresh_group_options():
                async with loading_animation():
                    db.expire_all()
                    all_group_names = [g.name for g in crud.get_groups(db)]
                    group_select.options = all_group_names
                    group_select.update()
                ui.notify(get_text('group_list_refreshed'), color='info')

            with ui.row().classes('w-full no-wrap items-center'):
                group_names = [g.name for g in crud.get_groups(db)]
                group_select = ui.select(group_names, multiple=True, label=get_text('assign_to_groups')).props('filled').classes('flex-grow')
                ui.button(icon='refresh', on_click=refresh_group_options).props('flat dense color=primary')

            def handle_add_key():
                if not group_select.value:
                    ui.notify(get_text('assign_to_at_least_one_group_error'), color='negative')
                    return
                ids = [g.id for g in crud.get_groups(db) if g.name in group_select.value]
                new_key = crud.create_api_key(db, schemas.APIKeyCreate(group_ids=ids))
                key_display_label.value = new_key.key
                show_key_dialog.open()
                refresh_keys_table()
                add_key_dialog.close()
            with ui.row():
                ui.button(get_text('create'), on_click=handle_add_key, color='primary')
                ui.button(get_text('cancel'), on_click=add_key_dialog.close)
        
        ui.button(get_text('create_api_key'), on_click=add_key_dialog.open, color='primary').classes('mb-4')
        
        keys_table = ui.table(columns=[
            {'name': 'key_display', 'label': get_text('key'), 'field': 'key_display', 'align': 'left'},
            {'name': 'is_active', 'label': get_text('active'), 'field': 'is_active', 'sortable': True},
            {'name': 'groups', 'label': get_text('groups'), 'field': 'groups', 'align': 'left', 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
            {'name': 'call_count', 'label': get_text('api_calls'), 'field': 'call_count', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
            {'name': 'created_at', 'label': get_text('created_at'), 'field': 'created_at', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
            {'name': 'last_used_at', 'label': get_text('last_used'), 'field': 'last_used_at', 'sortable': True, 'classes': 'mobile-hide', 'headerClasses': 'mobile-hide'},
            {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
        ], rows=get_all_api_keys(), row_key='id').classes('w-full')

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

        # Edit Key Dialog
        with ui.dialog() as edit_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
            ui.label(get_text('edit_api_key')).classes('text-h6')
            edit_key_id = ui.label().classes('hidden')
            
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
                ids = [g.id for g in crud.get_groups(db) if g.name in edit_group_select.value]
                crud.update_api_key(db, int(edit_key_id.text), schemas.APIKeyUpdate(group_ids=ids))
                ui.notify(get_text('api_key_updated'), color='positive')
                refresh_keys_table(); edit_dialog.close()
            with ui.row():
                ui.button(get_text('save'), on_click=handle_edit_key, color='primary')
                ui.button(get_text('cancel'), on_click=edit_dialog.close)

        keys_table.on('view-key', lambda e: ui.notify(f"Key: {e.args}", color='info', duration=10))
        keys_table.on('copy-key', lambda e: (ui.run_javascript(f"navigator.clipboard.writeText('{e.args}')"), ui.notify(get_text('copied_to_clipboard'), color='positive')))
        keys_table.on('open_remote', lambda e: ui.navigate.to(f'/remote?key={e.args}', new_tab=True))
        keys_table.on('edit_key', lambda e: (
            setattr(edit_key_id, 'text', str(e.args['id'])),
            setattr(edit_group_select, 'value', [g.name for g in crud.get_groups(db) if g.id in e.args['group_ids']]),
            edit_dialog.open()
        ))
        keys_table.on('toggle_key', lambda e: (
            crud.update_api_key(db, e.args['id'], schemas.APIKeyUpdate(is_active=not e.args['is_active'])),
            ui.notify(get_text('api_key_status_changed'), color='positive'),
            refresh_keys_table()
        ))
        keys_table.on('delete_key', lambda e: open_delete_key_confirm(e.args))

        def open_delete_key_confirm(row):
            with ui.dialog() as delete_dialog, ui.card():
                ui.label(get_text('delete_api_key_confirm').format(key_display=row['key_display']))
                with ui.row():
                    def handle_delete():
                        crud.delete_api_key(db, row['id']); ui.notify(get_text('api_key_deleted'), color='negative'); refresh_keys_table(); delete_dialog.close()
                    ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                    ui.button(get_text('cancel'), on_click=delete_dialog.close)
            delete_dialog.open()
        panel.on('show', refresh_keys_table_async)