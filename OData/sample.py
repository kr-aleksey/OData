from OData.odata import OData, Q

from pydantic import BaseModel, Field

# class FooSerializer(BaseModel):
#     pass
#     uid_1c: str = Field(validation_alias='Ref_Key',
#                         max_length=36)
#     name: str = Field(validation_alias='Description',
#                       min_length=1,
#                       max_length=200)
#     width: int = Field(validation_alias='Ширина')
#     length: int = Field(validation_alias='Длина')

class FooSerializer(BaseModel):
    a: int = Field()
    b: int = Field(validation_alias='Фуу')
    c: int = Field(validation_alias='Bar')
    d: int = Field()

class FooOdata(OData):
    serializer_class = FooSerializer
    pass




# q = (Q(a=10) | Q(c=10)) & ~Q(d=20)
# q = (~Q(d=20) | ~Q(c='abc')) & Q(b__eq__guid='123-321')
# q = Q(Q(a=10))
q = ~Q(c=10) & ~Q(d=20)


odata = FooOdata().filter(q)
print(odata.build_filter())