from nicegui import ui, app
import asyncio
from contextlib import asynccontextmanager
from ..language import get_text

def apply_styles():
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

def set_ui_colors():
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

def logout():
    app.storage.user['authenticated'] = False
    ui.navigate.reload()