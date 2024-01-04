import graphene


class Address(graphene.ObjectType):
    address_id = graphene.Int()
    address = graphene.String()


class StreamableERC20(graphene.ObjectType):
    token_address = graphene.String()
    is_pair = graphene.Boolean()
    total_supply = graphene.String()
    pair_token_0_address = graphene.String()
    pair_token_1_address = graphene.String()


class Balance(graphene.ObjectType):
    address = graphene.String()
    token_address = graphene.String()
    amount = graphene.String()


class Stream(graphene.ObjectType):
    stream_id = graphene.String()
    from_address = graphene.String()
    to_address = graphene.String()
    token_address = graphene.String()
    amount = graphene.String()
    start = graphene.Int()
    duration = graphene.Int()
    accrued = graphene.Boolean()
    swap_id = graphene.String()


class Swap(graphene.ObjectType):
    swap_id = graphene.String()
    pair_address = graphene.String()
    to_pair = graphene.Field(Stream)
    from_pair = graphene.Field(Stream)


class Cursor(graphene.ObjectType):
    cursor_id = graphene.Int()
    cursor = graphene.String()
