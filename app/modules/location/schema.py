from pydantic import BaseModel, ConfigDict


class CountryResponse(BaseModel):
    id: str
    name: str
    iso2: str
    iso3: str
    phoneCode: str

    model_config = ConfigDict(from_attributes=True)


class StateResponse(BaseModel):
    id: str
    name: str
    stateCode: str
    countryId: str

    model_config = ConfigDict(from_attributes=True)


class CityResponse(BaseModel):
    id: str
    name: str
    stateId: str

    model_config = ConfigDict(from_attributes=True)