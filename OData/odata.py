from http import HTTPStatus
from typing import Any, Callable, ClassVar, Optional, Type
from urllib.parse import quote, urlencode

import requests
import requests.exceptions as r_exceptions
from pydantic import BaseModel, ValidationError
from requests import Response

from OData.exeptions import ODataError, ResponseError
from OData.http import Connection


class OdataModel(BaseModel):
    """
    Data model for serialization, deserialization and validation.
    The nested_models attribute is used to optimize the query.
    If nested_models is None, all fields of nested entities will
    be requested, regardless of their presence in the nested model.
    """
    nested_models: ClassVar[Optional[dict[str, BaseModel]]] = None


class OData:
    database: str
    entity_model: Type[OdataModel]
    entity_name: str

    _err_msg: str = "Required attribute not defined: {}."

    @classmethod
    def manager(cls, connection: Connection) -> 'ODataManager':
        """Returns an instance of the model manager."""
        assert hasattr(cls, 'entity_model'), (
            cls._err_msg.format(f'{cls.__name__}.entity_model'))
        assert hasattr(cls, 'entity_name'), (
            cls._err_msg.format(f'{cls.__name__}.entity_name'))
        return ODataManager(odata_class=cls, connection=connection)


class Q:
    """
    Q is a node of a tree graph. A node is a connection whose child
    nodes are either leaf nodes or other instances of the node.
    This code is partially based on Django code.
    """

    AND = 'and'
    OR = 'or'
    NOT = 'not'

    OPERATORS = ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'in')
    DEFAULT_OPERATOR = 'eq'
    ANNOTATIONS = ('guid', 'date')

    arg_error_msg = 'The positional argument must be a Q object. Received {}.'

    def __new__(cls, *args: 'Q', **kwargs: Any):
        """
        Creates a Q object with kwargs leaf. Combines the created
        Q object with the objects passed via positional arguments
        using &. Returns the resulting Q object.
        :param args: Q objects.
        :param kwargs: Lookups.
        """
        obj = super().__new__(cls)
        children = []
        for key, value in kwargs.items():
            _, lookup, *_ = *key.split('__'), None
            if lookup == 'in':
                children.append(
                    cls.create(children=[(key, value)], connector=Q.OR))
            else:
                children.append((key, value))
        obj.children = children
        obj.connector = Q.AND
        obj.negated = False

        for arg in args:
            if not isinstance(arg, Q):
                raise TypeError(cls.arg_error_msg.format(type(arg)))
            obj &= arg

        return obj

    def __init__(self, *args: 'Q', **kwargs: Any):
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
        return self.build_expression()

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
        if self.connector != other.connector or other.negated:
            self.children.append(other)
        else:
            self.children.extend(other.children)

    def combine(self, other, connector):
        obj = self.create(connector=connector)
        obj.add(self)
        obj.add(other)
        return obj

    def build_expression(self,
                         field_mapping: dict[str, str] | None = None) -> str:
        """
        Recursively iterates over child elements. Builds an expression
        taking into account the priorities of the operations.
        The field_mapping argument is used to map the field name
        to the OData field name.
        :param field_mapping: {field_name: alias}
        :return: Full filter expression.
        """
        child_expressions: list[str] = []
        for child in self.children:
            if isinstance(child, Q):
                child_expression: str = child.build_expression(field_mapping)
                if self.connector == Q.AND and child.connector == Q.OR:
                    child_expression: str = f'({child_expression})'
            else:
                child_expression: str = self._build_lookup(child,
                                                           field_mapping)
            child_expressions.append(child_expression)
        expression = f' {self.connector} '.join(child_expressions)
        if self.negated:
            expression = f'{self.NOT} ({expression})'
        return expression

    def _build_lookup(self,
                      lookup: tuple[str, Any],
                      field_mapping: dict[str, str] | None = None) -> str:
        """
        Builds a lookup to a filter expression.
        :param lookup: (key, value)
        :param field_mapping: {field_name: alias}
        :return: Expression. For example: "Name eq 'Ivanov'"
        """
        field, operator, annotation, *_ = (
            *lookup[0].split('__', maxsplit=3),
            None,
            None
        )
        if field_mapping is not None:
            if field not in field_mapping:
                raise KeyError(
                    f"Field '{field}' not found. "
                    f"Use one of {list(field_mapping.keys())}"
                )
            field = field_mapping.get(field) or field
        operator = operator or self.DEFAULT_OPERATOR
        if operator not in self.OPERATORS:
            raise KeyError(
                f"Unsupported operator {operator} ({lookup[0]}). "
                f"Use one of {self.OPERATORS}."
            )
        return self._get_lookup_builder(operator)(field, lookup[1], annotation)

    def _get_lookup_builder(self, lookup: str) -> Callable:
        if lookup == 'in':
            return self._in_builder
        return lambda field, value, annotation: \
            f'{field} {lookup} {self._annotate_value(value, annotation)}'

    def _in_builder(self,
                    field: str,
                    value: Any,
                    annotation: str | None) -> str:
        """
        :param field: Field name.
        :param value: Value.
        :param annotation: Annotation.
        Converts lookup 'in' to an Odata filter parameter.
        For example: 'foo eq value or foo eq value2 ...'
        """
        items = [f'{field} eq {self._annotate_value(v, annotation)}'
                 for v in value]
        return ' or '.join(items)

    def _annotate_value(self,
                        value: Any,
                        annotation: str | None) -> str:
        """
        :param value: Value to annotate.
        :param annotation: Annotation ('guid', 'date', etc ).
        :return: Annotated value. For example: guid'123'.
        """
        if annotation is not None:
            if annotation not in self.ANNOTATIONS:
                raise KeyError(
                    f"Unknown annotation {annotation}. "
                    f"Use one of {self.ANNOTATIONS}"
                )
            return f"{annotation}'{value}'"

        if isinstance(value, str):
            return f"'{value}'"
        return str(value)


class ODataManager:

    odata_path = 'odata/standard.odata'
    odata_list_json_key = 'value'

    def __init__(self, odata_class: Type[OData], connection: Connection):
        self.odata_class = odata_class
        self.connection = connection
        self.request_data: dict[str, Any] | list[dict[str, Any]] | None = None
        self.response: Response | None = None
        self.validation_errors: dict[int, ValidationError] = {}
        self._filter: Q | None = None
        self._top: int | None = None

    def __str__(self):
        return f'{self.odata_class.__name__} manager'

    @property
    def relative_url(self) -> str:
        return (f'{self.odata_class.database}'
                f'/{self.odata_path}'
                f'/{self.odata_class.entity_name}')

    def get_canonical_url(self, guid: str):
        return f"{self.relative_url}(guid'{guid}'){self.get_query_params()}"

    def all(self, ignor_invalid: bool = False) -> list[OdataModel]:
        """Returns validated instances of the OdataModel class.
        If ignor_invalid = True, invalid objects will be skipped,
        errors will be accumulated in self.validation_errors.
        Otherwise, a pydantic.ValidationError exception will be raised."""
        self.request_data = None
        self.response = self.connection.request(
            method='GET',
            relative_url= self.relative_url + self.get_query_params()
        )

        try:
            objs: list[dict[str, Any]] = self.check_response(
                HTTPStatus.OK)[self.odata_list_json_key]
            validated_objs = []
        except KeyError:
            raise ODataError(
                f'Response json has no key {self.odata_list_json_key}'
            )

        self.validation_errors = {}
        for i, obj in enumerate(objs):
            try:
                validated_objs.append(self.odata_class.entity_model(**obj))
            except ValidationError as e:
                self.validation_errors[i] = e
                if not ignor_invalid:
                    raise e
        return validated_objs

    def get(self, guid: str) -> OdataModel:
        """Get an entity by guid."""
        self.request_data = None
        self.response = self.connection.request(
            method='GET',
            relative_url=self.get_canonical_url(guid)
        )
        data = self.check_response(HTTPStatus.OK)
        self.validation_errors = {}
        try:
            return self.odata_class.entity_model.model_validate(data)
        except ValidationError as e:
            self.validation_errors[0] = e
            raise e


    def update(self,
               guid: str,
               data: OdataModel | dict[str, Any]) -> OdataModel:
        """Updates (patch) an entity by guid."""
        if isinstance(data, OdataModel):
            self.request_data = data.model_dump(by_alias=True)
        else:
            self.request_data = data

        self.response = self.connection.request(
            method='PATCH',
            relative_url=self.get_canonical_url(guid),
            data=self.request_data
        )
        data = self.check_response(HTTPStatus.OK)
        try:
            return self.odata_class.entity_model.model_validate(data)
        except ValidationError as e:
            self.validation_errors[0] = e
            raise e

    # def make_posted(self,
    #                 guid: str,
    #                 operational_mode: bool = False) -> OdataModel:
    #
    #     self.response_data: dict[str, Any] = self.connection.post(
    #         entity_name=self.odata_class.entity_name,
    #         guid=guid,
    #     )

    def filter(self, *args, **kwargs):
        """
        Sets filtering conditions.
        Example: filter(Q(a=1, b__gt), c__in=[1, 2])
        :param args: Q objects.
        :param kwargs: Lookups.
        :return: self
        """
        q = Q(*args, **kwargs)
        if self._filter is not None:
            self._filter &= q
        else:
            self._filter = q
        return self

    def top(self, n: int):
        self._top = n
        return self

    def get_filter(self) -> str:
        fields = self.odata_class.entity_model.model_fields
        field_mapping = {f: i.alias for f, i in fields.items()}
        if self._filter is not None:
            return self._filter.build_expression(field_mapping)
        return ''

    def get_select(self) -> str:
        fields = self.odata_class.entity_model.model_fields
        nested_models = self.odata_class.entity_model.nested_models
        aliases = []
        for field, info in fields.items():
            alias = info.alias or field
            if nested_models is not None and field in nested_models:
                for nested_field, nested_info in nested_models[
                    field].model_fields.items():
                    nested_alias = nested_info.alias or nested_field
                    aliases.append(f'{alias}/{nested_alias}')
            else:
                aliases.append(alias)

        return ', '.join(aliases)

    def get_query_params(self) -> str:
        """Returns encoded query parameters."""
        query_params: dict[str, Any] = {}

        if self._top is not None:
            query_params['$top'] = self._top

        select_qp = self.get_select()
        if select_qp:
            query_params['$select'] = select_qp

        filter_qp = self.get_filter()
        if filter_qp:
            query_params['$filter'] = filter_qp

        if not query_params:
            return ''
        return f'?{urlencode(query_params, quote_via=quote)}'

    def check_response(self, ok_status: int) -> dict[str, Any]:
        if self.response.status_code != ok_status:
            raise ResponseError(self.response.status_code,
                                self.response.reason,
                                self.response.text)
        try:
            data = self.response.json()
        except r_exceptions.JSONDecodeError as e:
            raise ODataError(e)
        return data