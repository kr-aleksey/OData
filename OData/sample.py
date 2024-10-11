from decimal import Decimal
from pprint import pprint

from pydantic import BaseModel, Field

from OData.http import Connection, auth
from OData.odata import OData, OdataModel


# # deserialize
# ext_data = {'Номенклатура_Key': 'abc'}
# data = ProductsModel(**ext_data)
# print(data.model_dump())
#
# # serialize
# data = ProductsModel.model_construct(uid_1c='abc-def')
# print(data.model_dump(by_alias=True))
# print()

class ProductModel(OdataModel):
    uid_1c: str = Field(alias='Номенклатура_Key',
                        max_length=36)
    quantity: Decimal = Field(alias='Количество')


class StageModel(OdataModel):
    uid_1c: str = Field(alias='Ref_Key',
                        max_length=36,
                        exclude=True)
    number: str = Field(alias='Number',
                        min_length=1,
                        max_length=200)
    status: str = Field(alias='Статус', )
    products: list[ProductModel] = Field(alias='ВыходныеИзделия', exclude=True)

    nested_models = {
        'products': ProductModel,
    }


class StageOdata(OData):
    database = 'erp_dev'
    entity_model = StageModel
    entity_name = 'Document_ЭтапПроизводства2_2'


# conn = Connection('erp.polipak.local',
#                   'http',
#                   auth.HTTPBasicAuth('pro2', 'dev'))

guids = ['ddda9041-89a8-11ec-aa39-ac1f6bd30991',
         '4ab2c2af-8a36-11ec-aa39-ac1f6bd30991']
# manager = StageOdata.manager(conn)

with Connection('erp.polipak.local',
                'http',
                auth.HTTPBasicAuth('pro2', 'dev')) as conn:
    manager = StageOdata.manager(conn)
    stages: list[BaseModel] = (manager
                               .filter(uid_1c__in__guid=guids, status='Начат')
                               .top(5)
                               .all())
    pprint(stages)
    stage = manager.get(guid='ce52f328-3f1d-11ed-aa45-ac1f6bd30990')
    pprint(stage)
    stage.number = 'ПП00-5729.3.1.55'
    stage = manager.update(stage.uid_1c, stage)
    pprint(stage)


# conn = Connection('erp.polipak.local',
#                   'http',
#                   auth.HTTPBasicAuth('pro2', 'dev'))
# stage = StageOdata.manager(conn).top(3).all()
# print(stage)

# stages = manager.filter(number='ПП00-4311.9.1').all()
# stage = manager.get(guid='2ab4367f-58a5-11ee-aa67-ac1f6bd30991')
# pprint(stage)
# stage.number = 'ПП00-4311.9.1.1'
# result = manager.update(stage.uid_1c, data=stage)
# # for stage in stages:
# pprint(stage)
