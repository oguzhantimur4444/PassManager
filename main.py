import flet as ft
import db_manager as db
import json
import os

def main(page: ft.Page):
    # --- Sayfa Ayarları ---
    page.title = "Secure Vault"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    # --- DİNAMİK DİL YÜKLEME ---
    loaded_locales = {} # Tüm dilleri buraya yükleyeceğiz
    
    def load_languages():
        """locales klasöründeki tüm .json dosyalarını okur"""
        if not os.path.exists("locales"):
            os.makedirs("locales")
            
        for filename in os.listdir("locales"):
            if filename.endswith(".json"):
                lang_code = filename.split(".")[0] # tr.json -> tr
                try:
                    with open(f"locales/{filename}", "r", encoding="utf-8") as f:
                        loaded_locales[lang_code] = json.load(f)
                        print(f"Dil yüklendi: {lang_code}")
                except Exception as e:
                    print(f"Hata: {filename} yüklenemedi. {e}")

    # Başlangıçta dilleri yükle
    load_languages()
    
    # Varsayılan dil ayarı (Eğer tr yoksa ilk bulduğunu seç)
    default_lang = "tr" if "tr" in loaded_locales else (list(loaded_locales.keys())[0] if loaded_locales else "en")

    app_state = {
        "encryption_key": None,
        "edit_id": None,
        "edit_mode": None,
        "lang": default_lang
    }
    
    db.create_tables()

    # --- ÇEVİRİ FONKSİYONU ---
    def tr(key):
        current_lang_data = loaded_locales.get(app_state["lang"], {})
        return current_lang_data.get(key, key) # Bulamazsa anahtarın kendisini döndür

    def change_language(e):
        app_state["lang"] = e.control.value
        if app_state["encryption_key"]:
            show_dashboard()
        else:
            show_login_screen()

    # --- STİLLER ---
    input_style = {
        "filled": True,
        "border_color": "blue",
        "bgcolor": "white10",
        "content_padding": 15,
        "border_radius": 10
    }

    # --- UI BİLEŞENLERİ ---
    txt_master_pass = ft.TextField(password=True, can_reveal_password=True, **input_style)
    txt_confirm_pass = ft.TextField(password=True, can_reveal_password=True, visible=False, **input_style)
    lbl_error = ft.Text("", color="red", size=14, weight="bold")
    
    lv_passwords = ft.ListView(expand=True, spacing=10, padding=20)
    
    txt_new_web = ft.TextField(icon="public", **input_style)
    txt_new_user = ft.TextField(icon="person", **input_style)
    txt_new_pass = ft.TextField(password=True, can_reveal_password=True, icon="lock", **input_style)

    txt_edit_value = ft.TextField(**input_style)

    # --- DİNAMİK DROPDOWN ---
    # Klasörden hangi dilleri bulduysak onları listeye ekliyoruz
    lang_options = []
    for code, data in loaded_locales.items():
        # JSON içindeki "name" alanını kullanıyoruz (Örn: "Türkçe")
        display_name = data.get("name", code.upper())
        lang_options.append(ft.dropdown.Option(code, display_name))

    dd_lang = ft.Dropdown(
        width=100,
        value=app_state["lang"],
        options=lang_options, # Dinamik liste
        on_change=change_language,
        content_padding=5,
        text_size=12,
        border_radius=10,
        filled=True,
        bgcolor="white5"
    )

    # --- LİSTELEME ---
    def refresh_password_list():
        lv_passwords.controls.clear()
        passwords = db.get_passwords_db(app_state["encryption_key"])
        
        if not passwords:
            lv_passwords.controls.append(
                ft.Container(
                    content=ft.Text(tr("no_passwords"), color="grey", text_align="center"),
                    alignment=ft.alignment.center,
                    padding=50
                )
            )
        
        for p in passwords:
            lv_passwords.controls.append(
                ft.Card(
                    elevation=5,
                    color="grey900",
                    content=ft.Container(
                        padding=10,
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon("vpn_key", color="blue", size=30),
                                title=ft.Text(p['web'], weight="bold", size=16),
                                subtitle=ft.Text(p['user'], opacity=0.7),
                                trailing=ft.PopupMenuButton(
                                    icon="more_vert",
                                    items=[
                                        ft.PopupMenuItem(text=tr("menu_copy"), icon="copy", on_click=lambda e, pwd=p['pass']: copy_to_clipboard(pwd)),
                                        ft.PopupMenuItem(
                                            text=tr("menu_edit_user"), 
                                            icon="person_outline", 
                                            on_click=lambda e, pid=p['id'], val=p['user']: open_edit_dialog(pid, "username", val)
                                        ),
                                        ft.PopupMenuItem(text=tr("menu_edit_pass"), icon="lock_reset", on_click=lambda e, pid=p['id']: open_edit_dialog(pid, "password", "")),
                                        ft.PopupMenuItem(text=tr("menu_delete"), icon="delete", on_click=lambda e, pid=p['id']: delete_item(pid)),
                                    ]
                                )
                            )
                        ])
                    )
                )
            )
        page.update()

    def copy_to_clipboard(val):
        page.set_clipboard(val)
        page.snack_bar = ft.SnackBar(ft.Text(tr("copied_msg")), open=True)
        page.update()

    def delete_item(id):
        db.delete_password_db(id)
        refresh_password_list()
        page.snack_bar = ft.SnackBar(ft.Text(tr("deleted_msg")), open=True)
        page.update()

    # --- DÜZENLEME ---
    dlg_edit = ft.AlertDialog(content=txt_edit_value)

    def open_edit_dialog(id, mode, current_value):
        app_state["edit_id"] = id
        app_state["edit_mode"] = mode
        
        dlg_edit.title = ft.Text(tr("change_user") if mode == "username" else tr("change_pass"))
        dlg_edit.actions = [
            ft.TextButton(tr("cancel"), on_click=lambda e: page.close(dlg_edit)),
            ft.ElevatedButton(tr("update"), on_click=lambda e: save_edit(), bgcolor="blue", color="white")
        ]
        
        if mode == "username":
            txt_edit_value.value = current_value
            txt_edit_value.label = tr("username")
            txt_edit_value.password = False
            txt_edit_value.can_reveal_password = False
            txt_edit_value.icon = "person"
        else:
            txt_edit_value.value = ""
            txt_edit_value.label = tr("password")
            txt_edit_value.password = True
            txt_edit_value.can_reveal_password = True
            txt_edit_value.icon = "lock"
            
        page.open(dlg_edit)
        page.update()

    def save_edit():
        new_val = txt_edit_value.value
        if not new_val: return
        
        id = app_state["edit_id"]
        key = app_state["encryption_key"]
        
        if app_state["edit_mode"] == "username":
            db.update_password_entry(id, key, new_username=new_val)
            page.snack_bar = ft.SnackBar(ft.Text(tr("user_updated")), open=True)
        else:
            db.update_password_entry(id, key, new_password=new_val)
            page.snack_bar = ft.SnackBar(ft.Text(tr("pass_updated")), open=True)
            
        page.close(dlg_edit)
        refresh_password_list()
        page.update()

    # --- EKLEME ---
    dlg_add = ft.AlertDialog(modal=True)

    def open_add_dialog(e):
        txt_new_web.label = tr("website")
        txt_new_user.label = tr("username")
        txt_new_pass.label = tr("password")
        
        dlg_add.title = ft.Text(tr("add_title"))
        dlg_add.content = ft.Column([ft.Container(height=10), txt_new_web, txt_new_user, txt_new_pass], height=280, width=300)
        dlg_add.actions = [
            ft.TextButton(tr("cancel"), on_click=lambda e: page.close(dlg_add)),
            ft.ElevatedButton(tr("save"), on_click=lambda e: add_item(), bgcolor="blue", color="white")
        ]
        page.open(dlg_add)
        page.update()

    def add_item():
        if not (txt_new_web.value and txt_new_user.value and txt_new_pass.value):
            page.snack_bar = ft.SnackBar(ft.Text(tr("fill_all")), open=True)
            page.update()
            return 
        
        db.add_password_db(app_state["encryption_key"], txt_new_web.value, txt_new_user.value, txt_new_pass.value)
        
        txt_new_web.value = ""
        txt_new_user.value = ""
        txt_new_pass.value = ""
        
        page.close(dlg_add)
        refresh_password_list()
        page.snack_bar = ft.SnackBar(ft.Text(tr("added_msg")), open=True)
        page.update()

    # --- LOGIN ---
    def handle_login(e):
        password = txt_master_pass.value
        lbl_error.value = ""

        if not password: 
            lbl_error.value = tr("pass_empty")
            page.update()
            return

        if not db.check_user_exists(): 
            confirm = txt_confirm_pass.value
            if password != confirm:
                lbl_error.value = tr("pass_mismatch")
                page.update()
                return
            key = db.create_master_user(password)
            app_state["encryption_key"] = key
            show_dashboard()

        else: 
            key = db.verify_login(password)
            if key:
                app_state["encryption_key"] = key
                show_dashboard()
            else:
                lbl_error.value = tr("wrong_pass")
                txt_master_pass.value = ""
                page.update()

    def show_dashboard():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.floating_action_button = ft.FloatingActionButton(icon="add", bgcolor="blue", on_click=open_add_dialog)
        
        dd_lang.value = app_state["lang"]

        header = ft.Row([
            ft.Row([
                ft.Text(tr("my_vault"), size=28, weight="bold", color="blue"),
                ft.Icon("security", color="blue", size=30)
            ]),
            dd_lang
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        page.add(
            ft.Container(padding=20, content=header),
            ft.Divider(height=1, color="white10"),
            lv_passwords
        )
        refresh_password_list()

    def show_login_screen():
        page.clean()
        page.floating_action_button = None
        
        is_setup = not db.check_user_exists()
        txt_confirm_pass.visible = is_setup
        
        btn_text = tr("setup_btn") if is_setup else tr("login_btn")
        header_text = tr("welcome") if not is_setup else tr("first_setup")
        sub_text = tr("enter_pass") if not is_setup else tr("create_pass")
        txt_master_pass.label = tr("master_pass")
        txt_confirm_pass.label = tr("confirm_pass")

        dd_lang.value = app_state["lang"]
        
        page.add(
            ft.Container(alignment=ft.alignment.top_right, padding=10, content=dd_lang),
            ft.Container(
                padding=30,
                border_radius=10,
                content=ft.Column([
                    ft.Icon("lock_outline", size=80, color="blue"),
                    ft.Text(header_text, size=30, weight="bold"),
                    ft.Text(sub_text, size=14, color="grey"),
                    ft.Divider(height=20, color="transparent"),
                    txt_master_pass,
                    txt_confirm_pass,
                    ft.Divider(height=10, color="transparent"),
                    lbl_error,
                    ft.ElevatedButton(
                        text=btn_text, 
                        on_click=handle_login, 
                        width=200, 
                        style=ft.ButtonStyle(padding=15, bgcolor="blue", color="white")
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    show_login_screen()

ft.app(target=main)