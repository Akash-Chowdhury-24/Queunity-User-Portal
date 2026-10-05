from pydantic import BaseModel, EmailStr


class TokenPayload(BaseModel):
  id : str
  role : str
  email : EmailStr
  above8Years : bool