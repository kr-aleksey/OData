from typing import Any, Callable, Type

from pydantic import BaseModel, Field


# class Q:
#     """
#     Encapsulates filters as objects that can be logically
#     combined using `&` and `|`.
#     """
#     AND: str = "AND"
#     OR: str = "OR"
#
#     left: Optional['Q'] = None
#     right: Optional['Q'] = None
#     connector: str | None = None
#
#     def __init__(self, *args, **kwargs) -> None:
#         self.args = args
#         self.kwargs: dict[str, Any] = kwargs
#
#     def __or__(self, other: 'Q') -> 'Q':
#         return self._create(left=self, right=other, connector=self.OR)
#
#     def __and__(self, other: 'Q') -> 'Q':
#         return self._create(left=self, right=other, connector=self.AND)
#
#     def __str__(self) -> str:
#         def build(q: 'Q') -> tuple[str, str]:
#             if q.connector is None:
#                 return (f' {self.AND} '.join(
#                             f'{k}={v}' for k, v in q.kwargs.items()),
#                         self.AND)
#             left, left_connector = build(q.left)
#             right, right_connector = build(q.right)
#             if q.connector == self.AND:
#                 if left_connector == self.OR:
#                     left = f'({left})'
#                 if right_connector == self.OR:
#                     right = f'({right})'
#             return f'{left} {q.connector} {right}', q.connector
#         return build(self)[0]
#
#     @classmethod
#     def _create(cls, left: 'Q' , right: 'Q', connector: str) -> 'Q':
#         q = cls()
#         q.left = left
#         q.right = right
#         q.connector = connector
#         return q

class Q:
    """
    Q is a node of a tree graph.
    A single internal node in the tree graph. A node should be
    thought of as a connection (root) whose children are either
    leaf nodes or other instances of the node.
    """

    AND = 'and'
    OR = 'or'
    NOT = 'not'

    arg_error_msg = 'The positional argument must be a Q object. Received {}.'

    def __new__(cls, *args, **kwargs):
        """
        Creates a Q object with kwargs leaf. Combines the created
        Q object with the objects passed via positional arguments
        using &. Returns the resulting Q object.
        q = Q(Q(a=1) | Q(b=0) , Q(c=1) , e=2) equivalent
        q2 = Q(e=2) & (Q(a=1) | Q(b=0)) & Q(c=1)
        :param args: Q objects.
        :param kwargs: Lookups.
        """
        if args:
            cls.check_args_type(args)
            child = args[0]
            for arg in args[1:]:
                child &= arg

        obj = super().__new__(cls)
        obj.children = [*kwargs.items()]
        obj.connector = Q.AND
        obj.negated = False
        for child in args:
            obj &= child
        return obj

    @classmethod
    def check_args_type(cls, args: tuple) -> None:
        for arg in args:
            if not isinstance(arg, Q):
                raise TypeError(cls.arg_error_msg.format(type(arg)))

    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            raise AttributeError('No arguments given')

    @classmethod
    def create(cls, children=None, connector=None, negated=False):
        obj = cls.__new__(cls)
        obj.children = children.copy() if children else []
        obj.connector = connector if connector is not None else connector
        obj.negated = negated
        return obj

    def __str__(self) -> str:
        child_strs = []
        for child in self.children:
            if (self.connector == Q.AND
                    and isinstance(child, Q)
                    and not child.negated):
                child_strs.append(f'({child})')
            else:
                child_strs.append(f'{child}')
        result = f' {self.connector} '.join(child_strs)
        if self.negated:
            return f'{self.NOT} ({result})'
        return result

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self}>'


    def __copy__(self):
        return self.create(children=self.children,
                           connector=self.connector,
                           negated=self.negated)

    copy = __copy__

    def __or__(self, other):
        return self.combine(other=other, connector=self.OR)

    def __and__(self, other):
        return self.combine(other=other, connector=self.AND)

    def __invert__(self):
        obj = self.copy()
        obj.negated = not self.negated
        return obj

    def add(self, other) -> None:
        # if self.connector != connector:
        #     self.connector = connector
        #     self.children = [self.copy(), other]
        # elif (not other.negated
        #       and (other.connector == connector or len(other.children) == 1)):
        #     self.children.extend(other.children)
        if not other.negated and (
                self.connector == other.connector or len(other.children) == 1):
            self.children.extend(other.children)
        else:
            self.children.append(other)

    def combine(self, other, connector):
        if not self.children:
            return other.copy()

        obj = self.create(connector=connector)
        obj.add(self)
        obj.add(other)
        return obj


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
