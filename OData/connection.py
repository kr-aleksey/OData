from http import HTTPStatus
from typing import Any, Callable
from urllib.parse import quote, urlencode

import requests
import requests.auth as auth
import requests.exceptions as r_exceptions

from OData.exeptions import ODataError, ResponseError


class Connection:
    entity_list_json_key = 'value'
    odata_url_postfix = 'odata/standard.odata/'
    url_quote: Callable = quote

    def __init__(self,
                 url: str,
                 database: str,
                 authentication: auth.AuthBase,
                 connect_timeout: int | float = 10,
                 read_timeout: int | float = 121) -> None:
        self.url = f'{url}/{database}/odata/standard.odata/'
        self.timeout = (connect_timeout, read_timeout)
        self.session = requests.Session()
        self.session.auth = authentication
        self.session.headers.update(
            {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                # 'Connection': 'keep-alive'
            }
        )

    def __del__(self):
        self.session.close()

    def request(self,
                method: str,
                entity_name: str,
                guid: str | None = None,
                data: dict[str, Any] | None = None,
                query_params: dict[str, Any] | None = None
                ) -> requests.Response:
        url = self._get_url(entity_name, guid=guid, query_params=query_params)
        req = requests.Request(method, url, data=data)
        prep = self.session.prepare_request(req)
        return self.session.send(prep, timeout=self.timeout)

    def _get_url(self,
                 entity_name: str,
                 *,
                 guid: str | None = None,
                 query_params: dict[str, Any] | None = None
                 ) -> str:
        url = f'{self.url}{entity_name}'
        if guid is not None:
            url += f"(guid'{guid}')"
        if query_params:
            url += f'?{urlencode(query_params, quote_via=quote)}'
        return url

    @staticmethod
    def _decode_response(response: requests.Response,
                         ok_status: int) -> dict[str, Any]:
        if response.status_code != ok_status:
            raise ResponseError(response.status_code,
                                response.reason,
                                response.text)
        try:
            data = response.json()
        except r_exceptions.JSONDecodeError as e:
            raise ODataError(e)
        return data

    def create(self,
               entity_name: str,
               data: dict[str, Any],
               query_params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Creating an object by guid."""
        response = self.request('POST',
                                entity_name,
                                data=data,
                                query_params=query_params)
        return self._decode_response(response, HTTPStatus.CREATED)

    def get(self,
            entity_name: str,
            guid: str,
            query_params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Getting an object by guid."""
        response = self.request('GET',
                                entity_name,
                                guid=guid,
                                query_params=query_params)
        return self._decode_response(response, HTTPStatus.OK)

    def list(self,
             entity_name: str,
             query_params: dict[str, Any] | None = None) -> list[Any]:
        """Getting a list of objects."""
        response = self.request('GET',
                                entity_name,
                                query_params=query_params)
        try:
            data: dict[str, Any] = self._decode_response(response,
                                                         HTTPStatus.OK)
            objects: list[Any] = data[self.entity_list_json_key]
            assert type(objects) is list
        except (AssertionError, KeyError):
            raise ODataError(f'Response does not contain entity list. '
                             f'Response: {response.text}')
        return objects

    def delete(self,
               entity_name: str,
               guid: str,
               query_params: dict[str, Any] | None = None):
        """Deleting an object by guid."""
        response = self.request('DELETE',
                                entity_name,
                                guid=guid,
                                query_params=query_params)
        return self._decode_response(response, HTTPStatus.NO_CONTENT)

    def patch(self,
              entity_name: str,
              guid: str,
              data: dict[str, Any],
              query_params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Updating an object by guid."""
        response = self.request('PATCH',
                                entity_name,
                                guid=guid,
                                data=data,
                                query_params=query_params)
        return self._decode_response(response, HTTPStatus.OK)
