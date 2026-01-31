from nicegui import ui
from sqlalchemy.orm import Session
from .. import crud
from ..language import get_text

def render_settings(db: Session, container: ui.element, panel: ui.tab_panel):
    def build_settings():
        container.clear()
        with container:
            with ui.row().classes('w-full items-center'):
                ui.label(get_text('settings')).classes('text-h6')
            
            with ui.card().classes('w-full mt-4'):
                ui.label(get_text('failover_settings')).classes('text-lg font-medium')
                ui.label(get_text('failover_description')).classes('text-sm text-gray-500 mb-4')
                
                db.expire_all()
                count_setting = crud.get_setting(db, 'failover_threshold_count')
                period_setting = crud.get_setting(db, 'failover_threshold_period_minutes')
                
                count_input = ui.number(
                    label=get_text('failure_count_threshold'),
                    value=int(count_setting.value) if count_setting else 2,
                    min=1
                ).props('filled')
                
                period_input = ui.number(
                    label=get_text('failure_period_minutes'),
                    value=int(period_setting.value) if period_setting else 5,
                    min=1
                ).props('filled')

                def save_settings():
                    try:
                        crud.update_setting(db, 'failover_threshold_count', str(int(count_input.value)))
                        crud.update_setting(db, 'failover_threshold_period_minutes', str(int(period_input.value)))
                        ui.notify(get_text('settings_saved'), color='positive')
                    except Exception as e:
                        ui.notify(f"Error saving settings: {e}", color='negative')

                ui.button(get_text('save'), on_click=save_settings, color='primary').classes('mt-4')
    
    panel.on('show', build_settings)
    build_settings()