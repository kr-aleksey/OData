from typing import Any, Type

from pydantic import BaseModel, Field


class Lookup:
    """Parses lookup."""

    def __new__(cls, *args, **kwargs):
        raise NotImplementedError(
            f'Class {cls.__name__} cannot be instantiated.')

    @classmethod
    def build(cls,
              field: Field,
              lookup: str | None,
              value: Any,
              notation: str | None) -> str:
        """
        Converts a filter parameter to OData format.
        :param field: Serializer field.
        :param lookup: Lookup. 'eq', 'ne', 'ge' etc.
        :param value: Filter value.
        :param notation: Value notation. 'guid' only.
        :return: Odata filter parameter.
        """
        if lookup is None:
            lookup = cls.DEFAULT_LOOKUP
        elif lookup not in cls.LOOKUPS:
            raise TypeError(
                f"Unsupported lookup {lookup}. Use one of {cls.LOOKUPS}.")
        field_alias: str = field.validation_alias
        if notation is not None:
            notation_func = cls.NOTATIONS.get(notation)
            if notation_func is None:
                raise TypeError(
                    f"Unsupported notation {notation}. "
                    f"Use one of {list(cls.NOTATIONS.keys())}."
                )
        else:
            notation_func = None
        builder = cls.LOOKUP_BUILDER.get(lookup)
        if builder is None:
            if notation_func is not None:
                value = notation_func(value)
            return f'{field_alias} {lookup} {value}'
        return builder(field_alias, value, notation_func)

    """Lookups."""

    @staticmethod
    def in_builder(field_alias: str,
                   value: Any,
                   notation_func: callable) -> str:
        """
        :param field_alias: Field alias.
        :param value: Filter value.
        :param notation_func: Value notation func.
        Converts lookup 'in' to an Odata filter parameter.
        For example: 'foo eq value or foo_alias eq value2 ...'
        """
        items = [(f'{field_alias} eq '
                  f'{v if notation_func is None else notation_func(v)}')
                 for v in value]
        filter_str = ' or '.join(items)
        return f'{filter_str}'

    """Notations."""

    @staticmethod
    def guid_notation(value) -> str:
        """
        :param value: Value.
        :return: The guid notation of value
        """
        return f"guid'{value}'"

    LOOKUPS = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in')
    DEFAULT_LOOKUP = 'eq'
    LOOKUP_BUILDER = {
        'in': in_builder
    }
    NOTATIONS = {
        'guid': guid_notation
    }


class OData:
    serializer_class: Type[BaseModel]
    field_func = {}

    def __new__(cls, *args, **kwargs):
        assert hasattr(cls, 'serializer_class'), \
            f"Не определен обязательный атрибут {cls.__name__}.serializer_class'."
        instance = super().__new__(cls)
        instance.field_func = cls.field_func.copy()
        return instance

    def __init__(self):
        self.fields = self.serializer_class.model_fields
        self.select_fields: list[str] = []
        self._filters: list[tuple[Field, str | None, Any, str]] = []

    def filter(self, **kwargs):
        """
        Фильтр odata запроса.
        Принимает параметры фильтрации - lookups в стиле Django ORM.
        В качестве имен параметров фильтрации используйте имена полей
        self.serializer_class.
        Параметры фильтрации объединяются пока только по and.
        Пример:
            filter(foo='Строка' , bar__gt=20, uid_1c__in__guid = ['',])
        """
        for key, value in kwargs.items():
            field_lookup: list[str | None] = key.split('__', maxsplit=3)
            if len(field_lookup) == 1:
                field_lookup.extend([None, None])
            elif len(field_lookup) == 2:
                field_lookup.append(None)
            field_name, lookup, notation = field_lookup

            field = self.fields.get(field_name)
            if field is None:
                raise KeyError(
                    f"Поля '{field_name}' нет среди {list(self.fields.keys())}"
                )

            self._filters.append((field, lookup, value, notation))
        return self

    def build_select(self) -> str:
        """Generates the "$select" query parameter."""
        select_fields = []
        for field in self.fields:
            select_fields.append(self.fields[field].validation_alias)
        if not select_fields:
            return ''
        return '$select=' + ','.join(select_fields)

    def build_filter(self) -> str:
        """Generates the "$select" query parameter."""
        conditions = []
        for field, lookup, value, notation in self._filters:
            conditions.append(Lookup.build(field, lookup, value, notation))
        if not conditions:
            return ''
        return '$filter=' + ' and '.join(conditions)

    def build_query_params(self) -> str:
        query_params = [p for p
                        in (self.build_select(), self.build_filter()) if p]
        if not query_params:
            return ''
        return f'?{'&'.join(query_params)}'
