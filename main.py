import flet as ft
import db_manager as db

def main(page: ft.Page):
    # --- Sayfa Ayarları ---
    page.title = "Güvenli Kasa"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    app_state = {
        "encryption_key": None,
        "edit_id": None,   # Şu an düzenlenen kaydın ID'si
        "edit_mode": None  # 'username' veya 'password'
    }
    
    db.create_tables()

    # --- ORTAK STİLLER ---
    input_style = {
        "filled": True,
        "border_color": "blue",
        "bgcolor": "white10",
        "content_padding": 15,
        "border_radius": 10
    }

    # --- UI BİLEŞENLERİ ---
    txt_master_pass = ft.TextField(label="Master Password", password=True, can_reveal_password=True, **input_style)
    txt_confirm_pass = ft.TextField(label="Şifreyi Tekrar Girin", password=True, can_reveal_password=True, visible=False, **input_style)
    lbl_error = ft.Text("", color="red", size=14, weight="bold")
    
    lv_passwords = ft.ListView(expand=True, spacing=10, padding=20)
    
    # Ekleme Penceresi Kutuları
    txt_new_web = ft.TextField(label="Website", icon="public", **input_style)
    txt_new_user = ft.TextField(label="Kullanıcı Adı", icon="person", **input_style)
    txt_new_pass = ft.TextField(label="Şifre", password=True, can_reveal_password=True, icon="lock", **input_style)

    # Düzenleme (Edit) Penceresi Kutusu
    txt_edit_value = ft.TextField(label="Yeni Değer", **input_style)

    # --- FONKSİYONLAR ---

    def refresh_password_list():
        lv_passwords.controls.clear()
        passwords = db.get_passwords_db(app_state["encryption_key"])
        
        if not passwords:
            lv_passwords.controls.append(
                ft.Container(
                    content=ft.Text("Henüz hiç şifre yok. + butonuna basarak ekle!", color="grey", text_align="center"),
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
                                        ft.PopupMenuItem(
                                            text="Şifreyi Kopyala", 
                                            icon="copy", 
                                            on_click=lambda e, pwd=p['pass']: copy_to_clipboard(pwd)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Kullanıcı Adı Değiştir", 
                                            icon="person_outline", 
                                            # Lambda içinde mevcut değeri de gönderiyoruz ki kutuya otomatik yazsın
                                            on_click=lambda e, pid=p['id'], val=p['user']: open_edit_dialog(pid, "username", val)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Şifre Değiştir", 
                                            icon="lock_reset", 
                                            on_click=lambda e, pid=p['id']: open_edit_dialog(pid, "password", "")
                                        ),
                                        ft.PopupMenuItem(
                                            text="Sil", 
                                            icon="delete", 
                                            on_click=lambda e, pid=p['id']: delete_item(pid)
                                        ),
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
        page.snack_bar = ft.SnackBar(ft.Text(f"Şifre panoya kopyalandı!"), open=True)
        page.update()

    def delete_item(id):
        db.delete_password_db(id)
        refresh_password_list()
        page.snack_bar = ft.SnackBar(ft.Text("Kayıt silindi."), open=True)
        page.update()

    # --- DÜZENLEME (EDIT) MANTIĞI ---
    
    dlg_edit = ft.AlertDialog(
        title=ft.Text("Düzenle"),
        content=txt_edit_value,
        actions=[
            ft.TextButton("İptal", on_click=lambda e: page.close(dlg_edit)),
            ft.ElevatedButton("Güncelle", on_click=lambda e: save_edit(), bgcolor="blue", color="white")
        ],
    )

    def open_edit_dialog(id, mode, current_value):
        # Hangi ID'yi ve neyi değiştireceğimizi hafızaya alalım
        app_state["edit_id"] = id
        app_state["edit_mode"] = mode
        
        # Pencereyi duruma göre ayarla
        if mode == "username":
            dlg_edit.title = ft.Text("Kullanıcı Adı Değiştir")
            txt_edit_value.value = current_value # Eski adı kutuya yaz
            txt_edit_value.label = "Yeni Kullanıcı Adı"
            txt_edit_value.password = False
            txt_edit_value.can_reveal_password = False
            txt_edit_value.icon = "person"
        else:
            dlg_edit.title = ft.Text("Şifre Değiştir")
            txt_edit_value.value = "" # Şifre için kutu boş gelsin
            txt_edit_value.label = "Yeni Şifre"
            txt_edit_value.password = True # Yazılanlar gizli olsun
            txt_edit_value.can_reveal_password = True
            txt_edit_value.icon = "lock"
            
        page.open(dlg_edit)
        page.update()

    def save_edit():
        new_val = txt_edit_value.value
        if not new_val:
            return # Boşsa işlem yapma
            
        id = app_state["edit_id"]
        key = app_state["encryption_key"]
        
        if app_state["edit_mode"] == "username":
            db.update_password_entry(id, key, new_username=new_val)
            page.snack_bar = ft.SnackBar(ft.Text("Kullanıcı adı güncellendi!"), open=True)
        else:
            db.update_password_entry(id, key, new_password=new_val)
            page.snack_bar = ft.SnackBar(ft.Text("Şifre güncellendi!"), open=True)
            
        page.close(dlg_edit)
        refresh_password_list()
        page.update()

    # --- EKLEME MANTIĞI ---
    
    dlg_add = ft.AlertDialog(
        modal=True,
        title=ft.Text("Yeni Şifre Ekle"),
        content=ft.Column([
            ft.Container(height=10),
            txt_new_web,
            txt_new_user,
            txt_new_pass
        ], height=280, width=300),
        actions=[
            ft.TextButton("İptal", on_click=lambda e: page.close(dlg_add)),
            ft.ElevatedButton("Kaydet", on_click=lambda e: add_item(), bgcolor="blue", color="white")
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_add_dialog(e):
        page.open(dlg_add)

    def add_item():
        if not (txt_new_web.value and txt_new_user.value and txt_new_pass.value):
            page.snack_bar = ft.SnackBar(ft.Text("Lütfen tüm alanları doldurun!"), open=True)
            page.update()
            return 
        
        db.add_password_db(app_state["encryption_key"], txt_new_web.value, txt_new_user.value, txt_new_pass.value)
        
        txt_new_web.value = ""
        txt_new_user.value = ""
        txt_new_pass.value = ""
        
        page.close(dlg_add)
        refresh_password_list()
        page.snack_bar = ft.SnackBar(ft.Text("Başarıyla eklendi!"), open=True)
        page.update()

    # --- GİRİŞ MANTIĞI ---
    def handle_login(e):
        password = txt_master_pass.value
        lbl_error.value = ""

        if not password: 
            lbl_error.value = "Şifre boş olamaz."
            page.update()
            return

        if not db.check_user_exists(): 
            confirm = txt_confirm_pass.value
            if password != confirm:
                lbl_error.value = "Şifreler uyuşmuyor."
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
                lbl_error.value = "Hatalı Şifre!"
                txt_master_pass.value = ""
                page.update()

    def show_dashboard():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        
        page.floating_action_button = ft.FloatingActionButton(
            icon="add", 
            bgcolor="blue", 
            on_click=open_add_dialog
        )
        
        page.add(
            ft.Container(
                padding=20,
                content=ft.Row([
                    ft.Text("Kasam", size=28, weight="bold", color="blue"),
                    ft.Icon("security", color="blue", size=30)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ),
            ft.Divider(height=1, color="white10"),
            lv_passwords
        )
        refresh_password_list()

    def show_login_screen():
        page.clean()
        page.floating_action_button = None
        
        is_setup = not db.check_user_exists()
        txt_confirm_pass.visible = is_setup
        
        btn_text = "Kurulumu Tamamla" if is_setup else "Giriş Yap"
        header_text = "Hoş Geldiniz" if not is_setup else "İlk Kurulum"
        
        page.add(
            ft.Container(
                padding=30,
                border_radius=10,
                content=ft.Column([
                    ft.Icon("lock_outline", size=80, color="blue"),
                    ft.Text(header_text, size=30, weight="bold"),
                    ft.Divider(height=20, color="transparent"),
                    txt_master_pass,
                    txt_confirm_pass,
                    ft.Divider(height=10, color="transparent"),
                    lbl_error,
                    ft.ElevatedButton(
                        text=btn_text, 
                        on_click=handle_login, 
                        width=200, 
                        style=ft.ButtonStyle(
                            padding=15, 
                            bgcolor="blue", 
                            color="white"
                        )
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    show_login_screen()

ft.app(target=main)