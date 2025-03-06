import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from lib.query_executor.base_client import BaseClient
from const.query_execution import QueryExecutionStatus, StatementExecutionStatus

class PythonClient(BaseClient):
    def __init__(self):
        self.output = io.StringIO()
        self.error = io.StringIO()
        self.status = QueryExecutionStatus.INITIALIZED
        self.result = None

    def execute(self, query):
        self.status = QueryExecutionStatus.RUNNING
        try:
            with redirect_stdout(self.output), redirect_stderr(self.error):
                exec(query)
            self.status = QueryExecutionStatus.DONE
        except Exception as e:
            self.error.write(str(e))
            self.status = QueryExecutionStatus.ERROR
        finally:
            self.result = self.output.getvalue()

    def cancel(self):
        # Python execution is synchronous, so we can't cancel it
        return False

    def get_status(self):
        return self.status

    def get_logs(self):
        return self.error.getvalue()

    def get_results(self):
        return self.result

    def close(self):
        self.output.close()
        self.error.close()