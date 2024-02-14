import typing as t
from datetime import date as d
from datetime import datetime as dt
from textwrap import dedent

try:
    from sqlalchemy import (
        Result,
        Select,
        Insert,
        Update,
        Delete,
        select,
        insert,
        update,
        delete,
        func,
        Column,
    )
    from sqlalchemy.engine import Row
    from sqlalchemy.inspection import inspect
    from sqlalchemy.orm import collections, Session
    from sqlalchemy.sql import sqltypes

except ImportError:
    raise ImportError("SQLAlchemy is not installed")

try:
    from flask_sqlalchemy import SQLAlchemy
    from flask_sqlalchemy.pagination import Pagination
except ImportError:
    raise ImportError("Flask-SQLAlchemy is not installed")


class ParseValueError(Exception):
    def __init__(self, key, value: t.Any, type_: t.Any):
        self.message = (
            f"Unable to parse value: {value} - of raw "
            f"type: {type(value)} - for: {key} - as sqla type: {type_}"
        )
        super().__init__(self.message)


class ModelAttributeError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class UtilityMixin:
    __um_session__: SQLAlchemy = None

    @classmethod
    def _um_check_session_exists(cls):
        if not cls.__um_session__:
            if hasattr(cls, "query"):
                cls.__um_session__ = cls.query.session
                return

            raise AttributeError(
                dedent(
                    """
                The class using this mixin must have a db attribute set to the Flask-SQLAlchemy instance",
                Example:
                from app.extensions import db
                class Example(db.Model, UtilityMixin):
                    __um_session__ = db.session
                """
                ),
            )

    @staticmethod
    def _um_row_as_dict(row: Row) -> dict:
        return {key: row.__dict__[key] for key in row.__dict__ if key[0] != "_"}

    @staticmethod
    def _um_parse_value(key, value, type_):
        """
        Returns value as type_ if possible, otherwise raises ParseValueException

        :param key:
        :param value:
        :param type_:
        :return:
        """

        if isinstance(type_, sqltypes.DateTime):
            if isinstance(value, dt):
                return value

            if isinstance(value, d):
                return dt.combine(value, dt.min.time())

            if isinstance(value, str):
                # Guess the format
                try:
                    return dt.strptime(value, "%Y-%m-%d")
                except ValueError:
                    pass

                try:
                    return dt.strptime(value, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    pass

                try:
                    return dt.strptime(value, "%Y-%m-%dT%H:%M:%d.%f")
                except ValueError:
                    pass

                raise ParseValueError(key, value, type_)

        if isinstance(type_, sqltypes.Integer):
            try:
                return int(value)
            except ValueError:
                pass

            raise ParseValueError(key, value, type_)

        if isinstance(type_, sqltypes.Boolean):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ["yes", "true", "t", "1"]:
                    return True
                return False
            if isinstance(value, int):
                if value == 1:
                    return True
                return False

            raise ParseValueError(key, value, type_)

        return value

    @staticmethod
    def _parse_rows(
            cls,
            rows: t.Union[Row, list, dict],
            include_joins: list[tuple[str, str] | str] = None,
            cast_joins: list[tuple[str, str]] = None,
            all_columns_but: list = None,
            only_columns: list = None,
            _is_join: bool = False,
    ) -> t.Union[dict, list]:
        """
        Parses the rows into a dictionary or list of dictionaries

        include_joins: [('given_name', 'join_attr') | 'join_attr']
        cast_joins: [('given_name', 'join_attr.attr_of_join')]

        all_columns_but: ['column_name', ...] # exclude these columns in the return
        only_columns: ['column_name', ...] # only include these columns in the return

        _is_join: Tell the function if it is parsing a join or not, this is for
        internal use only
        """

        if isinstance(rows, list):
            return [cls._parse_rows(row, _is_join=True) for row in rows]

        if include_joins is None:
            include_joins = []

        if all_columns_but is None:
            all_columns_but = []

        if only_columns is None:
            only_columns = []

        def include_column(column_: str) -> bool:
            if only_columns:
                if column_ not in only_columns:
                    return False

            if all_columns_but:
                if column_ in all_columns_but:
                    return False

            return True

        data = dict()
        for column, value in cls._um_row_as_dict(rows).items():
            if not _is_join:
                if not include_column(column):
                    continue

            if isinstance(value, collections.InstrumentedList):
                continue

            data[column] = value

        if _is_join:
            return data

        joins = dict()
        if include_joins:
            for join in include_joins:
                if isinstance(join, tuple):
                    name, join_attr = join
                    if hasattr(rows, join_attr):
                        joins[name] = [
                                          cls._parse_rows(row, _is_join=True)
                                          for row in getattr(rows, join_attr)
                                      ] or []

                if isinstance(join, str):
                    if hasattr(rows, join):
                        if isinstance(getattr(rows, join), list):
                            joins[join] = [
                                              cls._parse_rows(row, _is_join=True)
                                              for row in getattr(rows, join)
                                          ] or []

                            continue

                        joins[join] = cls._parse_rows(rows, _is_join=True)

        if cast_joins:
            for given_name, join_cast in cast_joins:
                split_join_cast = join_cast.split(".")
                if hasattr(rows, split_join_cast[0]):
                    join_attr = getattr(rows, split_join_cast[0])
                    if hasattr(join_attr, split_join_cast[1]):
                        data[given_name] = getattr(join_attr, split_join_cast[1])
                    else:
                        data[given_name] = None
                else:
                    data[given_name] = None

        return {**data, **joins}

    def um_commit(self):
        self._um_check_session_exists()

        self.__um_session__.commit()
        return self

    @classmethod
    def um_count(
            cls,
            pkv: int = None,
            fields: dict = None,
    ) -> int:
        """
        pkv is the primary key value
        fields: {'model_attribute': 'value', ...}
        """
        cls._um_check_session_exists()

        q = select(func.count()).select_from(cls)

        if pkv:
            pk = inspect(cls).primary_key[0]
            q = q.where(pk == pkv)

        if fields:
            if fields:
                for model_attr, value in fields.items():
                    if hasattr(cls, model_attr):
                        q = q.where(getattr(cls, model_attr) == value)  # type: ignore

        return cls.__um_session__.execute(q).scalar()

    # ~ CRUD

    # Create
    @classmethod
    def um_create(
            cls,
            values: dict,
            allow_none: bool = True,
            return_record: bool = False,
    ) -> t.Optional[t.Self]:
        cls._um_check_session_exists()

        new_values = {
            key: cls._um_parse_value(key, value, getattr(cls, key).type)
            if not allow_none
            else value
            for key, value in values.items()
            if hasattr(cls, key)
        }

        if return_record:
            r = cls.__um_session__.execute(
                insert(cls).values(**new_values).returning(cls)
            ).scalar_one_or_none()
            cls.__um_session__.commit()
            return r

        cls.__um_session__.execute(insert(cls).values(**new_values))
        cls.__um_session__.commit()

    @classmethod
    def um_create_batch(
            cls,
            batch_values: list[dict],
            allow_none: bool = True,
    ) -> tuple[t.Any, t.Any] | tuple[None, None]:
        cls._um_check_session_exists()

        _ = [
            {
                key: cls._um_parse_value(key, value, getattr(cls, key).type)
                if not allow_none
                else value
                for key, value in x.items()
                if hasattr(cls, key)
            }
            for x in batch_values
        ]

        r = cls.__um_session__.execute(insert(cls).values(_))
        cls.__um_session__.commit()
        return r

    # Read
    @classmethod
    def um_read(
            cls,
            pkv: int = None,
            fields: dict = None,
            custom_select: Select = None,
            order_by: dict = None,
            one_or_none: bool = False,
            first: bool = False,
            paginate: bool = False,
            paginate_page: int = 1,
            paginate_per_page: int = 10,
            paginate_count: bool = True,
            as_json: bool = False,
            json_include_joins: list[tuple[str, str] | str] = None,
            json_return_key_name: str = None,
            json_only_columns: list = None,
            json_remove_return_key: bool = False,
    ) -> t.Union[dict, list, t.Any] | t.Any:
        """
        pkv is the primary key value
        fields: {'model_attribute': 'value', ...}
        custom_select: pass your own select query in

        order_by: {'model_attribute': 'asc' | 'desc', ...}
        one_or_none: True | False # if True, return one or None
        first: True | False # if True, return the first result

        paginate: True | False # if True, paginate the results
        as_json: True | False # if True, return the results as a jsonable dict

        paginate and as_json can be used together.
        """
        cls._um_check_session_exists()

        if custom_select:
            q = custom_select

        else:
            q = select(cls)

        if pkv:
            pk = inspect(cls).primary_key[0]
            q = q.where(pk == pkv)

        if fields:
            for model_attr, value in fields.items():
                if hasattr(cls, model_attr):
                    q = q.where(getattr(cls, model_attr) == value)  # type: ignore

        if order_by:
            for field, direction in order_by.items():
                if hasattr(cls, field):
                    if direction == "asc":
                        q = q.order_by(getattr(cls, field).desc())
                    else:
                        q = q.order_by(getattr(cls, field).asc())

        if paginate and not as_json:
            return cls.__um_session__.paginate(
                q, page=paginate_page, per_page=paginate_per_page, count=paginate_count
            )

        if as_json:
            return cls.um_as_jsonable_dict(
                q,
                return_key_name=json_return_key_name
                if json_return_key_name
                else cls.__name__,
                one_or_none=one_or_none,
                include_joins=json_include_joins,
                only_columns=json_only_columns,
                remove_return_key=json_remove_return_key,
                **{
                    "paginate": True,
                    "paginate_page": paginate_page,
                    "paginate_per_page": paginate_per_page,
                    "paginate_count": paginate_count,
                }
                if paginate
                else {"paginate": False},
            )

        if one_or_none:
            return cls.__um_session__.execute(q).scalar_one_or_none()

        if first:
            return cls.__um_session__.execute(q).first()

        return cls.__um_session__.execute(q).scalars().all()

    # Update
    @classmethod
    def um_update(
            cls,
            where: dict[str, t.Union[str, list]] = None,
            custom_update: Update = None,
            values: dict = None,
            skip_attrs: list[str] = None,
            fail_on_unknown_attr: bool = True,
            return_record: bool = False,
            return_input_values: bool = False,
            prevent_commit: bool = False,
    ) -> t.Optional[t.Union[dict, Result]]:
        """
        where: {'model_attribute': 'value' | ['values'...], ...} :raw-html:`<br />`
        if where value is a list, the query will use the IN operator. :raw-html:`<br />`
        values: {'model_attribute': 'value', ...} :raw-html:`<br />`
        fail_on_unknown_attr will raise a ValueError if an attribute is not found in the model :raw-html:`<br />`
        if fail_on_unknown_attr is False, the function will ignore any attribute not found in the model
        """
        cls._um_check_session_exists()

        if not values:
            raise ValueError("values parameter is required")

        pk = inspect(cls).primary_key[0]

        if custom_update:
            q = custom_update
        else:
            q = update(cls)

        if where:
            for model_attr, value in where.items():
                if hasattr(cls, model_attr):
                    if isinstance(value, list):
                        q = q.where(getattr(cls, model_attr).in_(value))
                    else:
                        q = q.where(getattr(cls, model_attr) == value)
        else:
            if pk.name not in values:
                raise ValueError(f"Primary key value not found in values")
            else:
                q.where(pk == values[pk.name])  # type: ignore

        _ = {}

        for key, value in values.items():
            if key in skip_attrs:
                continue
            if key == pk.name:
                continue
            if hasattr(cls, key):
                _[key] = cls._um_parse_value(key, value, getattr(cls, key).type)
            else:
                if fail_on_unknown_attr:
                    raise ModelAttributeError(
                        f"Model attribute {key} not found in {cls.__name__}"
                    )

        if return_record:
            r = cls.__um_session__.execute(
                q.values(**_).returning(cls)
            ).scalar_one_or_none()

            if not prevent_commit:
                cls.__um_session__.commit()
            return r

        cls.__um_session__.execute(q.values(**_))  # type: ignore

        if not prevent_commit:
            cls.__um_session__.commit()

        if return_input_values:
            return _

    def um_inline_update(self, values: dict, fail_on_unknown_attr: bool = True):
        for key, value in values.items():
            if hasattr(self, key):
                setattr(
                    self, key, self._um_parse_value(key, value, getattr(self, key).type)
                )
            else:
                if fail_on_unknown_attr:
                    raise ModelAttributeError(
                        f"Model attribute {key} not found in {self.__name__}"
                    )

        return self

    # Delete
    @classmethod
    def um_delete(
            cls,
            pkv: int = None,
            fields: dict = None,
            fail_on_unknown_attr: bool = True,
            prevent_commit: bool = False,
    ) -> None:
        """
        pkv is the primary key value
        fields: {'model_attribute': 'value', ...}
        """
        cls._um_check_session_exists()

        q = delete(cls)
        if pkv:
            pk = inspect(cls).primary_key[0]
            q.where(pk == pkv)

        if fields:
            for model_attr, value in fields.items():
                if hasattr(cls, model_attr):
                    q = q.where(getattr(cls, model_attr) == value)  # type: ignore
                else:
                    if fail_on_unknown_attr:
                        raise ValueError(
                            f"Model attribute {model_attr} not found in {cls.__name__}"
                        )

        cls.__um_session__.execute(q)

        if not prevent_commit:
            cls.__um_session__.commit()

    @classmethod
    def um_as_jsonable_dict(
            cls,
            execute: t.Union[Select, Insert, Update, Delete, Result, Pagination],
            return_key_name: str = None,
            remove_return_key: bool = False,
            include_joins: list[tuple[str, str] | str] = None,
            cast_joins: list[tuple[str, str]] = None,
            all_columns_but: list = None,
            only_columns: list = None,
            one_or_none: bool = False,
            first: bool = False,
            paginate: bool = False,
            paginate_page: int = 1,
            paginate_per_page: int = 10,
            paginate_count: bool = True,
    ) -> (
            dict
            | dict[str | None, dict]
            | dict[t.Any, t.Any]
            | list[dict]
            | dict[str | None, list[dict]]
    ):
        cls._um_check_session_exists()

        if (
                isinstance(execute, Select)
                or isinstance(execute, Insert)
                or isinstance(execute, Update)
                or isinstance(execute, Delete)
        ):
            if paginate:
                execute: t.Union[Result, Pagination] = cls.__um_session__.paginate(
                    execute,
                    page=paginate_page,
                    per_page=paginate_per_page,
                    count=paginate_count,
                )
            else:
                execute = cls.__um_session__.execute(execute)

        shrink_args = {
            "include_joins": include_joins,
            "cast_joins": cast_joins,
            "all_columns_but": all_columns_but,
            "only_columns": only_columns,
        }

        if one_or_none:
            if not hasattr(execute, "scalar_one_or_none"):
                raise ValueError(
                    "execute does not have a scalar_one_or_none() attribute"
                )

            r = execute.scalar_one_or_none()
            if r:
                if remove_return_key:
                    return cls._parse_rows(r, **shrink_args)

                return {
                    cls.__um_session__.__name__
                    if return_key_name is None
                    else return_key_name: cls._parse_rows(r, **shrink_args)
                }

            return {}

        if first:
            if not hasattr(execute, "first"):
                raise ValueError("execute does not have a first() attribute")

            r = execute.scalars().first()
            if r:
                if remove_return_key:
                    return cls._parse_rows(r, **shrink_args)

                return {
                    cls.__um_session__.__name__
                    if return_key_name is None
                    else return_key_name: cls._parse_rows(r, **shrink_args)
                }

            return {}

        if remove_return_key:
            r = (
                [cls._parse_rows(x, **shrink_args) for x in execute.items]
                if paginate
                else [
                    cls._parse_rows(x, **shrink_args) for x in execute.scalars().all()
                ]
            )

            if paginate:
                return {
                    "__paginate__": {
                        "page": execute.page,
                        "pages": execute.pages,
                        "per_page": execute.per_page,
                        "total": execute.total,
                    },
                    "data": r,
                }

            return {"data": r}

        return {
            "__paginate__": {
                "page": execute.page,
                "pages": execute.pages,
                "per_page": execute.per_page,
                "total": execute.total,
            }
            if paginate
            else None,
            cls.__um_session__.__name__
            if return_key_name is None
            else return_key_name: [
                cls._parse_rows(x.items, **shrink_args) for x in execute.items
            ]
            if paginate
            else [cls._parse_rows(x, **shrink_args) for x in execute.scalars().all()],
        }
