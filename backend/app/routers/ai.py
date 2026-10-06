from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.agent import run_agent
from ..ai.tools import TOOLS
from ..config import get_settings
from ..db import get_db
from ..deps import audit, require_owner
from ..models import AuditLog, User
from ..schemas import ChatIn, ConfirmIn
from ..security import verify_action

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def status(user: User = Depends(require_owner)):
    s = get_settings()
    endpoint = s.ai_endpoint()
    return {"mode": "model" if endpoint else "basic", "provider": s.ai_provider,
            "model": endpoint[2] if endpoint else None, "tools": list(TOOLS)}


@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    history = [m.model_dump() for m in body.messages]
    if history[-1]["role"] != "user":
        raise HTTPException(400, "The last message must be from you.")
    return run_agent(db, user, history)


@router.post("/confirm")
def confirm(body: ConfirmIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    data = verify_action(body.action_token)
    if not data or data.get("uid") != user.id:
        raise HTTPException(400, "This action has expired. Ask the assistant again.")
    tool = TOOLS.get(data.get("tool", ""))
    if not tool or not tool.is_action:
        raise HTTPException(400, "Unknown action.")
    args = dict(data.get("args") or {})
    jti = str(args.pop("_jti", ""))
    if jti and db.scalar(select(AuditLog.id).where(AuditLog.action == "ai.action", AuditLog.entity_id == jti)):
        raise HTTPException(409, "This action was already done.")
    result = tool.execute(db, user, **args)
    audit(db, user, "ai.action", "ai", jti, new={"tool": tool.name, "args": args, "result": result["message"]})
    db.commit()
    return {"ok": True, "message": result["message"]}
