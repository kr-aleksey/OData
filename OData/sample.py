from pydantic import BaseModel, Field

from OData.odata import OData


class FooSerializer(BaseModel):
    uid_1c: str = Field(validation_alias='Ref_Key',
                        max_length=36)
    name: str = Field(validation_alias='Description',
                      min_length=1,
                      max_length=200)
    width: int = Field(validation_alias='Ширина')
    length: int = Field(validation_alias='Длина')


class FooOdata(OData):
    serializer_class = FooSerializer

odata = FooOdata().filter(width__gt=50, length=500)
print(odata.build_query_params())
