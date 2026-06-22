import json
import logging


class JsonLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = {
                "timestamp": self.formatter.formatTime(record) if self.formatter else record.created,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            if hasattr(record, "correlation_id"):
                log_entry["correlation_id"] = record.correlation_id
            if record.exc_info and record.exc_info[0]:
                log_entry["exception"] = self.formatter.formatException(record.exc_info) if self.formatter else str(record.exc_info)
            print(json.dumps(log_entry))
        except Exception:
            self.handleError(record)
