from nicegui import ui
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..language import get_text
from .common import loading_animation

def render_keywords(db: Session, container: ui.element, panel: ui.tab_panel):
    def refresh_keywords_table():
        db.expire_all()
        keywords_table.update_rows([{key: getattr(kw, key) for key in kw.__table__.columns.keys()} for kw in crud.get_error_keywords(db)])

    async def refresh_keywords_table_async():
        async with loading_animation():
            refresh_keywords_table()
        ui.notify(get_text('keywords_refreshed'), color='positive')

    with container:
        with ui.row().classes('w-full items-center'):
            ui.label(get_text('failure_keywords')).classes('text-h6')
        
        ui.label(get_text('failure_keywords_description')).classes('mb-4')

        async def open_add_dialog():
            db.expire_all()
            add_dialog.open()

        with ui.dialog() as add_dialog, ui.card().classes('w-[95vw] md:w-[60vw] max-w-[800px] min-h-[300px]'):
            ui.label(get_text('add_failure_keyword')).classes('text-h6')
            with ui.column().classes('w-full'):
                kw_input = ui.input(get_text('keyword_case_insensitive')).props('filled').classes('w-full')
                desc_input = ui.input(get_text('description')).props('filled').classes('w-full')
            def handle_add():
                crud.create_error_keyword(db, schemas.ErrorKeywordCreate(keyword=kw_input.value, description=desc_input.value))
                ui.notify(get_text('keyword_added').format(keyword=kw_input.value), color='positive')
                refresh_keywords_table(); add_dialog.close()
            with ui.row():
                ui.button(get_text('add'), on_click=handle_add, color='primary')
                ui.button(get_text('cancel'), on_click=add_dialog.close)

        ui.button(get_text('add_keyword'), on_click=open_add_dialog, color='primary').classes('mb-4')
        
        keywords_table = ui.table(columns=[
            {'name': 'id', 'label': get_text('id'), 'field': 'id', 'sortable': True},
            {'name': 'keyword', 'label': get_text('keyword'), 'field': 'keyword', 'sortable': True},
            {'name': 'description', 'label': get_text('description'), 'field': 'description'},
            {'name': 'is_active', 'label': get_text('active'), 'field': 'is_active'},
            {'name': 'last_triggered', 'label': get_text('last_triggered'), 'field': 'last_triggered', 'sortable': True},
            {'name': 'actions', 'label': get_text('actions'), 'field': 'actions'},
        ], rows=[], row_key='id').classes('w-full')
        refresh_keywords_table()
        
        keywords_table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn @click="$parent.$emit('delete', props.row)" icon="delete" flat dense color="negative" />
            </q-td>
        ''')

        async def open_delete_dialog(row):
            with ui.dialog() as delete_dialog, ui.card().style('width: 60vw; max-width: 800px;'):
                ui.label(get_text('delete_keyword_confirm').format(keyword=row['keyword']))
                with ui.row():
                    def handle_delete():
                        crud.delete_error_keyword(db, row['id']); ui.notify(get_text('keyword_deleted').format(keyword=row['keyword']), color='negative'); refresh_keywords_table(); delete_dialog.close()
                    ui.button(get_text('delete'), on_click=handle_delete, color='negative')
                    ui.button(get_text('cancel'), on_click=delete_dialog.close)
            await delete_dialog

        keywords_table.on('delete', lambda e: open_delete_dialog(e.args))
        panel.on('show', refresh_keywords_table_async)