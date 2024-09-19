from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, Field


class Q:
    """
    Encapsulates filters as objects that can be logically
    combined using `&` and `|`.
    """
    AND: str = "AND"
    OR: str = "OR"

    left: Optional['Q'] = None
    right: Optional['Q'] = None
    connector: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs: dict[str, Any] = kwargs

    def __or__(self, other: 'Q') -> 'Q':
        return self._create(left=self, right=other, connector=self.OR)

    def __and__(self, other: 'Q') -> 'Q':
        return self._create(left=self, right=other, connector=self.AND)

    def __str__(self) -> str:
        def build(q: 'Q') -> tuple[str, str]:
            if q.connector is None:
                return (f' {self.AND} '.join(
                            f'{k}={v}' for k, v in q.kwargs.items()),
                        self.AND)
            left, left_connector = build(q.left)
            right, right_connector = build(q.right)
            if q.connector == self.AND:
                if left_connector == self.OR:
                    left = f'({left})'
                if right_connector == self.OR:
                    right = f'({right})'
            return f'{left} {q.connector} {right}', q.connector
        return build(self)[0]

    @classmethod
    def _create(cls, left: 'Q' , right: 'Q', connector: str) -> 'Q':
        q = cls()
        q.left = left
        q.right = right
        q.connector = connector
        return q


class OData:
    serializer_class: Type[BaseModel]

    LOOKUPS = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in')
    DEFAULT_LOOKUP = 'eq'
    ANNOTATIONS = ('guid', 'date')

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
            filter(Q(baz='a'), foo='b' , bar__gt=20, uid__in__guid = ['',])
        """
        for key, value in kwargs.items():
            field_lookup: list[str | None] = key.split('__', maxsplit=3)
            if len(field_lookup) == 1:
                field_lookup.extend([self.DEFAULT_LOOKUP, None])
            elif len(field_lookup) == 2:
                field_lookup.append(None)
            field, lookup, annotation = field_lookup

            if field not in self.fields:
                raise KeyError(
                    f"Field '{field_lookup[0]}' not found. "
                    f"Use one of {list(self.fields.keys())}"
                )
            self._filters.append((field, lookup, value, annotation))

            if lookup not in self.LOOKUPS:
                raise TypeError(
                    f"Unsupported lookup {lookup}. Use one of {self.LOOKUPS}.")

            if annotation is not None and annotation not in self.ANNOTATIONS:
                raise TypeError(f"Unsupported annotation {annotation}."
                                f" Use one of {self.ANNOTATIONS}.")
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
        for field, lookup, value, annotation in self._filters:
            lookup_builder = self.get_lookup_builder(lookup)
            conditions.append(lookup_builder(field, value, annotation))
        if not conditions:
            return ''
        return '$filter=' + ' and '.join(conditions)

    def annotate_value(self,
                       field: str,
                       value: Any,
                       annotation: str | None) -> str:
        if annotation is not None:
            return f"{annotation}'{value}'"

        field_type = self.fields[field].annotation
        if field_type is str:
            return f"'{value}'"
        return str(value)

    """Lookups."""

    def get_lookup_builder(self, lookup: str) -> Callable:
        if lookup == 'in':
            return self.in_builder
        return lambda field, value, annotation: \
            (f'{self.fields[field].validation_alias} {lookup} '
             f'{self.annotate_value(field, value, annotation)}')

    def in_builder(self,
                   field: str,
                   value: Any,
                   annotation: str | None) -> str:
        """
        :param field: Field name.
        :param value: Value.
        :param annotation: Annotation.
        Converts lookup 'in' to an Odata filter parameter.
        For example: 'foo eq value or foo_alias eq value2 ...'
        """
        alias = self.fields[field].validation_alias
        items = [f'{alias} eq {self.annotate_value(field, v, annotation)}'
                 for v in value]
        return ' or '.join(items)
