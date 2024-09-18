from typing import Any, Callable, Type

from pydantic import BaseModel, Field


class OData:
    serializer_class: Type[BaseModel]

    LOOKUPS = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in')
    DEFAULT_LOOKUP = 'eq'
    NOTATIONS = ('guid', 'date')

    def __new__(cls, *args, **kwargs):
        assert hasattr(cls, 'serializer_class'), \
            f"Required attribute not defined {cls.__name__}.serializer_class'."
        return super().__new__(cls)

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
                field_lookup.extend([self.DEFAULT_LOOKUP, None])
            elif len(field_lookup) == 2:
                field_lookup.append(None)
            field, lookup, notation = field_lookup

            if field not in self.fields:
                raise KeyError(
                    f"Field '{field_lookup[0]}' not found. "
                    f"Use one of {list(self.fields.keys())}"
                )
            self._filters.append((field, lookup, value, notation))

            if lookup not in self.LOOKUPS:
                raise TypeError(
                    f"Unsupported lookup {lookup}. Use one of {self.LOOKUPS}.")
        return self

    def build_query_params(self) -> str:
        query_params = [p for p
                        in (self.build_select(), self.build_filter())
                        if p]
        if not query_params:
            return ''
        return f'?{'&'.join(query_params)}'

    def build_select(self) -> str:
        """Generates the "$select" query parameter."""
        select_fields = []
        for field in self.fields:
            select_fields.append(self.fields[field].validation_alias)
        if not select_fields:
            return ''
        return '$select=' + ','.join(select_fields)

    def build_filter(self) -> str:
        """Generates the "$filter" query parameter."""
        conditions = []
        for field, lookup, value, notation in self._filters:
            lookup_builder = self.get_lookup_builder(lookup)
            notation_func = self.get_notation_func(notation)
            alias = self.fields[field].validation_alias

            conditions.append(lookup_builder(alias, value, notation_func))
        if not conditions:
            return ''
        return '$filter=' + ' and '.join(conditions)

    """Lookups."""

    def get_lookup_builder(self, lookup: str) -> Callable:
        if lookup == 'in':
            return self.in_builder
        return lambda field_alias, value, notation_func: \
            f'{field_alias} {lookup} {notation_func(value)}'

    @staticmethod
    def in_builder(field_alias: str,
                   value: Any,
                   notation: callable) -> str:
        """
        :param field_alias: Field validation_alias.
        :param value: Value.
        :param notation: Notation func.
        Converts lookup 'in' to an Odata filter parameter.
        For example: 'foo eq value or foo_alias eq value2 ...'
        """
        items = [f'{field_alias} eq {notation(v)}' for v in value]
        return ' or '.join(items)

    """Notations."""

    def get_notation_func(self, notation: str | None) -> Callable[[Any], str]:
        if notation is None:
            return lambda value: str(value)
        if notation not in self.NOTATIONS:
            raise TypeError(f"Unsupported notation {notation}."
                            f" Use one of {self.NOTATIONS}.")
        return lambda value: f"{notation}'{value}'"
