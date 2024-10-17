from datetime import datetime
from decimal import Decimal
from pprint import pprint

from pydantic import Field

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


class NomenclatureTypeModel(OdataModel):
    uid_1c: str = Field(alias='Ref_Key', max_length=36, exclude=True)
    name: str = Field(alias='Description', max_length=200)


class MeasureUnitModel(OdataModel):
    uid_1c: str = Field(alias='Ref_Key', max_length=36, exclude=True)
    name: str = Field(alias='Description', max_length=6)


class NomenclatureModel(OdataModel):
    uid_1c: str = Field(alias='Ref_Key', max_length=36, exclude=True)
    code: str = Field(alias='Code', max_length=12)
    name: str = Field(alias='Description', max_length=200)
    nomenclature_type: NomenclatureTypeModel = Field(alias='ВидНоменклатуры')
    measure_unit: MeasureUnitModel = Field(alias='ЕдиницаИзмерения')

    nested_models = {
        'nomenclature_type': NomenclatureTypeModel,
        'measure_unit': MeasureUnitModel
    }


class NomenclatureOdata(OData):
    database = 'erp_dev'
    entity_model = NomenclatureModel
    entity_name = 'Catalog_Номенклатура'


# with Connection('erp.polipak.local',
#                 'http',
#                 auth.HTTPBasicAuth('pro2', 'dev')) as conn:
#     manager = NomenclatureOdata.manager(conn)
#     nomenclatures = (manager
#                      .expand(['nomenclature_type', 'measure_unit'])
#                      .filter(code='00-00028707')
#                      .all())


# pprint(dict(nomenclatures[0]))


class ProductModel(OdataModel):
    uid_1c: str = Field(alias='Номенклатура_Key',
                        max_length=36,
                        exclude=True)
    quantity: Decimal = Field(alias='Количество')


class StageModel(OdataModel):
    uid_1c: str = Field(alias='Ref_Key',
                        max_length=36,
                        exclude=True)
    number: str = Field(alias='Number',
                        min_length=1,
                        max_length=200)
    # date: datetime = Field(alias='Date')
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

# guids = ['ddda9041-89a8-11ec-aa39-ac1f6bd30991',
#          '4ab2c2af-8a36-11ec-aa39-ac1f6bd30991']

# with Connection('erp.polipak.local',
#                 'http',
#                 auth.HTTPBasicAuth('pro2', 'dev')) as conn:
#     manager = StageOdata.manager(conn)
#     # stages = (manager
#     #           # .filter(uid_1c__in__guid=guids, status='Начат')
#     #           # .filter(date__gt__datetime='2024-09-12T00:00:00')
#     #           .filter(date__gt=datetime(year=2024, month=1, day=12))
#     #           .top(5)
#     #           .skip(2)
#     #           .all())
#     # pprint(stages)
#     stage = manager.get(guid='4ab2c2af-8a36-11ec-aa39-ac1f6bd30991')
#     pprint(stage)
#     stage.number = 'ПП00-5729.3.1.5'
#     # stage.uid_1c = ''
#     stage = manager.update(stage.uid_1c, stage)
#     pprint(stage)
#     # stages = manager.filter(number='ПП00-813.1.1').all()
#     # print(stages)

conn = Connection('erp.polipak.local',
                  'http',
                  auth.HTTPBasicAuth('pro2', 'dev'))
stage = StageOdata.manager(conn).top(3).all()
print(stage)

# stages = manager.filter(number='ПП00-4311.9.1').all()
# stage = manager.get(guid='2ab4367f-58a5-11ee-aa67-ac1f6bd30991')
# pprint(stage)
# stage.number = 'ПП00-4311.9.1.1'
# result = manager.update(stage.uid_1c, data=stage)
# # for stage in stages:
# pprint(stage)
