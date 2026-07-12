from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from contexts.chatbots.application.dtos import ChatbotView
from contexts.chatbots.application.use_cases import (
    CreateChatbot, DeleteChatbot, ListChatbots, UpdateChatbot)
from contexts.chatbots.domain.enums import Tone
from contexts.chatbots.infrastructure.repository import SqlAlchemyChatbotRepository
from sfplatform.db import get_session
from sfplatform.middleware import get_tenant_context
from shared.application.tenant_context import TenantContext

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


class CreateBody(BaseModel):
    name: str
    tone: Tone
    purpose: str = ""


class UpdateBody(BaseModel):
    name: str | None = None
    tone: Tone | None = None
    purpose: str | None = None


def _repo(session: Session) -> SqlAlchemyChatbotRepository:
    return SqlAlchemyChatbotRepository(session)


@router.post("", status_code=201)
def create(body: CreateBody, ctx: TenantContext = Depends(get_tenant_context),
           session: Session = Depends(get_session)) -> dict:
    bot = CreateChatbot(_repo(session)).execute(ctx, body.name, body.tone, body.purpose)
    session.commit()
    return ChatbotView.of(bot).__dict__


@router.get("")
def list_bots(ctx: TenantContext = Depends(get_tenant_context),
              session: Session = Depends(get_session)) -> list[dict]:
    bots = ListChatbots(_repo(session)).execute(ctx)
    return [ChatbotView.of(b).__dict__ for b in bots]


@router.put("/{chatbot_id}")
def update(chatbot_id: int, body: UpdateBody,
           ctx: TenantContext = Depends(get_tenant_context),
           session: Session = Depends(get_session)) -> dict:
    bot = UpdateChatbot(_repo(session)).execute(ctx, chatbot_id, body.name, body.tone, body.purpose)
    session.commit()
    return ChatbotView.of(bot).__dict__


@router.delete("/{chatbot_id}", status_code=204)
def delete(chatbot_id: int, ctx: TenantContext = Depends(get_tenant_context),
           session: Session = Depends(get_session)) -> Response:
    DeleteChatbot(_repo(session)).execute(ctx, chatbot_id)
    session.commit()
    return Response(status_code=204)
