"""API v1 router"""
from fastapi import APIRouter
from app.api.v1.endpoints import chat, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(chat.router, tags=["Chat"])
