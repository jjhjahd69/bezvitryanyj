class LogicError(Exception):
    """Базовий виняток для всіх логічних помилок у боті."""
    def __init__(self, message="Сталася помилка логіки."):
        self.message = message
        super().__init__(self.message)

class GameNotFoundError(LogicError):
    """Виняток, коли гра не знайдена."""
    def __init__(self, message="Вказаної вами гри не існує."): # <--- Тут задаємо дефолтний текст
        super().__init__(message) # <--- Передаємо його в __init__ батьківського класу BusinessLogicError
        # Якщо при raise GameNotFoundError(...) передати свій текст, він потрапить в параметр message тут.
        # Якщо не передати, параметр message буде мати дефолтне значення "Вказаної вами гри не існує.".

class NotEnoughtPermissions(LogicError):
    """Виняток, коли недостатньо прав для виконання команди."""
    def __init__(self, message="Недостатньо прав для виконання цієї команди."): # <--- Ще один дефолтний текст
        super().__init__(message)

class InvalidGameStateError(LogicError):
    """Виняток, коли стан гри не дозволяє виконати дію."""
    def __init__(self, message="Ви не можете виконати цю дію для гри в поточному стані."): # <--- Ще один дефолтний текст
        super().__init__(message)

class CannotDeleteGame(LogicError):
    """Виняток, коли стан гри не дозволяє виконати дію."""
    def __init__(self, message="Ви не можете видалити гру, що йде або закінчена"): # <--- Ще один дефолтний текст
        super().__init__(message)

class CannotToRespondToMySelfError(LogicError):
    """Виняток, коли стан гри не дозволяє виконати дію."""
    def __init__(self, message="Ви не можете залишити відгук на самого себе."): # <--- Ще один дефолтний текст
        super().__init__(message)