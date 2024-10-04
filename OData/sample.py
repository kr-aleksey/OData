from decimal import Decimal
from pprint import pprint
from typing import ClassVar

from pydantic import BaseModel, Field

from OData.connection import Connection, auth
from OData.odata import ODataModel


# # deserialize
# ext_data = {'Номенклатура_Key': 'abc'}
# data = ProductsModel(**ext_data)
# print(data.model_dump())
#
# # serialize
# data = ProductsModel.model_construct(uid_1c='vcbv')
# print(data.model_dump(by_alias=True))
# print()

class ProductModel(BaseModel):
    uid_1c: str = Field(alias='Номенклатура_Key',
                        max_length=36)
    quantity: Decimal = Field(alias='Количество')

class StageModel(BaseModel):
    uid_1c: str = Field(alias='Ref_Key',
                        max_length=36)
    number: str = Field(alias='Number',
                        min_length=1,
                        max_length=200)
    status: str = Field(alias='Статус', )
    products: list[ProductModel] = Field(alias='ВыходныеИзделия')

    nested_models: ClassVar = {
        'products': ProductModel,
    }


class StageOdataModel(ODataModel):
    entity_model = StageModel
    entity_name = 'Document_ЭтапПроизводства2_2'


conn = Connection('http://erp.polipak.local/',
                  'erp_dev',
                  auth.HTTPBasicAuth('pro2', 'dev'))

guids = ['ddda9041-89a8-11ec-aa39-ac1f6bd30991',
         '4ab2c2af-8a36-11ec-aa39-ac1f6bd30991']
stages: list[BaseModel] = (StageOdataModel
                           .manager(conn)
                           # .filter(uid_1c__in__guid=guids, status='Начат')
                           .top(5)
                           .all())

for stage in stages:
    pprint(stage.model_dump())
