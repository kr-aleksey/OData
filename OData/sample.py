from OData.odata import OData, Q

from pydantic import BaseModel, Field

class FooSerializer(BaseModel):
    pass
    uid_1c: str = Field(validation_alias='Ref_Key',
                        max_length=36)
    name: str = Field(validation_alias='Description',
                      min_length=1,
                      max_length=200)
    width: int = Field(validation_alias='Ширина')
    length: int = Field(validation_alias='Длина')


class FooOdata(OData):
    serializer_class = FooSerializer

# odata = FooOdata().filter(uid_1c__in__guid=['123-456', '789-874'], width__gt=200, name='Foo')
# print(odata.build_query_params())

q = Q(Q(w=1), b='abc', a=123)
q2 = (Q(a=10, b='abc') | Q(c=50)) & Q(d__in=[50, 55])
print(q)
print(q2)
