from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import hcps, interactions, chat

app = FastAPI(
    title="HCP CRM - Log Interaction API",
    description="Backend for the Healthcare Professional (HCP) interaction "
                 "logging module. Structured-form and conversational-chat "
                 "entry points both flow through the same LangGraph agent "
                 "tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only; restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hcps.router)
app.include_router(interactions.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "hcp-crm-backend"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}
