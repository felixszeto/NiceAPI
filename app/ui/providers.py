from nicegui import ui
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import asyncio
import httpx
from .. import crud, models, schemas
from ..language import get_text
from .common import loading_animation

def render_providers(db: Session, container: ui.element, panel: ui.tab_panel):
    # 用於追蹤主頁面的搜尋關鍵字
    provider_search_state = {'v': ''}

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

    def refresh_providers_table(search_val=None):
        if search_val is not None:
            if isinstance(search_val, (list, tuple)) and len(search_val) > 0:
                search_val = search_val[0]
            provider_search_state['v'] = str(search_val)
        v = provider_search_state['v']
        table.rows = get_all_providers_as_dict(search_query=v)
        table.update()

    async def refresh_providers_table_async():
        async with loading_animation():
            refresh_providers_table()
        ui.notify(get_text('providers_refreshed'), color='positive')

    with container:
        with ui.row().classes('w-full items-center mb-4 gap-4'):
            ui.label(get_text('providers')).classes('text-h6')
            ui.space()
            with ui.row().classes('items-center gap-2'):
                ui.input(placeholder=get_text('search_models')).props('outlined dense icon="search"').classes('w-64').on('update:model-value', lambda e: refresh_providers_table(e.args))
            
            async def open_sync_models_dialog():
                providers = crud.get_providers(db)
                unique_sync_targets = {}
                for p in providers:
                    target_key = (p.api_endpoint, p.api_key)
                    if target_key not in unique_sync_targets:
                        unique_sync_targets[target_key] = p.name
                
                options = {}
                for (endpoint, key), name in unique_sync_targets.items():
                    options[f"{endpoint}|{key}"] = f"{name} [{endpoint}] ({key[:5]}...{key[-4:]})"

                if not options:
                    ui.notify("No providers available to sync.", color='warning')
                    return

                with ui.dialog() as sync_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
                    ui.label(get_text('select_providers_to_sync')).classes('text-h6')
                    target_select = ui.select(options=options, multiple=True, label=get_text('providers')).props('filled use-chips').classes('w-full')
                    
                    with ui.row():
                        ui.button(get_text('select_all'), on_click=lambda: setattr(target_select, 'value', list(options.keys()))).props('flat')

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
                                    base_url = endpoint.split('/v1/chat/completions')[0]
                                    models_url = f"{base_url.rstrip('/')}/v1/models"
                                    async with httpx.AsyncClient() as client:
                                        try:
                                            response = await client.get(models_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
                                            if response.status_code == 200:
                                                remote_models_data = response.json()
                                                remote_model_ids = [m['id'] for m in remote_models_data.get('data', [])]
                                                db_providers = db.query(models.ApiProvider).filter(models.ApiProvider.api_endpoint == endpoint, models.ApiProvider.api_key == api_key).all()
                                                db_model_map = {p.model: p for p in db_providers}
                                                for model_id in remote_model_ids:
                                                    triplet_exists = db.query(models.ApiProvider).filter(models.ApiProvider.api_endpoint == endpoint, models.ApiProvider.api_key == api_key, models.ApiProvider.model == model_id).first()
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

        # Add Provider Dialog
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
                if not name_input.value or not endpoint_input.value or not key_input.value or not model_input.value:
                    ui.notify("Please fill in all required fields.", color='warning')
                    return
                url = endpoint_input.value.strip()
                if url.endswith('/v1') or url.endswith('/v1/'):
                    final_endpoint = f"{url.rstrip('/')}/chat/completions"
                else:
                    parsed = urlparse(url)
                    if not parsed.path or parsed.path == '/':
                        final_endpoint = f"{url.rstrip('/')}/v1/chat/completions"
                    else:
                        final_endpoint = url
                provider_data = schemas.ApiProviderCreate(name=name_input.value, api_endpoint=final_endpoint, api_key=key_input.value, model=model_input.value, price_per_million_tokens=price_input.value, type=type_select.value, is_active=active_toggle.value)
                crud.create_provider(db, provider_data)
                ui.notify(get_text('provider_added').format(name=name_input.value), color='positive')
                refresh_providers_table()
                add_dialog.close()

            async def handle_import():
                if not base_url_input.value or not api_key_input.value:
                    ui.notify("Please fill in both Base URL and API Key.", color='warning')
                    return
                progress_container.visible = True
                try:
                    api_url = "http://127.0.0.1:8001/api/import-models/"
                    payload = {"base_url": base_url_input.value, "api_key": api_key_input.value, "alias": alias_input.value, "default_type": default_type_select.value, "filter_mode": filter_mode_select.value, "filter_keyword": filter_keyword_input.value}
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", api_url, json=payload, timeout=None) as response:
                            if response.status_code != 200:
                                error_detail = (await response.aread()).decode()
                                ui.notify(f"Error: {error_detail}", color='negative')
                                return
                            total = 0
                            async for line in response.aiter_lines():
                                if line.startswith('data:'):
                                    data = line[len('data:'):].strip()
                                    if data.startswith('TOTAL='):
                                        total = int(data.split('=')[1])
                                    elif data.startswith('PROGRESS='):
                                        count = int(data.split('=')[1])
                                        if total > 0:
                                            progress.value = count / total
                                            progress_label.text = f'{(count/total)*100:.1f}%'
                                    elif data.startswith('DONE='):
                                        ui.notify(data.split('=', 1)[1], color='positive')
                                        refresh_providers_table()
                                        await asyncio.sleep(1)
                                        add_dialog.close()
                                    elif data.startswith('ERROR='):
                                        ui.notify(data.split('=', 1)[1], color='negative')
                except Exception as e:
                    ui.notify(f"An unexpected error occurred: {e}", color='negative')
                finally:
                    progress_container.visible = False

        def open_quick_remove_dialog():
            with ui.dialog() as dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[250px]'):
                ui.label(get_text('quick_remove_by_api_key')).classes('text-h6')
                def get_keys_with_alias():
                    providers = crud.get_providers(db)
                    key_info = {}
                    for p in providers:
                        key_info[p.api_key] = f"{p.name} [{p.api_endpoint}] ({p.api_key[:5]}...{p.api_key[-4:]})"
                    return key_info
                def handle_quick_remove(key_select):
                    if not key_select.value:
                        ui.notify('An API Key must be selected.', color='negative')
                        return
                    deleted_count = crud.delete_providers_by_key(db, key_select.value)
                    ui.notify(f'Removed {deleted_count} providers.', color='positive')
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

        # Edit Dialog
        with ui.dialog() as edit_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[500px]'):
            ui.label(get_text('edit_provider')).classes('text-h6')
            edit_id_label = ui.label()
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
                else:
                    parsed = urlparse(url)
                    if not parsed.path or parsed.path == '/':
                        final_endpoint = f"{url.rstrip('/')}/v1/chat/completions"
                    else:
                        final_endpoint = url
                provider_data = {"name": edit_name_input.value, "api_endpoint": final_endpoint, "model": edit_model_input.value, "price_per_million_tokens": edit_price_input.value, "type": edit_type_select.value, "is_active": edit_active_toggle.value}
                if edit_key_input.value: provider_data['api_key'] = edit_key_input.value
                crud.update_provider(db, edit_id_label.text, provider_data)
                ui.notify(get_text('provider_updated').format(name=edit_name_input.value), color='positive')
                refresh_providers_table()
                edit_dialog.close()
            with ui.row():
                ui.button(get_text('save'), on_click=handle_edit, color='primary')
                ui.button(get_text('cancel'), on_click=edit_dialog.close)

        table.on('edit', lambda e: (
            setattr(edit_id_label, 'text', e.args['id']),
            setattr(edit_name_input, 'value', e.args['name']),
            setattr(edit_endpoint_input, 'value', e.args['api_endpoint']),
            setattr(edit_key_input, 'value', ''),
            setattr(edit_model_input, 'value', e.args['model']),
            setattr(edit_price_input, 'value', e.args['price_per_million_tokens']),
            setattr(edit_type_select, 'value', e.args['type']),
            setattr(edit_active_toggle, 'value', e.args['is_active']),
            edit_dialog.open()
        ))
        
        table.on('delete', lambda e: open_delete_confirm(e.args))
        panel.on('show', refresh_providers_table_async)

        def open_delete_confirm(row):
            with ui.dialog() as delete_dialog, ui.card():
                ui.label(get_text('delete_provider_confirm').format(name=row['name']))
                with ui.row():
                    def handle_delete():
                        crud.delete_provider(db, row['id'])
                        ui.notify(get_text('provider_deleted').format(name=row['name']), color='negative')
                        refresh_providers_table()
                        delete_dialog.close()
                    ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                    ui.button(get_text('cancel'), on_click=delete_dialog.close)
            delete_dialog.open()