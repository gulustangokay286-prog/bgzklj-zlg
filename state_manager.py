from PySide6.QtCore import QObject, Signal

class GlobalState(QObject):
    # Data changed signals
    teachers_changed = Signal()
    classes_changed = Signal()
    subjects_changed = Signal()
    rooms_changed = Signal()
    lessons_changed = Signal()
    placements_changed = Signal()
    
    # Global settings changed
    settings_changed = Signal()

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GlobalState()
        return cls._instance

# Singleton instance for easy import
store = GlobalState.get_instance()
