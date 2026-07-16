from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    id: int
    username: str
    token: str
    refresh_token: str
    expires_in: int  # seconds until access token expires


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(BaseModel):
    token: str
    refresh_token: str
    expires_in: int


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    has_avatar: bool = False


class MeOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    has_avatar: bool = False


class UpdateMeIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)


class ChatCreateIn(BaseModel):
    type: str = Field(pattern="^(direct|group)$")
    title: str | None = Field(default=None, max_length=128)
    member_ids: list[int] = Field(default_factory=list)


class ChatOut(BaseModel):
    id: int
    type: str
    title: str | None
    created_by: int
    created_at: datetime


class MemberIn(BaseModel):
    user_id: int
    role: str = Field(default="writer", pattern="^(reader|writer|owner)$")


class SendMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    client_msg_id: UUID | None = None
    attachment_ids: list[int] = Field(default_factory=list)


class StatusOut(BaseModel):
    user_id: int
    status: str


class AttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    size_bytes: int


class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    created_at: datetime
    statuses: list[StatusOut] = Field(default_factory=list)
    attachments: list[AttachmentOut] = Field(default_factory=list)
