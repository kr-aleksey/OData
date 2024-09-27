from typing import Any, Callable, Type

from pydantic import BaseModel


class Q:
    """
    Q is a node of a tree graph. A node is a connection whose child
    nodes are either leaf nodes or other instances of the node.
    This code is partially based on Django code.
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

    def __iter__(self):
        children = []
        for child in self.children:
            if isinstance(child, Q):
                yield from child
            else:
                children.append(child)
        yield self.NOT if self.negated else '', self.connector, children


    def add(self, other) -> None:
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

    OPERATORS = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in')
    DEFAULT_OPERATOR = 'eq'
    ANNOTATIONS = ('guid', 'date')

    def __new__(cls, *args, **kwargs):
        assert hasattr(cls, 'serializer_class'), \
            f"Required attribute not defined {cls.__name__}.serializer_class'."
        return super().__new__(cls)

    def __init__(self):
        self.fields = self.serializer_class.model_fields
        self.select_fields: list[str] = []
        self._filter: None | Q = None

    def filter(self, *args, **kwargs) -> 'OData':
        """
        Request filtering.
        Example: filter(Q(a=1, b__gt), c__eq__in=[1, 2])
        :param args: Q objects.
        :param kwargs: Lookups.
        :return: self
        """

        self._filter = Q(*args, **kwargs)
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
        if self._filter is None:
            return ''
        result = ''
        children = []
        prev_conn = None
        connector = Q.AND
        for negated, connector, lookups in self._filter:
            conditions = []
            for lookup in lookups:
                conditions.append(self.build_lookup(lookup))
            if conditions:
                condition = f' {connector} '.join(conditions)
                if negated:
                    condition = f'{negated} ({condition})'
                children.append(condition)
            if prev_conn is not None and connector != prev_conn:
                if connector == Q.AND:
                    children = list(map(lambda x: f'({x})', children))
                result += f' {connector} '.join(children)
                children = []
                prev_conn = None
            else:
                prev_conn = connector
        if children:
            result += f' {connector} '.join(children)
        return result

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

    def build_lookup(self, lookup: str) -> str:
        field, operator, annotation, *_ = (
            *lookup[0].split('__', maxsplit=3),
            None,
            None
        )
        if field not in self.fields:
            raise KeyError(
                f"Field '{field}' not found. "
                f"Use one of {list(self.fields.keys())}"
            )
        field = field or self.fields[field].annotation
        operator = operator or self.DEFAULT_OPERATOR
        if operator not in self.OPERATORS:
            raise KeyError(
                f"Unsupported operator {operator} ({operator[0]}). "
                f"Use one of {self.OPERATORS}."
            )
        return self.get_lookup_builder(operator)(field, lookup[1], annotation)


    def get_lookup_builder(self, lookup: str) -> Callable:
        if lookup == 'in':
            return self.in_builder
        return lambda field, value, annotation: \
            (f'{field} {lookup} '
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
        items = [f'{field} eq {self.annotate_value(field, v, annotation)}'
                 for v in value]
        return ' or '.join(items)
