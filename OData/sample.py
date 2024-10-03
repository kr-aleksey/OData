from decimal import Decimal
from pprint import pprint
from typing import List

from pydantic import BaseModel, Field, TypeAdapter

from OData.odata import ODataManager, ODataModel, Q
from OData.connection import Connection, auth


class ProductsModel(BaseModel):
    uid_1c: str = Field(alias='Номенклатура_Key',
                        # validation_alias='Номенклатура_Key',
                        # alias='uid_1c',
                        # serialization_alias='Номенклатура_Key',
                        max_length=36)
    # quantity: Decimal = Field(validation_alias='Количество')

# deserialize
ext_data = {'Номенклатура_Key': 'abc'}
data = ProductsModel(**ext_data)
print(data.model_dump())

# serialize
data = ProductsModel.model_construct(uid_1c='vcbv')
print(data.model_dump(by_alias=True))
# print()
pass


class StageModel(BaseModel):
    pass
    uid_1c: str = Field(validation_alias='Ref_Key',
                        max_length=36)
    number: str = Field(validation_alias='Number',
                        min_length=1,
                        max_length=200)
    status: str = Field(validation_alias='Статус',)
    products: List[ProductsModel] = Field(alias='asd',
                                          validation_alias='ВыходныеИзделия')

s = StageModel.model_construct()
pass

class StageOdataModel(ODataModel):
    entity_model = StageModel
    entity_name = 'Document_ЭтапПроизводства2_2'


conn = Connection('http://erp.polipak.local/',
                  'erp_dev',
                  auth.HTTPBasicAuth('pro2', 'dev'))
stages = StageOdataModel.manager(conn).top(5).all()



pass
# class FooOdata(ODataManager):
#      obj_model = StageModel
#      obj_name = 'Document_ЭтапПроизводства2_2'
#
#
# authentication = auth.HTTPBasicAuth('pro2', 'dev')
# conn = Connection('http://erp.polipak.local/', 'erp_dev', authentication)
# odata = FooOdata(connection=conn)
# guids = ['ddda9041-89a8-11ec-aa39-ac1f6bd30991',
#          '4ab2c2af-8a36-11ec-aa39-ac1f6bd30991']
# q = Q(uid_1c__in__guid=guids,status='Завершен')
# stages = odata.filter(uid_1c__in__guid=guids, status='Завершен')
# pprint(stages)

# q = (Q(a=10) | Q(c=10)) & ~Q(d=20)
# q = (~Q(d=20) | ~Q(c='abc')) & Q(b__eq__guid='123-321')
# q = Q(Q(a=10))
# q = ~Q(c=10) & ~Q(d=20)
#
#
# odata = FooOdata().filter(q)
# print(odata.build_filter())
