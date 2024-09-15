from typing import Any, Type

from pydantic import BaseModel

COMPARISON_OPERATORS = ['eq',  'ne', 'gt', 'ge', 'lt', 'le']
DEFAULT_COMPARISON_OPERATOR = 'eq'

class OData:
    serializer_class: Type[BaseModel]

    def __new__(cls):
        assert hasattr(cls, 'serializer_class'), \
            f"Не задан обязательный атрибут {cls.__name__}.serializer_class'."
        return super().__new__(cls)

    def __init__(self):
        self.fields = self.serializer_class.model_fields
        self.select_fields: list[str] = []
        self._filters: list[tuple[str, str, Any]] = []

    def filter(self, **kwargs):
        """
        Фильтр odata запроса.
        Принимает параметры фильтрации - lookups в стиле Django ORM.
        В качестве имен параметров фильтрации используйте имена полей
        self.serializer_class.
        Параметры фильтрации объединяются пока только по and.
        Пример:
            filter(foo='Строка' , bar__gt=20)
        """
        for lookup, value in kwargs.items():
            field_operator = lookup.split('__', maxsplit=1)

            if len(field_operator) == 1:
                field_operator.append(DEFAULT_COMPARISON_OPERATOR)
            field, operator = field_operator

            if field not in self.fields:
                raise TypeError(
                    f"Ошибка в аргументе '{lookup}. "
                    f"Поле '{field}' нет среди "
                    f"{self.fields.keys()}"
                )

            if operator not in COMPARISON_OPERATORS:
                raise TypeError(
                    f"Ошибка в аргумент '{lookup}'. "
                    f"Оператора '{operator}' нет среди поддерживаемых: "
                    f"{COMPARISON_OPERATORS}."
                )

            self._filters.append((field, operator, value))
        return self

    def build_select(self) -> str:
        """Формирует параметр odata запроса $select."""
        select_fields = []
        for field in self.fields:
            select_fields.append(self.fields[field].validation_alias)
        if not select_fields:
            return ''
        return '$select=' + ','.join(select_fields)

    def build_filter(self) -> str:
        """Формирует параметр запроса $filter."""
        conditions = []
        for field, operator, value in self._filters:
            conditions.append(
                f'{self.fields[field].validation_alias} {operator} {value}')
        if not conditions:
            return ''
        return '$filter=' + ' and '.join(conditions)

    def build_query_params(self) -> str:
        query_params = [self.build_select(), self.build_filter()]
        if not query_params:
            return ''
        return f'?{'&'.join(query_params)}'
