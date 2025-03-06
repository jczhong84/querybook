import sys
from datetime import timedelta

from celery import Celery
from flask import Flask, Blueprint, json as flask_json, has_request_context
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_restx import Api, Resource, Namespace

from const.path import BUILD_PATH, STATIC_PATH, WEBAPP_DIR_PATH
from env import QuerybookSettings
from lib.utils.json import JSONEncoder

# Import all datasources
from datasources import (
    admin, admin_audit_log, board, comment, dag_exporter, data_element,
    datadoc, event_log, github, impression, metastore, query_engine,
    query_execution, query_review, query_snippet, query_transform,
    schedule, search, survey, table_upload, tag, user, utils
)

# Import the register_routes function from admin
from datasources.admin import register_routes as register_admin_routes

def validate_db():
    # We need to make sure db connection is valid
    # before proceeding to other things such as
    # celery or flask server
    if not hasattr(sys, "_called_from_test"):
        from app.db import get_db_engine

        try:
            engine = get_db_engine()
            connection = engine.connect()
            connection.close()
        except Exception:
            raise Exception(
                f"Invalid Database connection string {QuerybookSettings.DATABASE_CONN}"
            )

def make_flask_app():
    app = Flask(__name__, static_folder=STATIC_PATH)
    app.json_encoder = JSONEncoder
    app.secret_key = QuerybookSettings.FLASK_SECRET_KEY

    if QuerybookSettings.PRODUCTION:
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
        )

    if QuerybookSettings.LOGS_OUT_AFTER > 0:
        app.permanent_session_lifetime = timedelta(
            seconds=QuerybookSettings.LOGS_OUT_AFTER
        )

    if QuerybookSettings.TABLE_MAX_UPLOAD_SIZE is not None:
        app.config["MAX_CONTENT_LENGTH"] = int(QuerybookSettings.TABLE_MAX_UPLOAD_SIZE)

    # Add Content-Security-Policy header to restrict iframe embedding to the allowed origins
    csp_header_value = "frame-ancestors 'self' " + " ".join(
        QuerybookSettings.IFRAME_ALLOWED_ORIGINS or []
    )

    @app.after_request
    def add_csp_header(response):
        response.headers["Content-Security-Policy"] = csp_header_value
        return response

    # Initialize Flask-RESTX
    api = Api(app, version='1.0', title='Querybook API',
              description='API for Querybook', doc='/api/docs')

    # Create namespaces for all datasources
    namespaces = {
        'admin': Namespace('admin', description='Admin operations'),
        'admin_audit_log': Namespace('admin_audit_log', description='Admin audit log operations'),
        'board': Namespace('board', description='Board operations'),
        'comment': Namespace('comment', description='Comment operations'),
        'dag_exporter': Namespace('dag_exporter', description='DAG exporter operations'),
        'data_element': Namespace('data_element', description='Data element operations'),
        'datadoc': Namespace('datadoc', description='DataDoc operations'),
        'event_log': Namespace('event_log', description='Event log operations'),
        'github': Namespace('github', description='GitHub operations'),
        'impression': Namespace('impression', description='Impression operations'),
        'metastore': Namespace('metastore', description='Metastore operations'),
        'query_engine': Namespace('query_engine', description='Query engine operations'),
        'query_execution': Namespace('query_execution', description='Query execution operations'),
        'query_review': Namespace('query_review', description='Query review operations'),
        'query_snippet': Namespace('query_snippet', description='Query snippet operations'),
        'query_transform': Namespace('query_transform', description='Query transform operations'),
        'schedule': Namespace('schedule', description='Schedule operations'),
        'search': Namespace('search', description='Search operations'),
        'survey': Namespace('survey', description='Survey operations'),
        'table_upload': Namespace('table_upload', description='Table upload operations'),
        'tag': Namespace('tag', description='Tag operations'),
        'user': Namespace('user', description='User operations'),
        'utils': Namespace('utils', description='Utility operations'),
    }

    # Add namespaces to the API
    for ns in namespaces.values():
        api.add_namespace(ns)

    # Register routes from all datasources
    datasource_modules = [
        admin, admin_audit_log, board, comment, dag_exporter, data_element,
        datadoc, event_log, github, impression, metastore, query_engine,
        query_execution, query_review, query_snippet, query_transform,
        schedule, search, survey, table_upload, tag, user, utils
    ]

    for module in datasource_modules:
        if hasattr(module, 'register_routes'):
            try:
                module.register_routes(namespaces[module.__name__.split('.')[-1]])
            except Exception as e:
                app.logger.error(f"Error registering routes for {module.__name__}: {str(e)}")
        else:
            app.logger.warning(f"Module {module.__name__} does not have a register_routes function")

    return app


def make_cache(app):
    return Cache(
        app,
        config=QuerybookSettings.FLASK_CACHE_CONFIG,
    )


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=QuerybookSettings.REDIS_URL,
        broker=QuerybookSettings.REDIS_URL,
    )

    celery.conf.update(
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1,
        task_track_started=True,
        task_soft_time_limit=172800,
        worker_proc_alive_timeout=60,
        broker_transport_options={
            # This must be higher than soft time limit,
            # otherwise the task will get retried (in the case of acks_late=True)
            # after visibility timeout
            "visibility_timeout": 180000  # 2 days + 2 hours
        },
    )

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            # If request context is already present then the celery task is called
            # sychronously in a request, so no need to generate a new app context
            if has_request_context():
                return TaskBase.__call__(self, *args, **kwargs)
            # Otherwise in worker, we create the context and run
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def make_limiter(app):
    def limiter_key_func():
        from flask_login import current_user

        if hasattr(current_user, "id"):
            return current_user.id
        return get_remote_address()

    limiter = Limiter(
        app,
        key_func=limiter_key_func,
        default_limits=["60 per minute"],
        default_limits_per_method=True,
    )
    limiter.enabled = QuerybookSettings.PRODUCTION
    for handler in app.logger.handlers:
        limiter.logger.addHandler(handler)

    @app.after_request
    def limiter_add_headers(response):
        if limiter.enabled and limiter.current_limit and limiter.current_limit.breached:
            response.headers["flask-limit-amount"] = limiter.current_limit.limit.amount
            response.headers["flask-limit-key"] = limiter.current_limit.key
            response.headers["flask-limit-reset-at"] = limiter.current_limit.reset_at
            response.headers[
                "flask-limit-window-size"
            ] = limiter.current_limit.limit.get_expiry()
        return response

    return limiter


def make_socketio(app):
    socketio = SocketIO(
        app,
        path="-/socket.io",
        message_queue=QuerybookSettings.REDIS_URL,
        json=flask_json,
        cors_allowed_origins=(
            QuerybookSettings.WS_CORS_ALLOWED_ORIGINS
            if QuerybookSettings.PRODUCTION
            else "*"
        ),
    )
    return socketio


def make_blue_print(app, limiter, api):
    # Have flask automatically return the files within the build, so that it gzips them
    # and handles its 200/304 logic.
    blueprint = Blueprint(
        "static_build_files",
        __name__,
        static_folder=WEBAPP_DIR_PATH,
        static_url_path=BUILD_PATH,
    )
    app.register_blueprint(blueprint)
    limiter.exempt(blueprint)

    # Add Swagger UI
    @app.route('/swagger')
    def swagger_ui():
        return api.swagger_ui()

    return blueprint


validate_db()
flask_app = make_flask_app()
api = Api(flask_app, version='1.0', title='Querybook API',
          description='API for Querybook', doc='/api/docs')
limiter = make_limiter(flask_app)
make_blue_print(flask_app, limiter, api)
cache = make_cache(flask_app)
celery = make_celery(flask_app)
socketio = make_socketio(flask_app)

# Add a sample endpoint
@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        """A simple hello world endpoint"""
        return {'message': 'Hello from Querybook API!'}
