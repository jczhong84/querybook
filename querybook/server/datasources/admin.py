from flask_login import current_user
from flask_restx import Namespace, Resource

from app.datasource import admin_only, api_assert
from app.db import DBSession
from const.admin import AdminOperation, AdminItemType
from datasources.admin_audit_log import with_admin_audit_log
from env import QuerybookSettings

from lib.engine_status_checker import (
    ALL_ENGINE_STATUS_CHECKERS,
    get_engine_checker_class,
)
from lib.metastore.all_loaders import ALL_METASTORE_LOADERS
from lib.table_upload.exporter.exporter_factory import ALL_TABLE_UPLOAD_EXPORTER_BY_NAME
from lib.query_executor.all_executors import (
    get_flattened_executor_template,
    get_executor_class,
)
from lib.query_analysis.validation.all_validators import ALL_QUERY_VALIDATORS_BY_NAME
from logic import admin as logic
from logic import user as user_logic
from logic import environment as environment_logic
from logic import demo as demo_logic
from models.admin import Announcement, QueryMetastore, QueryEngine, AdminAuditLog

def register_routes(api: Namespace):
    @api.route('/announcement/')
    class AnnouncementResource(Resource):
        def get(self):
            """Get all announcements"""
            return logic.get_admin_announcements()

    @api.route('/admin/announcement/')
    class AdminAnnouncementResource(Resource):
        @admin_only
        def get(self):
            """Get all announcements (admin view)"""
            announcements = Announcement.get_all()
            announcements_dict = [
                announcement.to_dict_admin() for announcement in announcements
            ]
            return announcements_dict

        @admin_only
        @api.doc(params={
            'message': 'Announcement message',
            'url_regex': 'URL regex',
            'can_dismiss': 'Can be dismissed',
            'active_from': 'Active from date',
            'active_till': 'Active till date'
        })
        @with_admin_audit_log(AdminItemType.Announcement, AdminOperation.CREATE)
        def post(self):
            """Create a new announcement"""
            data = api.payload
            with DBSession() as session:
                announcement = Announcement.create(
                    {
                        "uid": current_user.id,
                        "url_regex": data.get('url_regex', ''),
                        "can_dismiss": data.get('can_dismiss', True),
                        "message": data['message'],
                        "active_from": data.get('active_from'),
                        "active_till": data.get('active_till'),
                    },
                    session=session,
                )
                announcement_dict = announcement.to_dict_admin()
            return announcement_dict

    @api.route('/admin/announcement/<int:id>/')
    class AdminAnnouncementItemResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Announcement ID'})
        @with_admin_audit_log(AdminItemType.Announcement, AdminOperation.UPDATE)
        def put(self, id):
            """Update an announcement"""
            data = api.payload
            with DBSession() as session:
                announcement = Announcement.update(
                    id=id,
                    fields={
                        **data,
                        "uid": current_user.id,
                    },
                    field_names=[
                        "uid",
                        "message",
                        "url_regex",
                        "can_dismiss",
                        "active_from",
                        "active_till",
                    ],
                    session=session,
                )
                announcement_dict = announcement.to_dict_admin()
            return announcement_dict

        @admin_only
        @api.doc(params={'id': 'Announcement ID'})
        @with_admin_audit_log(AdminItemType.Announcement, AdminOperation.DELETE)
        def delete(self, id):
            """Delete an announcement"""
            Announcement.delete(id)
            return {"message": "Announcement deleted successfully"}

    @api.route('/admin/query_engine_template/')
    class QueryEngineTemplateResource(Resource):
        @admin_only
        def get(self):
            """Get all query engine templates"""
            return get_flattened_executor_template()

    @api.route('/admin/query_engine_status_checker/')
    class QueryEngineStatusCheckerResource(Resource):
        @admin_only
        def get(self):
            """Get all query engine status checkers"""
            return [checker.NAME() for checker in ALL_ENGINE_STATUS_CHECKERS]

    @api.route('/admin/query_engine/')
    class QueryEngineResource(Resource):
        @admin_only
        def get(self):
            """Get all query engines (admin view)"""
            with DBSession() as session:
                engines = QueryEngine.get_all(session=session)
                engines_dict = [engine.to_dict_admin() for engine in engines]
                return engines_dict

        @admin_only
        @api.doc(params={
            'name': 'Engine name',
            'language': 'Query language',
            'executor': 'Executor type',
            'executor_params': 'Executor parameters',
            'feature_params': 'Feature parameters',
            'description': 'Engine description',
            'metastore_id': 'Metastore ID'
        })
        @with_admin_audit_log(AdminItemType.QueryEngine, AdminOperation.CREATE)
        def post(self):
            """Create a new query engine"""
            data = api.payload
            with DBSession() as session:
                query_engine = QueryEngine.create(
                    {
                        "name": data['name'],
                        "description": data.get('description'),
                        "language": data['language'],
                        "executor": data['executor'],
                        "executor_params": data['executor_params'],
                        "feature_params": data['feature_params'],
                        "metastore_id": data.get('metastore_id'),
                    },
                    session=session,
                )
                query_engine_dict = query_engine.to_dict_admin()
            return query_engine_dict

    @api.route('/admin/query_engine/connection/')
    class QueryEngineConnectionResource(Resource):
        @admin_only
        @api.doc(params={
            'name': 'Engine name',
            'language': 'Query language',
            'executor': 'Executor type',
            'executor_params': 'Executor parameters',
            'feature_params': 'Feature parameters'
        })
        def get(self):
            """Test query engine connection"""
            data = api.payload
            status_checker = get_engine_checker_class(data['feature_params']["status_checker"])
            executor_class = get_executor_class(data['language'], data['executor'])
            pseudo_engine_dict = {
                "name": data['name'],
                "language": data['language'],
                "executor": data['executor'],
                "executor_params": data['executor_params'],
                "feature_params": data['feature_params'],
            }
            return status_checker.perform_check_with_executor(
                executor_class, data['executor_params'], pseudo_engine_dict
            )

    @api.route('/admin/query_engine/<int:id>/')
    class QueryEngineItemResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Query Engine ID'})
        @with_admin_audit_log(AdminItemType.QueryEngine, AdminOperation.UPDATE)
        def put(self, id):
            """Update a query engine"""
            data = api.payload
            with DBSession() as session:
                query_engine = QueryEngine.update(
                    id,
                    data,
                    field_names=[
                        "name",
                        "description",
                        "language",
                        "executor",
                        "executor_params",
                        "feature_params",
                        "metastore_id",
                        "deleted_at",
                        "status_checker",
                    ],
                    session=session,
                )
                query_engine_dict = query_engine.to_dict_admin()
            return query_engine_dict

        @admin_only
        @api.doc(params={'id': 'Query Engine ID'})
        @with_admin_audit_log(AdminItemType.QueryEngine, AdminOperation.DELETE)
        def delete(self, id):
            """Delete a query engine"""
            logic.delete_query_engine_by_id(id)
            return {"message": "Query engine deleted successfully"}

    @api.route('/admin/query_engine/<int:id>/recover/')
    class QueryEngineRecoverResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Query Engine ID'})
        @with_admin_audit_log(AdminItemType.QueryEngine, AdminOperation.UPDATE)
        def post(self, id):
            """Recover a deleted query engine"""
            logic.recover_query_engine_by_id(id)
            return {"message": "Query engine recovered successfully"}

    @api.route('/admin/query_metastore_loader/')
    class QueryMetastoreLoaderResource(Resource):
        @admin_only
        def get(self):
            """Get all query metastore loaders"""
            return [
                loader_class.serialize_loader_class() for loader_class in ALL_METASTORE_LOADERS
            ]

    @api.route('/admin/query_metastore/')
    class QueryMetastoreResource(Resource):
        @admin_only
        def get(self):
            """Get all query metastores (admin view)"""
            with DBSession() as session:
                metastores = logic.get_all_query_metastore(session=session)
                metastores_dict = [metastore.to_dict_admin() for metastore in metastores]
            return metastores_dict

        @admin_only
        @api.doc(params={
            'name': 'Metastore name',
            'metastore_params': 'Metastore parameters',
            'loader': 'Loader type',
            'acl_control': 'ACL control'
        })
        @with_admin_audit_log(AdminItemType.QueryMetastore, AdminOperation.CREATE)
        def post(self):
            """Create a new query metastore"""
            data = api.payload
            with DBSession() as session:
                metastore = QueryMetastore.create(
                    {
                        "name": data['name'],
                        "metastore_params": data['metastore_params'],
                        "loader": data['loader'],
                        "acl_control": data.get('acl_control'),
                    },
                    session=session,
                )
                metastore_dict = metastore.to_dict_admin()
            return metastore_dict

    @api.route('/admin/query_metastore/<int:id>/')
    class QueryMetastoreItemResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Query Metastore ID'})
        @with_admin_audit_log(AdminItemType.QueryMetastore, AdminOperation.UPDATE)
        def put(self, id):
            """Update a query metastore"""
            data = api.payload
            with DBSession() as session:
                metastore = QueryMetastore.update(
                    id=id,
                    fields=data,
                    field_names=["name", "loader", "metastore_params", "acl_control"],
                    update_callback=lambda m: logic.sync_metastore_schedule_job(
                        m.id, session=session
                    ),
                    session=session,
                )
                metastore_dict = metastore.to_dict_admin()
            return metastore_dict

        @admin_only
        @api.doc(params={'id': 'Query Metastore ID'})
        @with_admin_audit_log(AdminItemType.QueryMetastore, AdminOperation.DELETE)
        def delete(self, id):
            """Delete a query metastore"""
            logic.delete_query_metastore_by_id(id)
            return {"message": "Query metastore deleted successfully"}

    @api.route('/admin/query_metastore/<int:id>/recover/')
    class QueryMetastoreRecoverResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Query Metastore ID'})
        @with_admin_audit_log(AdminItemType.QueryMetastore, AdminOperation.UPDATE)
        def put(self, id):
            """Recover a deleted query metastore"""
            logic.recover_query_metastore_by_id(id)
            return {"message": "Query metastore recovered successfully"}

    @api.route('/admin/query_metastore/<int:id>/schedule/')
    class QueryMetastoreScheduleResource(Resource):
        @admin_only
        @api.doc(params={
            'id': 'Query Metastore ID',
            'cron': 'Cron expression for the schedule'
        })
        def post(self, id):
            """Create a schedule for query metastore update"""
            data = api.payload
            with DBSession() as session:
                return logic.create_query_metastore_update_schedule(
                    metastore_id=id, cron=data['cron'], session=session
                )

    @api.route('/admin/user_role/')
    class UserRoleResource(Resource):
        @admin_only
        def get(self):
            """Get all user roles"""
            with DBSession() as session:
                return user_logic.get_all_user_role(session=session)

        @admin_only
        @api.doc(params={
            'uid': 'User ID',
            'role': 'Role to assign'
        })
        @with_admin_audit_log(AdminItemType.Admin, AdminOperation.CREATE)
        def post(self):
            """Create a new user role"""
            data = api.payload
            with DBSession() as session:
                return user_logic.create_user_role(uid=data['uid'], role=data['role'], session=session)

    @api.route('/admin/user_role/<int:id>/')
    class UserRoleItemResource(Resource):
        @admin_only
        @api.doc(params={'id': 'User Role ID'})
        @with_admin_audit_log(AdminItemType.Admin, AdminOperation.DELETE)
        def delete(self, id):
            """Delete a user role"""
            user_logic.delete_user_role(id)
            return {"message": "User role deleted successfully"}

    @api.route('/admin/environment/')
    class EnvironmentResource(Resource):
        @admin_only
        def get(self):
            """Get all environments"""
            return environment_logic.get_all_environment(include_deleted=True)

        @admin_only
        @api.doc(params={
            'name': 'Environment name',
            'description': 'Environment description',
            'image': 'Environment image',
            'public': 'Is public',
            'hidden': 'Is hidden',
            'deleted_at': 'Deletion timestamp',
            'shareable': 'Is shareable'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.CREATE)
        def post(self):
            """Create a new environment"""
            data = api.payload
            return environment_logic.create_environment(**data)

    @api.route('/admin/environment/<int:id>/')
    class EnvironmentItemResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Environment ID'})
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def put(self, id):
            """Update an environment"""
            data = api.payload
            return environment_logic.update_environment(id=id, **data)

        @admin_only
        @api.doc(params={'id': 'Environment ID'})
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.DELETE)
        def delete(self, id):
            """Delete an environment"""
            environment_logic.delete_environment_by_id(id)
            return {"message": "Environment deleted successfully"}

    @api.route('/admin/environment/<int:id>/recover/')
    class EnvironmentRecoverResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Environment ID'})
        def put(self, id):
            """Recover a deleted environment"""
            environment_logic.recover_environment_by_id(id)
            return {"message": "Environment recovered successfully"}

    @api.route('/admin/environment/<int:id>/users/')
    class EnvironmentUsersResource(Resource):
        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'limit': 'Number of users to return',
            'offset': 'Offset for pagination'
        })
        def get(self, id):
            """Get users in an environment"""
            args = api.payload
            with DBSession() as session:
                return environment_logic.get_users_in_environment(
                    id, args['offset'], args['limit'], session=session
                )

    @api.route('/admin/environment/<int:id>/user/<int:uid>/')
    class EnvironmentUserResource(Resource):
        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'uid': 'User ID'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def post(self, id, uid):
            """Add a user to an environment"""
            environment_logic.add_user_to_environment(uid, id)
            return {"message": "User added to environment successfully"}

        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'uid': 'User ID'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def delete(self, id, uid):
            """Remove a user from an environment"""
            environment_logic.remove_user_to_environment(uid, id)
            return {"message": "User removed from environment successfully"}

    @api.route('/admin/environment/<int:id>/query_engine/')
    class EnvironmentQueryEngineResource(Resource):
        @admin_only
        @api.doc(params={'id': 'Environment ID'})
        def get(self, id):
            """Get query engines in an environment"""
            return logic.get_query_engines_by_environment(id, ordered=True)

        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'engine_id': 'Query Engine ID'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def post(self, id):
            """Add a query engine to an environment"""
            data = api.payload
            return logic.add_query_engine_to_environment(id, data['engine_id'])

    @api.route('/admin/environment/<int:id>/query_engine/<int:engine_id>/')
    class EnvironmentQueryEngineItemResource(Resource):
        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'engine_id': 'Query Engine ID'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def delete(self, id, engine_id):
            """Remove a query engine from an environment"""
            logic.remove_query_engine_from_environment(id, engine_id)
            return {"message": "Query engine removed from environment successfully"}

    @api.route('/admin/environment/<int:id>/query_engine/<int:from_index>/<int:to_index>/')
    class EnvironmentQueryEngineOrderResource(Resource):
        @admin_only
        @api.doc(params={
            'id': 'Environment ID',
            'from_index': 'Original index of the query engine',
            'to_index': 'New index for the query engine'
        })
        @with_admin_audit_log(AdminItemType.Environment, AdminOperation.UPDATE)
        def put(self, id, from_index, to_index):
            """Swap the order of query engines in an environment"""
            logic.swap_query_engine_order_in_environment(id, from_index, to_index)
            return {"message": "Query engine order updated successfully"}

    @api.route('/admin/api_access_token/<token_id>/')
    class ApiAccessTokenResource(Resource):
        @admin_only
        @api.doc(params={
            'token_id': 'API Access Token ID',
            'enabled': 'Enable or disable the token'
        })
        def put(self, token_id):
            """Update an API Access Token"""
            data = api.payload
            uid = current_user.id
            return logic.update_api_access_token(uid, token_id, data.get('enabled', False))

    @api.route('/admin/api_access_tokens/')
    class ApiAccessTokensResource(Resource):
        @admin_only
        def get(self):
            """Get all API Access Tokens"""
            return logic.get_api_access_tokens()

    @api.route('/admin/demo_set_up/')
    class DemoSetUpResource(Resource):
        @admin_only
        def post(self):
            """Set up demo environment"""
            return demo_logic.set_up_demo(current_user.id)

    @api.route('/admin/audit_log/')
    class AdminAuditLogResource(Resource):
        @admin_only
        @api.doc(params={
            'item_type': 'Type of the audited item',
            'item_id': 'ID of the audited item',
            'offset': 'Offset for pagination',
            'limit': 'Number of logs to return'
        })
        def get(self):
            """Get admin audit logs"""
            args = api.payload
            api_assert(args.get('limit', 10) < 200)
            item_type = args.get('item_type')
            api_assert(item_type is None or item_type in set(item.value for item in AdminItemType))

            filters = {}
            if item_type is not None:
                filters["item_type"] = item_type
            if args.get('item_id') is not None:
                filters["item_id"] = args['item_id']

            return AdminAuditLog.get_all(
                **filters, limit=args.get('limit', 10), offset=args.get('offset', 0),
                order_by="id", desc=True
            )

    @api.route('/admin/querybook_config/')
    class QuerybookConfigResource(Resource):
        @admin_only
        def get(self):
            """Get Querybook configuration"""
            return {
                key: getattr(QuerybookSettings, key)
                for key in dir(QuerybookSettings)
                if not key.startswith("__")
            }

    @api.route('/admin/table_upload/exporter/')
    class TableUploadExporterResource(Resource):
        @admin_only
        def get(self):
            """Get all table upload exporters"""
            return list(ALL_TABLE_UPLOAD_EXPORTER_BY_NAME.keys())

    @api.route('/admin/query_validator/')
    class QueryValidatorResource(Resource):
        @admin_only
        def get(self):
            """Get all query validators"""
            return list(ALL_QUERY_VALIDATORS_BY_NAME.values())
        
