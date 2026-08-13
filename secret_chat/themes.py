#/ ============================================================================
#/  themes.py — 14 тем и сборка QSS
#/  themes.py — 14 themes and the QSS builder
#/ ============================================================================
#/  палитра любой темы: 14 ключей. добавить тему = добавить пару строк внизу.
#/  any theme palette: 14 keys. adding a theme = adding a couple of lines below.
#/  ключи (keys): bg panel header input me them text dim accent border hover
#/                danger me_fg accent_fg
#/   me/accent     — свой пузырь и акцентные кнопки  | own bubble and accent buttons
#/   me_fg/        — цвет текста поверх me и accent (на светлых акцентах — тёмный)
#/   accent_fg       text color on me and accent (dark on bright accents)

#/ ----------------------------------------------------------------------------
#/  палитры  |  palettes
#/ ----------------------------------------------------------------------------
PALETTES = {

'black':  dict(bg='#0e0e0f', panel='#17181a', header='#1d1e21', input='#141416', me='#7d6bf5', them='#26282c', text='#e8eaed', dim='#8a8f98', accent='#7d6bf5', border='#2a2c31', hover='#222429', danger='#e5534b', me_fg='#ffffff', accent_fg='#ffffff'),
'white':  dict(bg='#f2f3f5', panel='#ffffff', header='#f7f7f8', input='#ffffff', me='#7d6bf5', them='#e4e6ea', text='#1c1e21', dim='#7a7f88', accent='#7d6bf5', border='#d9dce1', hover='#e9ebef', danger='#d93a34', me_fg='#ffffff', accent_fg='#ffffff'),
'darkblue': dict(bg='#0d1b2a', panel='#152a40', header='#1b3350', input='#101e30', me='#2f6fed', them='#1c3a5e', text='#e6eef7', dim='#7d96ad', accent='#3f8cff', border='#23415f', hover='#1a3048', danger='#ff5d5d', me_fg='#ffffff', accent_fg='#ffffff'),
'green':  dict(bg='#0e1f16', panel='#16301f', header='#1c3d28', input='#11241a', me='#2fa35c', them='#24402f', text='#e2f2e8', dim='#7fa58d', accent='#34c06b', border='#2b4a35', hover='#1a3624', danger='#ff6b5e', me_fg='#ffffff', accent_fg='#0a2416'),
'purple': dict(bg='#160f24', panel='#221740', header='#2b1d4f', input='#1a1130', me='#7c4dff', them='#2e2058', text='#ece7fb', dim='#9a8cc0', accent='#9b6bff', border='#3a2c68', hover='#251a47', danger='#ff5f7a', me_fg='#ffffff', accent_fg='#ffffff'),
'red':    dict(bg='#220f0f', panel='#381616', header='#461c1c', input='#2a1212', me='#d93a34', them='#4a2020', text='#f7e6e6', dim='#b08a8a', accent='#ff5b52', border='#582424', hover='#3b1a1a', danger='#ff6b5e', me_fg='#ffffff', accent_fg='#ffffff'),
'orange': dict(bg='#201608', panel='#38250c', header='#452f10', input='#2a1c0a', me='#e8842e', them='#4a3416', text='#f7eee1', dim='#b09a74', accent='#ff9a3d', border='#5a401a', hover='#352409', danger='#ff6b5e', me_fg='#ffffff', accent_fg='#2a1505'),
'pink':   dict(bg='#211019', panel='#381b2c', header='#452237', input='#2b1521', me='#e0559a', them='#482a3b', text='#f8e9f1', dim='#b28aa0', accent='#ff6cb4', border='#593147', hover='#361a28', danger='#ff5f7a', me_fg='#ffffff', accent_fg='#3a0a24'),
'gray':   dict(bg='#161618', panel='#222226', header='#2a2a2f', input='#1c1c1f', me='#5c6470', them='#313137', text='#e9eaec', dim='#90949c', accent='#7d8590', border='#38383e', hover='#26262a', danger='#e5534b', me_fg='#ffffff', accent_fg='#ffffff'),
'teal':   dict(bg='#0c1f1f', panel='#143231', header='#1a3d3c', input='#102726', me='#17a8a0', them='#224543', text='#e0f2f1', dim='#7ba5a2', accent='#24c4ba', border='#28514f', hover='#123030', danger='#ff6b5e', me_fg='#ffffff', accent_fg='#05312d'),
'amber':  dict(bg='#1e1704', panel='#33290b', header='#403412', input='#271f08', me='#e0a71a', them='#4a3d16', text='#f8f0dc', dim='#b3a06b', accent='#ffc23d', border='#5a4a1c', hover='#31280a', danger='#ff6b5e', me_fg='#241a04', accent_fg='#2b1e04'),
'forest': dict(bg='#101810', panel='#1b2a1b', header='#223722', input='#152315', me='#4f8f3f', them='#2c442c', text='#e8f0e4', dim='#8aa580', accent='#63b84f', border='#335033', hover='#1d301d', danger='#ff6b5e', me_fg='#ffffff', accent_fg='#0e2410'),
'hacker': dict(bg='#000000', panel='#050d06', header='#081408', input='#020602', me='#00e05a', them='#0a1f0e', text='#3dff70', dim='#1f7a3d', accent='#00c853', border='#0f2e17', hover='#061006', danger='#ff4d4d', me_fg='#001a08', accent_fg='#001a08'),
'ultrablack': dict(bg='#000000', panel='#050505', header='#0a0a0a', input='#020202', me='#3a4149', them='#121212', text='#eaeaea', dim='#616161', accent='#9aa4b2', border='#1c1c1c', hover='#0d0d0d', danger='#e5534b', me_fg='#ffffff', accent_fg='#050505'),

}

#/ порядок тем в списке выбора  |  the order of themes in the picker
ORDER = ['black', 'white', 'darkblue', 'green', 'purple', 'red',
         'orange', 'pink', 'gray', 'teal', 'amber', 'forest',
         'hacker', 'ultrablack']


#/ ----------------------------------------------------------------------------
#/  сборка стиля  |  stylesheet builder
#/ ----------------------------------------------------------------------------
def build_qss(theme_id):
  #* не знаем тему — берём чёрную                 |  unknown theme — fall back to black
  c = PALETTES.get(theme_id, PALETTES['black'])
  qss = f"""
    QMainWindow, QWidget {{ background-color: {c['bg']}; }}
    QDialog {{ background-color: {c['bg']}; }}

    QLabel {{ color: {c['text']}; font-size: 13px; }}
    QLabel#dim {{ color: {c['dim']}; }}
    QLabel#title {{ font-size: 15px; font-weight: 600; }}
    QLabel#hint {{ color: {c['dim']}; font-size: 12px; }}

    QPushButton {{
      background-color: {c['panel']}; color: {c['text']};
      border: 1px solid {c['border']}; border-radius: 8px; padding: 6px 12px; font-size: 13px;
    }}
    QPushButton:hover {{ background-color: {c['hover']}; }}
    QPushButton:pressed {{ background-color: {c['border']}; }}
    QPushButton#accent {{ background-color: {c['accent']}; color: {c['accent_fg']}; border: none; font-weight: 600; }}
    QPushButton#accent:hover {{ background-color: {c['me']}; color: {c['me_fg']}; }}
    QPushButton#danger {{ color: {c['danger']}; }}
    QPushButton:disabled {{ color: {c['dim']}; background-color: {c['panel']}; }}

    QLineEdit, QTextEdit, QSpinBox, QComboBox {{
      background-color: {c['input']}; color: {c['text']};
      border: 1px solid {c['border']}; border-radius: 10px; padding: 7px 10px; font-size: 13px;
      selection-background-color: {c['accent']};
    }}
    QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {c['accent']}; }}

    QListWidget {{
      background-color: {c['panel']}; color: {c['text']}; border: none;
      font-size: 13px; outline: none;
    }}
    QListWidget::item {{ padding: 8px 10px; border-radius: 6px; margin: 1px 6px; }}
    QListWidget::item:hover {{ background-color: {c['hover']}; }}
    QListWidget::item:selected {{ background-color: {c['accent']}; color: {c['accent_fg']}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    QFrame#att_row, QFrame#file_card {{ background-color: {c['input']}; border: 1px solid {c['border']}; border-radius: 8px; }}

    QPushButton#attach_btn {{
      background-color: {c['input']}; color: {c['accent']}; border: 1px solid {c['border']};
      border-radius: 19px; font-size: 17px; padding: 0; margin: 0; font-weight: 600;
    }}
    QPushButton#attach_btn:hover {{ background-color: {c['hover']}; }}

    QPushButton#send_btn {{
      background-color: {c['accent']}; color: {c['accent_fg']}; border: none;
      border-radius: 19px; font-size: 17px; padding: 0; font-weight: 600;
    }}
    QPushButton#send_btn:hover {{ background-color: {c['me']}; color: {c['me_fg']}; }}
    QPushButton#send_btn:pressed {{ background-color: {c['accent']}; }}
    QPushButton#send_btn:disabled {{ background-color: {c['border']}; color: {c['dim']}; }}

    QFrame#bubble_me {{
      background-color: {c['me']}; border-radius: 12px;
      border-bottom-right-radius: 3px; color: {c['me_fg']};
    }}
    QFrame#bubble_them {{
      background-color: {c['them']}; border-radius: 12px;
      border-bottom-left-radius: 3px; color: {c['text']};
    }}
    QFrame#bubble_me QLabel {{ color: {c['me_fg']}; }}
    QFrame#bubble_them QLabel {{ color: {c['text']}; }}

    QMenu {{ background-color: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; }}
    QMenu::item:selected {{ background-color: {c['accent']}; color: {c['accent_fg']}; }}

    QToolTip {{ background-color: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; }}
  """
  return qss
