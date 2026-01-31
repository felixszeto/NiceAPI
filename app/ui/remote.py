from nicegui import ui, app
from sqlalchemy.orm import Session
from fastapi import Request, Depends
from .. import crud, models
from ..language import get_text
from ..database import get_db

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
        if not url_key: app.storage.user.pop('remote_api_key', None)
        with ui.column().classes('w-full h-screen flex-center'):
            ui.label("Invalid or Inactive API Key").classes('text-h4 text-red')
        return

    if url_key: app.storage.user['remote_api_key'] = url_key

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
            cards.forEach(c => {
                const cRect = c.getBoundingClientRect();
                if (c !== card && cRect.top < cardRect.top) {
                    c.style.transform = `translateY(${cardRect.height + 8}px)`;
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
                    
                    associations = db.query(models.provider_group_association).filter_by(group_id=group.id).all()
                    associations.sort(key=lambda x: x.priority)
                    if not associations:
                        ui.label("No models in this group.").classes('text-italic text-grey-6')
                        continue

                    item_col = ui.column().classes('w-full gap-2')
                    container_id = f"group-list-{group.id}"
                    item_col.props(f'id="{container_id}"')
                    with item_col:
                        for i, assoc in enumerate(associations):
                            provider = db.query(models.ApiProvider).filter_by(id=assoc.provider_id).first()
                            if not provider: continue
                            card_id = f"card-{group.id}-{provider.id}"
                            card = ui.card().classes('w-full p-0 mb-1 shadow-sm border overflow-hidden model-card cursor-pointer')
                            card.props(f'id="{card_id}"')
                            async def handle_click(g_id=group.id, p_id=provider.id, assocs=associations, c_id=card_id, ct_id=container_id, idx=i):
                                if idx == 0: return
                                await ui.run_javascript(f'animateToTop("{c_id}", "{ct_id}")', timeout=1.0)
                                await move_to_top(g_id, p_id, assocs)
                            card.on('click', handle_click)
                            with card:
                                with ui.row().classes('w-full items-center no-wrap'):
                                    with ui.element('div').classes('p-4 bg-gray-50 border-r flex flex-center h-full w-14'):
                                        ui.label(str(i + 1)).classes('text-h6 text-grey-6 font-bold seq-label')
                                    with ui.column().classes('gap-0 flex-grow p-3'):
                                        ui.label(provider.model).classes('text-subtitle1 font-medium')
                                        ui.label(provider.name).classes('text-caption text-grey-5')
                                    with ui.row().classes('items-center p-3 w-16 justify-center'):
                                        if i == 0: ui.icon('check_circle', color='positive', size='md')
                                        else: ui.element('div').classes('w-6 h-6')

                    async def move_to_top(group_id, provider_id, current_associations):
                        pids = [a.provider_id for a in current_associations]
                        if provider_id in pids:
                            pids.remove(provider_id); pids.insert(0, provider_id)
                            for idx, pid in enumerate(pids):
                                crud.add_provider_to_group(db, provider_id=pid, group_id=group_id, priority=idx+1)
                            ui.notify(get_text('save_success'), color='positive')
                            await refresh_remote_view()

    await refresh_remote_view()