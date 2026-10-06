from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pypinyin import lazy_pinyin,Style
from snownlp import SnowNLP
from datetime import datetime, timezone
from uuid import uuid4
from storage import save_record, get_history, init_db

init_db()  # 初始化数据库，创建表格

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=True,
)

profile = {
    "heroTitle": "关于我",  # → 临时加的标记，验证完删掉
    "heroSubtitle": "项目，创意，灵感，心得，我的作品",
    "featuredWork": {
        "kicker": "作品",
        "title": "文字实验室",
        "copy": "拼音和情绪，挖掘中文里的细节",
        "linkLabel": "打开作品",
    },
    "identity": {
        "motto": "已识乾坤大，尤怜草木青",
        "learning": "零到全栈",
    },
}


class AnalyzeRequest(BaseModel):
    text: str


def get_session_id(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = uuid4().hex
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
        )
    return session_id

@app.get("/api/profile")
def get_profile():
    return profile

def score_label(score):
    if score >= 0.6:
        return "偏积极"
    elif score <= 0.4:
        return "偏消极"
    else:
        return "中性"

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, response: Response):
    sid = get_session_id(request, response)
    text = req.text
    score = round(SnowNLP(text).sentiments, 2)
    result = {
        "text": text,
        "score": score,
        "label": score_label(score),
        "pinyin": " ".join(lazy_pinyin(text, style=Style.TONE)),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_record(sid, result)          # 存的时候盖上这个会话的记号
    return result                     # ← 返回体一个字没变，session_id 只走 cookie

@app.get("/api/history")
def history(request: Request, response: Response, limit: int = 10):
    sid = get_session_id(request, response)
    return get_history(sid, limit)    # 只回这个会话自己的
