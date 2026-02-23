class SettingsError(Exception):
    pass

class DatabaseError(Exception):
    pass

class AuthenticationError(Exception):
    pass

class ValidationError(Exception):
    pass

class AuthorizationError(Exception):
    pass

class AgentNotFoundError(Exception):
    pass

class TaskNotFoundError(Exception):
    pass

class UserNotFoundError(Exception):
    pass