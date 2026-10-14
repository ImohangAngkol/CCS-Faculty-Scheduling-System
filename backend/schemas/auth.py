from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=254)
    password: SecretStr = Field(max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        value = value.strip().lower()
        if not value or any(character.isspace() for character in value):
            raise ValueError("Use a username or institutional email without spaces.")
        return value


class CreateAccount(LoginInput):
    role: Literal["admin", "faculty"]
    faculty_id: UUID | None = None


class UpdateAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: StrictBool | None = None
    role: Literal["admin", "faculty"] | None = None
    faculty_id: UUID | None = None
    password: SecretStr | None = Field(default=None, max_length=1024)
