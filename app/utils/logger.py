import sys
from datetime import datetime
from typing import Any, Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"

class Colors:
    """ANSI color codes for console output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

class BiteWiseLogger:
    """Robust logging utility for BiteWise backend with colorized output and consistent formatting"""
    
    def __init__(self, service_name: str = "BITEWISE", enable_colors: bool = True):
        self.service_name = service_name.upper()
        self.enable_colors = enable_colors
        
        # Color mapping for different log levels
        self.level_colors = {
            LogLevel.DEBUG: Colors.BRIGHT_CYAN,
            LogLevel.INFO: Colors.BRIGHT_BLUE,
            LogLevel.WARNING: Colors.BRIGHT_YELLOW,
            LogLevel.ERROR: Colors.BRIGHT_RED,
            LogLevel.SUCCESS: Colors.BRIGHT_GREEN,
        }
        
        # Emoji mapping for different log levels
        self.level_emojis = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.SUCCESS: "✅",
        }
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if not self.enable_colors:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def _format_message(self, level: LogLevel, message: str, context: Optional[str] = None) -> str:
        """Format the log message with consistent structure"""
        timestamp = self._get_timestamp()
        emoji = self.level_emojis.get(level, "")
        level_color = self.level_colors.get(level, Colors.WHITE)
        
        # Format: [TIMESTAMP] 🔍 [SERVICE/CONTEXT] [DEBUG] Message
        level_text = self._colorize(f"[{level.value}]", level_color + Colors.BOLD)
        service_context = f"{self.service_name}"
        
        if context:
            service_context += f"/{context.upper()}"
        
        service_text = self._colorize(f"[{service_context}]", Colors.BRIGHT_BLACK)
        timestamp_text = self._colorize(f"[{timestamp}]", Colors.DIM)
        
        return f"{timestamp_text} {emoji} {service_text} {level_text} {message}"
    
    def _log(self, level: LogLevel, message: str, context: Optional[str] = None, **kwargs):
        """Internal logging method"""
        formatted_message = self._format_message(level, message, context)
        
        # Add any additional key-value pairs
        if kwargs:
            extras = []
            for key, value in kwargs.items():
                if isinstance(value, (dict, list)):
                    import json
                    value_str = json.dumps(value, indent=None, separators=(',', ':'))[:100]
                    if len(str(value)) > 100:
                        value_str += "..."
                else:
                    value_str = str(value)
                extras.append(f"{key}={value_str}")
            
            if extras:
                extra_text = self._colorize(f" | {', '.join(extras)}", Colors.DIM)
                formatted_message += extra_text
        
        print(formatted_message, file=sys.stdout)
        sys.stdout.flush()
    
    # Public logging methods
    def debug(self, message: str, context: Optional[str] = None, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, context, **kwargs)
    
    def info(self, message: str, context: Optional[str] = None, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[str] = None, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: Optional[str] = None, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, message, context, **kwargs)
    
    def success(self, message: str, context: Optional[str] = None, **kwargs):
        """Log success message"""
        self._log(LogLevel.SUCCESS, message, context, **kwargs)
    
    # Visual separator methods for better readability
    def separator(self, char: str = "─", length: int = 60, context: Optional[str] = None):
        """Print a visual separator line"""
        separator_line = char * length
        colored_line = self._colorize(separator_line, Colors.DIM)
        
        timestamp = self._get_timestamp()
        timestamp_text = self._colorize(f"[{timestamp}]", Colors.DIM)
        
        service_context = f"{self.service_name}"
        if context:
            service_context += f"/{context.upper()}"
        service_text = self._colorize(f"[{service_context}]", Colors.BRIGHT_BLACK)
        
        print(f"{timestamp_text} {service_text} {colored_line}", file=sys.stdout)
        sys.stdout.flush()
    
    def banner(self, message: str, context: Optional[str] = None, char: str = "═", width: int = 60):
        """Print a banner with message"""
        # Calculate padding
        content = f" {message} "
        content_length = len(content)
        if content_length >= width - 4:
            # If message is too long, just use it as is
            banner_content = content
        else:
            # Center the message
            padding = (width - content_length) // 2
            banner_content = char * padding + content + char * (width - content_length - padding)
        
        colored_banner = self._colorize(banner_content, Colors.BRIGHT_CYAN + Colors.BOLD)
        
        timestamp = self._get_timestamp()
        timestamp_text = self._colorize(f"[{timestamp}]", Colors.DIM)
        
        service_context = f"{self.service_name}"
        if context:
            service_context += f"/{context.upper()}"
        service_text = self._colorize(f"[{service_context}]", Colors.BRIGHT_BLACK)
        
        print(f"{timestamp_text} {service_text} {colored_banner}", file=sys.stdout)
        sys.stdout.flush()
    
    def section_start(self, section_name: str, context: Optional[str] = None):
        """Start a new section with a clear banner"""
        self.banner(f"🚀 {section_name.upper()} STARTED", context, "═", 50)
    
    def section_end(self, section_name: str, context: Optional[str] = None, success: bool = True):
        """End a section with a clear banner"""
        status_emoji = "✅" if success else "❌"
        status_text = "COMPLETED" if success else "FAILED"
        self.banner(f"{status_emoji} {section_name.upper()} {status_text}", context, "═", 50)
        self.separator("─", 60, context)
        print()  # Add extra spacing after section end
        sys.stdout.flush()
    
    def newline(self):
        """Add a blank line for spacing"""
        print()
        sys.stdout.flush()


# Global logger instances for different services
agent_logger = BiteWiseLogger("AGENT")
intake_logger = BiteWiseLogger("INTAKE")
dish_logger = BiteWiseLogger("DISH")
auth_logger = BiteWiseLogger("AUTH")
db_logger = BiteWiseLogger("DATABASE")
api_logger = BiteWiseLogger("API")

# Convenience function for quick logging
def get_logger(service_name: str) -> BiteWiseLogger:
    """Get a logger instance for a specific service"""
    return BiteWiseLogger(service_name) 