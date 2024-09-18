from OData.odata import OData

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

odata = FooOdata().filter(uid_1c__in__guid=['123-456', '789-874'], width__gt=200)
print(odata.build_query_params())
