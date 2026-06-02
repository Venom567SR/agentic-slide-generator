"""
Utility modules for the application.
"""


class AppError(Exception):
    """
    Custom application error that carries context about which component failed.
    Used for cleaner error handling and logging throughout the pipeline.
    """

    def __init__(self, message: str, component: str = None):
        """
        Args:
            message: Human-readable error message
            component: Name of the component that raised the error (e.g., "notion_reader", "ppt_generator")
        """
        self.message = message
        self.component = component
        super().__init__(self.message)

    def __str__(self):
        if self.component:
            return f"[{self.component}] {self.message}"
        return self.message
