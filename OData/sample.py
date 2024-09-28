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
    c: int = Field()
    d: int = Field()

class FooOdata(OData):
    serializer_class = FooSerializer
    pass



# q = Q(a=1) | ~Q(b=0)
# q2 =  (Q(a=1, e=33) | Q(b=0)) & (Q(j=0) | Q(c=1)) & ~(Q(z=0) | Q(y=1))
# for i in q2.flatten():
#     print(i)
# pass

# q2 = (Q(a=10, b='abc') | Q(c=50)) & Q(d__in=[50, 55])
# print(repr(q))
# pass
# print(q2)

def print_flatten(q):
    for i in q:
        print(i)
    print()

q1 = Q(a='1') & Q(b=2) | Q(c=3) & Q(d=4)
q2 = Q(q1, a=1) | Q(b=2) & Q(c=3) | Q(d=4)
q3 = ((Q(a=1) | Q(b=2)) & (Q(c=3) | Q(d__ne=4)))


print_flatten(q1)
print_flatten(q2)
print_flatten(q3)
q = Q(a=10, b__lt__gt=20) | Q(c=10) & ~Q(d=20)
odata = FooOdata().filter(q)
print(odata.build_filter())