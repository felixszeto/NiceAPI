from nicegui import ui, app
import asyncio
import os
from .common import set_language, get_text

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

def login_page():
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