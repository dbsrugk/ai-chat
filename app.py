#!/usr/bin/env python3
"""
app.py — Claude · GPT 2자 대화 (호스팅 배포용, 실제 API)
=========================================================
이 파일을 Render 등 무료 호스팅에 올리면, 인터넷 주소만으로
어디서든 진짜 Claude와 GPT가 번갈아 대화하는 사이트가 됩니다.

호스팅에서 설정할 환경변수(Environment Variables) 2개:
    ANTHROPIC_API_KEY = sk-ant-...
    OPENAI_API_KEY    = sk-...

(Gemini를 다시 넣고 싶으면 아래 ORDER와 HANDLERS, 화면 부분에
 Gemini를 추가하고 GOOGLE_API_KEY 환경변수를 설정하면 됩니다.)
"""

import os
from flask import Flask, request, jsonify, Response

# ── 모델 설정 (2026-06 최신. 자유롭게 변경 가능) ──
CLAUDE_MODEL = "claude-opus-4-6"
GPT_MODEL    = "gpt-5.5"

PERSONAS = {
    "Claude": "너는 Claude야. 사려 깊고 호기심이 많으며, 가끔 질문을 던져 대화를 넓힌다.",
    "GPT":    "너는 GPT야. 위트 있고 활기차며, 농담과 가벼운 비유를 즐긴다.",
}

BASE_RULES = (
    "지금 Claude와 GPT 두 AI가 한 채팅방에서 자유롭게 잡담하고 있다. "
    "한국어로, 사람처럼 자연스럽고 짧게(2~4문장) 말해라. "
    "딱딱한 설명체 대신 친구끼리 수다 떠는 말투로. "
    "앞사람 말을 듣고 자연스럽게 이어가되, 가끔 새로운 얘깃거리도 던져라. "
    "자기 이름을 매번 붙이지 말고 그냥 대화 내용만 말해라."
)

app = Flask(__name__)


def build_transcript(history, me):
    if not history:
        return "(아직 아무도 말하지 않았다. 네가 대화를 시작해라.)"
    lines = []
    for h in history:
        tag = "나" if h.get("speaker") == me else h.get("speaker")
        lines.append(f"{tag}: {h.get('text','')}")
    return "\n".join(lines)


def make_system(speaker, topic):
    system = f"{PERSONAS[speaker]} {BASE_RULES}"
    if topic:
        system += f" 오늘의 대화 주제 힌트: '{topic}'."
    return system


def make_user_msg(speaker, history):
    transcript = build_transcript(history, speaker)
    return (f"지금까지의 대화:\n{transcript}\n\n"
            f"이제 네({speaker}) 차례야. 다음 한 마디를 말해줘.")


def ask_claude(history, topic):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=300,
        system=make_system("Claude", topic),
        messages=[{"role": "user", "content": make_user_msg("Claude", history)}],
    )
    return resp.content[0].text.strip()


def ask_gpt(history, topic):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=GPT_MODEL, max_completion_tokens=300,
        messages=[
            {"role": "system", "content": make_system("GPT", topic)},
            {"role": "user", "content": make_user_msg("GPT", history)},
        ],
    )
    return resp.choices[0].message.content.strip()


HANDLERS = {"Claude": ask_claude, "GPT": ask_gpt}


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/api/keys")
def keys_status():
    return jsonify({
        "Claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "GPT": bool(os.environ.get("OPENAI_API_KEY")),
    })


@app.route("/api/turn", methods=["POST"])
def turn():
    data = request.get_json(force=True)
    speaker = data.get("speaker")
    topic = data.get("topic", "")
    history = data.get("history", [])
    if speaker not in HANDLERS:
        return jsonify({"error": f"unknown speaker: {speaker}"}), 400
    try:
        return jsonify({"speaker": speaker, "text": HANDLERS[speaker](history, topic)})
    except KeyError as e:
        return jsonify({"error": f"API 키 환경변수 누락: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude · GPT 대화</title>
<style>
  :root{
    --panel:#171a23; --panel2:#1d212c;
    --claude:#7c9cff; --claude-bg:#1b2440;
    --gpt:#5fd28a;    --gpt-bg:#163127;
    --text:#e7e9ee; --muted:#8b90a0; --line:#262a36;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
    background:radial-gradient(1200px 600px at 50% -10%,#1a1f2e,#0f1117);
    color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .app{width:100%;max-width:760px;background:var(--panel);border:1px solid var(--line);
    border-radius:20px;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,.5);display:flex;flex-direction:column;height:90vh;max-height:900px}
  header{padding:18px 22px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;background:var(--panel2)}
  .avas{display:flex}
  .avas .ava{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:13px;color:#0f1117;border:2px solid var(--panel2);margin-left:-8px}
  .avas .ava:first-child{margin-left:0}
  .ava.c{background:var(--claude)} .ava.g{background:var(--gpt)}
  .head-meta{flex:1}
  header h1{font-size:16px;font-weight:700}
  header p{font-size:12px;color:var(--muted);margin-top:2px}
  .live{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:6px}
  .live .blink{width:7px;height:7px;border-radius:50%;background:#3ddc84;box-shadow:0 0 8px #3ddc84;animation:pulse 1.4s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .warn{background:#3a2218;color:#ffb98a;font-size:12.5px;padding:9px 22px;border-bottom:1px solid var(--line);display:none}
  .feed{flex:1;overflow-y:auto;padding:22px;display:flex;flex-direction:column;gap:14px;scroll-behavior:smooth}
  .feed::-webkit-scrollbar{width:8px}.feed::-webkit-scrollbar-thumb{background:#2c313f;border-radius:8px}
  .row{display:flex;gap:10px;max-width:88%;align-self:flex-start;animation:rise .35s ease}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .sm{width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;color:#0f1117}
  .sm.Claude{background:var(--claude)} .sm.GPT{background:var(--gpt)}
  .name{font-size:11px;color:var(--muted);margin-bottom:4px}
  .bub{padding:11px 14px;border-radius:16px;border-top-left-radius:5px;font-size:14.5px;line-height:1.55;white-space:pre-wrap}
  .bub.Claude{background:var(--claude-bg)} .bub.GPT{background:var(--gpt-bg)}
  .bub.err{background:#3a1f1f;color:#ff9b9b}
  .typing{display:flex;gap:4px;padding:14px}
  .typing span{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:bounce 1.2s infinite}
  .typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
  @keyframes bounce{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-5px);opacity:1}}
  .controls{padding:14px 18px;border-top:1px solid var(--line);background:var(--panel2);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  button{font-family:inherit;font-size:13px;font-weight:600;border:none;border-radius:10px;padding:9px 16px;cursor:pointer;color:var(--text);background:#2a2f3d;transition:.15s}
  button:hover{background:#343a4a}
  button.primary{background:var(--claude);color:#0f1117}
  .topic{flex:1;min-width:150px;background:#11141c;border:1px solid var(--line);border-radius:10px;padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px}
  .topic::placeholder{color:#5b606f}
  .rounds{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
  .rounds input{width:54px;background:#11141c;border:1px solid var(--line);border-radius:8px;padding:7px;color:var(--text);font-family:inherit;text-align:center}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="avas">
      <div class="ava c">C</div><div class="ava g">G</div>
    </div>
    <div class="head-meta">
      <h1>Claude · GPT</h1>
      <p>두 AI의 실시간 대화</p>
    </div>
    <div class="live"><span class="blink"></span><span id="status">대기 중</span></div>
  </header>

  <div class="warn" id="warn"></div>
  <div class="feed" id="feed"></div>

  <div class="controls">
    <button class="primary" id="toggle">▶ 시작</button>
    <button id="reset">↺ 초기화</button>
    <button id="save">⤓ 저장</button>
    <input class="topic" id="topicInput" placeholder="대화 주제 (선택, 예: 우주여행)">
    <div class="rounds">라운드<input type="number" id="rounds" min="1" max="50" value="5"></div>
  </div>
</div>

<script>
const ORDER = ["Claude","GPT"];
const feed = document.getElementById('feed');
const statusEl = document.getElementById('status');
const toggleBtn = document.getElementById('toggle');
let running=false, history=[], turnIdx=0, stopFlag=false;

fetch('/api/keys').then(r=>r.json()).then(k=>{
  const missing = ORDER.filter(s=>!k[s]);
  if(missing.length){
    const w=document.getElementById('warn');
    w.style.display='block';
    w.textContent='⚠ API 키 미설정: '+missing.join(', ')+' — 호스팅 환경변수에 해당 키를 추가하세요.';
  }
}).catch(()=>{});

function addMessage(speaker,text,isErr){
  removeTyping();
  const row=document.createElement('div');
  row.className='row';
  row.innerHTML=`<div class="sm ${speaker}">${speaker[0]}</div>`+
    `<div><div class="name">${speaker}</div><div class="bub ${speaker}${isErr?' err':''}">${escapeHtml(text)}</div></div>`;
  feed.appendChild(row);
  feed.scrollTop=feed.scrollHeight;
}
function showTyping(speaker){
  removeTyping();
  const row=document.createElement('div');
  row.className='row';row.id='typingRow';
  row.innerHTML=`<div class="sm ${speaker}">${speaker[0]}</div><div class="bub ${speaker} typing"><span></span><span></span><span></span></div>`;
  feed.appendChild(row);feed.scrollTop=feed.scrollHeight;
}
function removeTyping(){const t=document.getElementById('typingRow');if(t)t.remove();}
function escapeHtml(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

async function nextTurn(){
  if(stopFlag){running=false;return;}
  const totalRounds=parseInt(document.getElementById('rounds').value)||5;
  if(turnIdx >= totalRounds*ORDER.length){ finish('대화 완료');return; }
  const speaker=ORDER[turnIdx % ORDER.length];
  const topic=document.getElementById('topicInput').value.trim();
  statusEl.textContent=speaker+' 생각 중...';
  showTyping(speaker);
  try{
    const res=await fetch('/api/turn',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({speaker,topic,history})
    });
    const data=await res.json();
    if(stopFlag){running=false;removeTyping();statusEl.textContent='멈춤';return;}
    if(data.error){ addMessage(speaker,'⚠ '+data.error,true); }
    else{ addMessage(speaker,data.text,false); history.push({speaker,text:data.text}); }
  }catch(e){ addMessage(speaker,'⚠ 서버 호출 실패: '+e.message,true); }
  turnIdx++;
  if(!stopFlag){statusEl.textContent='대화 중';setTimeout(nextTurn,700);}
  else{running=false;statusEl.textContent='멈춤';}
}

function start(){
  if(running)return;
  running=true;stopFlag=false;
  toggleBtn.textContent='⏸ 멈춤';toggleBtn.classList.remove('primary');
  statusEl.textContent='대화 중';
  nextTurn();
}
function pause(){ stopFlag=true; toggleBtn.textContent='▶ 계속';toggleBtn.classList.add('primary'); }
function finish(msg){
  running=false;stopFlag=true;removeTyping();
  toggleBtn.textContent='▶ 시작';toggleBtn.classList.add('primary');
  statusEl.textContent=msg;turnIdx=0;
}

toggleBtn.onclick=()=>{running && !stopFlag ? pause() : start();};
document.getElementById('reset').onclick=()=>{
  stopFlag=true;running=false;history=[];turnIdx=0;feed.innerHTML='';
  toggleBtn.textContent='▶ 시작';toggleBtn.classList.add('primary');statusEl.textContent='대기 중';
};
document.getElementById('save').onclick=()=>{
  if(!history.length){alert('저장할 대화가 없습니다.');return;}
  let txt='# Claude · GPT 대화\n\n';
  const topic=document.getElementById('topicInput').value.trim();
  if(topic)txt+='# 주제: '+topic+'\n\n';
  history.forEach(h=>txt+=h.speaker+': '+h.text+'\n\n');
  const blob=new Blob([txt],{type:'text/plain;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='ai_chat_log.txt';a.click();
};

addMessage('Claude','시작 버튼을 누르면 Claude와 GPT가 실제로 번갈아 대화합니다. 위에 주제를 적으면 그 주제로 시작해요.',false);
history.length=0;
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
