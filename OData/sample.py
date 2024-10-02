from decimal import Decimal
from pprint import pprint

from pydantic import BaseModel, Field

from OData.odata import OData, Q
from OData.connection import Connection, auth


# conn.session.close()
#
#
# data = conn.list('Document_ЭтапПроизводства2_2',
#                  {'$top': 2, '$select': 'Number,Ref_Key'})
# print(data)
#
# data = conn.get('Document_ЭтапПроизводства2_2',
#                 'f75e2f51-6c60-11ec-aa38-ac1f6bd30991',
#                 {'$select': 'Number, Ref_Key'})
# print(data)

class ProductsModel(BaseModel):
    uid_1c: str = Field(validation_alias='Номенклатура_Key',
                        max_length=36)
    quantity: Decimal = Field(validation_alias='Количество')

class StageModel(BaseModel):
    pass
    uid_1c: str = Field(validation_alias='Ref_Key',
                        max_length=36)
    number: str = Field(validation_alias='Number',
                        min_length=1,
                        max_length=200)
    status: str = Field(validation_alias='Статус',)
    products: ProductsModel = Field(validation_alias='ВыходныеИзделия')


class FooOdata(OData):
     obj_model = StageModel
     obj_name = 'Document_ЭтапПроизводства2_2'


authentication = auth.HTTPBasicAuth('pro2', 'dev')
conn = Connection('http://erp.polipak.local/', 'erp_dev', authentication)
odata = FooOdata(connection=conn)
guids = ['ddda9041-89a8-11ec-aa39-ac1f6bd30991',
         '4ab2c2af-8a36-11ec-aa39-ac1f6bd30991']
q = Q(uid_1c__in__guid=guids,status='Завершен')
stages = odata.filter(uid_1c__in__guid=guids, status='Завершен')
pprint(stages)

# q = (Q(a=10) | Q(c=10)) & ~Q(d=20)
# q = (~Q(d=20) | ~Q(c='abc')) & Q(b__eq__guid='123-321')
# q = Q(Q(a=10))
# q = ~Q(c=10) & ~Q(d=20)
#
#
# odata = FooOdata().filter(q)
# print(odata.build_filter())
