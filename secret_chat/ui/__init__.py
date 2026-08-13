#/ ============================================================================
#/  ui  — всё, что рисуется
#/  ui  — everything that gets drawn
#/ ============================================================================

from .main_window import MainWindow
from .dialogs import NewChatDialog, JoinDialog, SettingsDialog, IpDialog
from .chat_widget import ChatWidget

#? всё, что нужно снаружи, доступно одной строкой импорта:
#? from secret_chat.ui import MainWindow, NewChatDialog
__all__ = ['MainWindow', 'NewChatDialog', 'JoinDialog', 'SettingsDialog', 'IpDialog', 'ChatWidget']
