from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import csv
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

DATA_DIR = Path("motionfit_data")
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "session_logs.csv"

exercise_names = {
    "squat": "Squat",
    "pushup": "Push-up",
    "lunge": "Lunge",
    "pullup": "Pull-up",
    "legraise": "Leg Raise",
    "shoulderpress": "Shoulder Press",
    "lateralraise": "Lateral Raise",
}

exercise_meta = {
    "squat": {"tag": "하체", "goal": "횟수", "camera": "측면 권장", "target": 12, "sets": 3},
    "pushup": {"tag": "상체", "goal": "횟수", "camera": "측면 권장", "target": 10, "sets": 3},
    "lunge": {"tag": "하체", "goal": "횟수", "camera": "측면 권장", "target": 10, "sets": 3},
    "pullup": {"tag": "등", "goal": "횟수", "camera": "정면 또는 약간 측면", "target": 8, "sets": 3},
    "legraise": {"tag": "코어", "goal": "횟수", "camera": "측면 권장", "target": 12, "sets": 3},
    "shoulderpress": {"tag": "상체", "goal": "횟수", "camera": "정면 권장", "target": 12, "sets": 3},
    "lateralraise": {"tag": "어깨", "goal": "횟수", "camera": "정면 권장", "target": 12, "sets": 3},
}

exercise_tips = {
    "squat": ["엉덩이를 먼저 뒤로", "무릎이 안쪽으로 모이지 않게", "측면에서 하체 전체가 보이게"],
    "pushup": ["몸통을 일직선으로", "가슴을 충분히 내리기", "측면에서 어깨-골반-발이 보이게"],
    "lunge": ["앞무릎이 발 안쪽으로 무너지지 않게", "상체는 너무 숙이지 않기", "측면에서 앞다리 각도가 보이게"],
    "pullup": ["턱이 손 높이 위로", "반동보다 완전 신전 우선", "얼굴과 손목이 함께 보이게"],
    "legraise": ["다리를 곧게 유지", "허리가 과하게 뜨지 않게", "측면에서 어깨-골반-발끝이 보이게"],
    "shoulderpress": ["양팔 높이를 맞추기", "끝까지 밀어올리기", "정면에서 양어깨와 양손이 보이게"],
    "lateralraise": ["양팔을 어깨 높이까지", "반동 줄이기", "정면에서 양팔 전체가 보이게"],
}

INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Motion Fit</title>
<style>
:root{
  --bg:#f5f7fb;--panel:#fff;--line:#e5e7eb;--text:#0f172a;--muted:#64748b;
  --soft:#f8fafc;--shadow:0 16px 40px rgba(15,23,42,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;}
.shell{max-width:1220px;margin:0 auto;padding:24px;}
.hero{background:var(--panel);border:1px solid var(--line);border-radius:28px;padding:28px;box-shadow:var(--shadow);}
.brand{display:inline-flex;align-items:center;gap:10px;padding:10px 14px;border:1px solid var(--line);border-radius:999px;background:#fff;font-weight:800;margin-bottom:20px;}
.brand:before{content:"";width:10px;height:10px;border-radius:50%;background:#111827;}
h1{margin:0 0 8px;font-size:34px;letter-spacing:-.03em}
.sub{margin:0;color:var(--muted)}
.grid{margin-top:22px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.card{width:100%;text-align:left;border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,#fff,#fbfdff);padding:18px;cursor:pointer;transition:.15s ease}
.card:hover{transform:translateY(-2px);box-shadow:0 14px 28px rgba(15,23,42,.08)}
.row{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.tag,.goal{border-radius:999px;padding:7px 11px;font-size:12px;font-weight:800}
.tag{background:#0f172a;color:#fff}.goal{background:var(--soft);color:var(--muted);border:1px solid var(--line)}
.title{font-size:28px;font-weight:800;letter-spacing:-.03em;margin-bottom:6px}
.caption{color:var(--muted);font-size:14px}
@media (max-width:960px){.grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:640px){.shell{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:28px}}
</style>
</head>
<body>
<div class="shell">
<section class="hero">
<div class="brand">Motion Fit</div>
<h1>운동 선택</h1>
<p class="sub"></p>
<form method="post" class="grid">{{ cards|safe }}</form>
</section>
</div>
</body>
</html>
"""

CAMERA_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ exercise_kor }}</title>
<style>
:root{
  --bg:#f5f7fb;--panel:#fff;--line:#e5e7eb;--text:#0f172a;--muted:#64748b;--soft:#f8fafc;
  --shadow:0 16px 40px rgba(15,23,42,.06);--good:#16a34a;--warn:#f59e0b;--bad:#ef4444;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;}
.shell{max-width:1380px;margin:0 auto;padding:20px;}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.left{display:flex;gap:10px;flex-wrap:wrap}
.pill,.back{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border-radius:999px;border:1px solid var(--line);background:#fff;text-decoration:none;color:var(--text);font-size:13px;font-weight:800}
.layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(340px,.6fr);gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow)}
.viewer,.side{padding:16px}
.camera-box{position:relative;width:100%;aspect-ratio:16/10;overflow:hidden;border-radius:22px;background:#dbe2ea;border:1px solid #dbe3ec}
video,canvas{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
canvas{pointer-events:none}
.overlay{position:absolute;left:14px;right:14px;top:14px;display:flex;justify-content:space-between;gap:12px;z-index:2}
.overlay-box{min-width:120px;background:rgba(15,23,42,.72);color:#fff;border-radius:18px;padding:12px 14px;backdrop-filter:blur(8px)}
.overlay-k{font-size:12px;opacity:.72;margin-bottom:4px}.overlay-v{font-size:24px;font-weight:800}
.toolbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}
button,a.btn{border:none;border-radius:16px;padding:14px 16px;font-size:14px;font-weight:800;cursor:pointer;text-decoration:none;text-align:center}
.dark{background:#111827;color:#fff}.light{background:#fff;color:var(--text);border:1px solid var(--line)}
.accent{background:#0f172a;color:#fff}.danger{background:#ef4444;color:#fff}
.card{border:1px solid var(--line);border-radius:22px;background:#fff;padding:18px}
.side{display:flex;flex-direction:column;gap:12px}
.status-chip{display:inline-flex;padding:8px 12px;border-radius:999px;background:#f8fafc;border:1px solid var(--line);font-size:12px;font-weight:800;margin-bottom:12px}
.feedback-main{font-size:22px;font-weight:800;line-height:1.35;margin-bottom:8px;letter-spacing:-.03em}
.feedback-sub{color:var(--muted);line-height:1.7;min-height:44px}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.metric{border:1px solid var(--line);border-radius:18px;background:var(--soft);padding:14px}
.metric-k{color:var(--muted);font-size:12px;margin-bottom:8px}.metric-v{font-size:22px;font-weight:800}
.list{display:grid;gap:8px;padding-left:18px;color:var(--muted);margin:0}
.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.field{display:grid;gap:8px}.field label{font-size:12px;font-weight:800;color:var(--muted)}
.field input{border:1px solid var(--line);border-radius:14px;padding:12px 14px;font-size:15px;font-weight:700;background:#fff}
.summary{display:none;border:1px solid #dbeafe;background:#f8fbff;border-radius:18px;padding:14px;margin-top:12px}
.summary.show{display:block}
.summary-title{font-size:15px;font-weight:800;margin-bottom:8px}
.summary-text{color:var(--muted);line-height:1.6}
.save-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.save-status{font-size:13px;color:var(--muted)}
.guide{display:grid;gap:6px;color:var(--muted);font-size:14px}
@media (max-width:1100px){.layout{grid-template-columns:1fr}}
@media (max-width:760px){.toolbar{grid-template-columns:1fr 1fr}}
@media (max-width:560px){.toolbar,.metric-grid,.config-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="shell">
<div class="topbar">
  <div class="left">
    <div class="pill">Motion Fit</div>
    <div class="pill">{{ exercise_kor }}</div>
    <div class="pill">{{ meta.tag }}</div>
  </div>
  <a href="/" class="back">운동 변경</a>
</div>

<div class="layout">
<section class="panel viewer">
  <div style="padding:2px 2px 14px;">
    <h1 style="margin:0 0 6px;font-size:30px;letter-spacing:-.03em;">{{ exercise_kor }}</h1>
    <p style="margin:0;color:#64748b;">권장 구도: {{ meta.camera }}</p>
  </div>

  <div class="camera-box">
    <video id="video" autoplay playsinline muted></video>
    <canvas id="canvas"></canvas>
    <div class="overlay">
      <div class="overlay-box"><div class="overlay-k">COUNT</div><div class="overlay-v" id="countText">0</div></div>
      <div class="overlay-box"><div class="overlay-k">GOOD REP</div><div class="overlay-v" id="goodText">0</div></div>
      <div class="overlay-box"><div class="overlay-k">STATE</div><div class="overlay-v" id="stateText">READY</div></div>
    </div>
  </div>

  <div class="toolbar">
    <button class="dark" onclick="startCamera()">카메라 시작</button>
    <button class="accent" onclick="startSet()">세트 시작</button>
    <button class="light" onclick="pauseSet()">일시정지</button>
    <button class="danger" onclick="endSession()">세션 종료</button>
  </div>
</section>

<aside class="panel side">
  <div class="card">
    <div class="status-chip" id="statusChip">대기 중</div>
    <div class="feedback-main" id="feedbackMain">카메라를 시작한 뒤 세트를 시작하세요.</div>
    <div class="feedback-sub" id="feedbackSub">세트 중에는 짧은 큐만 보여주고, 세트 종료 후에는 요약 피드백을 제공합니다.</div>

    <div class="config-grid">
      <div class="field">
        <label for="targetInput">목표 횟수</label>
        <input id="targetInput" type="number" min="1" max="50" value="{{ meta.target }}">
      </div>
      <div class="field">
        <label for="setsInput">세트 수</label>
        <input id="setsInput" type="number" min="1" max="10" value="{{ meta.sets }}">
      </div>
    </div>

    <div class="summary" id="summaryBox">
      <div class="summary-title" id="summaryTitle">세트 요약</div>
      <div class="summary-text" id="summaryText"></div>
    </div>

    <div class="save-row">
      <button class="light" onclick="saveSession()">기록 저장</button>
      
    </div>
    <div class="save-status" id="saveStatus">아직 저장된 세션 기록이 없습니다.</div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 12px;">운동 시작 가이드</h3>
    <div class="guide">
      <div>권장 카메라: {{ meta.camera }}</div>
      {% for tip in tips %}
      <div>• {{ tip }}</div>
      {% endfor %}
    </div>
  </div>

  <div class="card">
    <h3 style="margin:0 0 12px;">세션 상태</h3>
    <div class="metric-grid">
      <div class="metric"><div class="metric-k">현재 세트</div><div class="metric-v" id="setText">0 / 0</div></div>
      <div class="metric"><div class="metric-k">폼 점수</div><div class="metric-v" id="scoreText">-</div></div>
      <div class="metric"><div class="metric-k">카메라</div><div class="metric-v" id="cameraText">OFF</div></div>
      <div class="metric"><div class="metric-k">추적</div><div class="metric-v" id="trackingText">IDLE</div></div>
    </div>
  </div>
</aside>
</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
<script>
const EXERCISE_KEY = "{{ exercise_key }}";
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const countText = document.getElementById("countText");
const goodText = document.getElementById("goodText");
const stateText = document.getElementById("stateText");
const feedbackMain = document.getElementById("feedbackMain");
const feedbackSub = document.getElementById("feedbackSub");
const statusChip = document.getElementById("statusChip");
const setText = document.getElementById("setText");
const scoreText = document.getElementById("scoreText");
const cameraText = document.getElementById("cameraText");
const trackingText = document.getElementById("trackingText");
const targetInput = document.getElementById("targetInput");
const setsInput = document.getElementById("setsInput");
const summaryBox = document.getElementById("summaryBox");
const summaryTitle = document.getElementById("summaryTitle");
const summaryText = document.getElementById("summaryText");
const saveStatus = document.getElementById("saveStatus");

let pose = null, camera = null;
let skeletonOn = true;
let totalCount = 0, goodCount = 0, phase = "start", stableUp = 0, stableDown = 0, repLock = 0;
let cameraStarted = false, setActive = false, paused = false;
let currentSet = 0, totalSets = 0, targetReps = 0;
let liveScore = null;
let repScores = [];
let issueCounter = {};
let sessionHistory = [];

function resizeCanvas(){
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
}

function setStatus(chip, main, sub){
  statusChip.innerText = chip;
  feedbackMain.innerText = main;
  feedbackSub.innerText = sub;
}

function avg(values){
  const valid = values.filter(v => typeof v === "number" && !Number.isNaN(v));
  if(!valid.length) return null;
  return valid.reduce((a,b)=>a+b,0)/valid.length;
}

function point(lm, idx){
  const p = lm[idx];
  if(!p) return null;
  return {x:p.x,y:p.y,z:p.z,visibility:p.visibility || 0};
}

function chooseSide(lm){
  const left = [11,13,15,23,25,27].reduce((s,i)=>s+(lm[i]?.visibility||0),0);
  const right = [12,14,16,24,26,28].reduce((s,i)=>s+(lm[i]?.visibility||0),0);
  return left >= right ? "left" : "right";
}

function angle(a,b,c){
  if(!a || !b || !c) return null;
  const ab = {x:a.x-b.x,y:a.y-b.y};
  const cb = {x:c.x-b.x,y:c.y-b.y};
  const dot = ab.x*cb.x + ab.y*cb.y;
  const mag = Math.hypot(ab.x,ab.y) * Math.hypot(cb.x,cb.y);
  if(!mag) return null;
  const cos = Math.min(1, Math.max(-1, dot / mag));
  return Math.acos(cos) * 180 / Math.PI;
}

function resetRepCounters(){
  totalCount = 0;
  goodCount = 0;
  phase = "start";
  stableUp = 0;
  stableDown = 0;
  repLock = 0;
  repScores = [];
  issueCounter = {};
  updateHud();
}

function updateHud(){
  countText.innerText = String(totalCount);
  goodText.innerText = String(goodCount);
  setText.innerText = `${currentSet} / ${totalSets || 0}`;
  scoreText.innerText = liveScore == null ? "-" : String(Math.round(liveScore));
}

function addIssue(name){
  if(!name) return;
  issueCounter[name] = (issueCounter[name] || 0) + 1;
}

function registerRep(score, issue){
  totalCount += 1;
  if(score >= 80) goodCount += 1;
  repScores.push(score);
  if(issue) addIssue(issue);
  updateHud();
  if(totalCount >= targetReps) finishSet();
}

function topIssues(){
  return Object.entries(issueCounter)
    .sort((a,b)=>b[1]-a[1])
    .slice(0,2)
    .map(([name])=>name);
}

function updateRep(inUp, inDown, upLabel, downLabel, repScore, issue){
  if(repLock > 0) repLock -= 1;

  if(inDown){
    stableDown += 1;
    stableUp = 0;
    stateText.innerText = downLabel;
    if(phase === "up" && stableDown >= 3 && repLock === 0){
      repLock = 6;
      phase = "down";
      registerRep(repScore, issue);
    } else if(phase === "start" && stableDown >= 3){
      phase = "down";
    }
  } else if(inUp){
    stableUp += 1;
    stableDown = 0;
    stateText.innerText = upLabel;
    if((phase === "down" || phase === "start") && stableUp >= 3 && repLock === 0){
      phase = "up";
    }
  } else {
    stableUp = 0;
    stableDown = 0;
    stateText.innerText = "TRACK";
  }
}

function startSet(){
  if(!cameraStarted){
    setStatus("대기 중", "먼저 카메라를 시작하세요.", "카메라가 켜진 뒤 세트 시작이 가능합니다.");
    return;
  }
  if(setActive && !paused){
    setStatus("세트 진행", "이미 세트가 진행 중입니다.", "현재 세트를 마치거나 일시정지 후 다시 시작하세요.");
    return;
  }

  targetReps = Math.max(1, Number(targetInput.value || {{ meta.target }}));
  totalSets = Math.max(1, Number(setsInput.value || {{ meta.sets }}));

  if(!setActive && paused){
    paused = false;
    setActive = true;
    trackingText.innerText = "LIVE";
    setStatus("세트 진행", "세트를 다시 시작했습니다.", "짧은 큐를 보면서 동작을 이어가세요.");
    return;
  }

  if(currentSet >= totalSets){
    setStatus("완료", "모든 세트가 끝났습니다.", "기록 저장을 눌러 CSV로 남길 수 있습니다.");
    return;
  }

  currentSet += 1;
  setActive = true;
  paused = false;
  resetRepCounters();
  summaryBox.classList.remove("show");
  trackingText.innerText = "LIVE";
  setStatus("세트 진행", "세트를 시작했습니다.", "세트 중에는 짧은 큐만, 종료 후에는 요약 피드백을 제공합니다.");
}

function pauseSet(){
  if(!setActive){
    setStatus("대기 중", "현재 진행 중인 세트가 없습니다.", "카메라를 켜고 세트를 시작하세요.");
    return;
  }
  paused = true;
  setActive = false;
  trackingText.innerText = "PAUSE";
  setStatus("일시정지", "세트가 일시정지되었습니다.", "다시 시작을 누르면 이어서 진행합니다.");
}

function finishSet(){
  setActive = false;
  paused = false;
  trackingText.innerText = currentSet >= totalSets ? "DONE" : "REST";

  const avgScore = repScores.length ? Math.round(repScores.reduce((a,b)=>a+b,0)/repScores.length) : 0;
  const issues = topIssues();
  const summary = {
    exercise: EXERCISE_KEY,
    exercise_kor: "{{ exercise_kor }}",
    set_no: currentSet,
    target_reps: targetReps,
    total_reps: totalCount,
    good_reps: goodCount,
    avg_score: avgScore,
    issues: issues
  };
  sessionHistory.push(summary);

  summaryTitle.innerText = `${currentSet}세트 요약`;
  let text = `목표 ${targetReps}회 중 ${totalCount}회 수행, good rep ${goodCount}회, 평균 폼 점수 ${avgScore}점입니다.`;
  if(issues.length){
    text += ` 다음 세트에서는 ${issues.join(", ")}을(를) 먼저 보완해보세요.`;
  } else {
    text += ` 큰 문제 없이 진행됐습니다. 지금 리듬을 유지하면 좋습니다.`;
  }
  summaryText.innerText = text;
  summaryBox.classList.add("show");

  if(currentSet >= totalSets){
    setStatus("완료", "전체 세트가 끝났습니다.", "기록 저장을 눌러 CSV로 남길 수 있습니다.");
  } else {
    setStatus("세트 종료", "세트가 끝났습니다.", "다음 세트를 시작하려면 세트 시작을 누르세요.");
  }
}

async function saveSession(){
  if(!sessionHistory.length){
    saveStatus.innerText = "저장할 세트 기록이 없습니다.";
    return;
  }
  const payload = {
    created_at: new Date().toISOString(),
    exercise_key: EXERCISE_KEY,
    exercise_kor: "{{ exercise_kor }}",
    sets: sessionHistory
  };

  const res = await fetch("/api/save-session", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  saveStatus.innerText = data.message || "저장 완료";
}

function endSession(){
  setActive = false;
  paused = false;
  currentSet = 0;
  totalSets = 0;
  resetRepCounters();
  summaryBox.classList.remove("show");
  trackingText.innerText = cameraStarted ? "IDLE" : "OFF";
  setStatus("종료", "세션을 종료했습니다.", "다시 시작하려면 카메라를 켜고 세트를 시작하세요.");
  updateHud();
}

function evaluateForm(lm){
  const side = chooseSide(lm);
  const ids = side === "left"
    ? {shoulder:11, elbow:13, wrist:15, hip:23, knee:25, ankle:27}
    : {shoulder:12, elbow:14, wrist:16, hip:24, knee:26, ankle:28};

  const shoulder = point(lm, ids.shoulder);
  const elbow = point(lm, ids.elbow);
  const wrist = point(lm, ids.wrist);
  const hip = point(lm, ids.hip);
  const knee = point(lm, ids.knee);
  const ankle = point(lm, ids.ankle);
  const otherWrist = point(lm, side === "left" ? 16 : 15);
  const otherShoulder = point(lm, side === "left" ? 12 : 11);
  const otherHip = point(lm, side === "left" ? 24 : 23);
  const nose = point(lm, 0);

  const kneeAngle = angle(hip, knee, ankle);
  const elbowAngle = angle(shoulder, elbow, wrist);
  const hipAngle = angle(shoulder, hip, knee);
  const bodyAngle = angle(shoulder, hip, ankle);
  const shoulderY = avg([point(lm,11)?.y, point(lm,12)?.y]);
  const wristY = avg([point(lm,15)?.y, point(lm,16)?.y]);
  const hipDiff = otherHip && hip ? Math.abs(otherHip.y - hip.y) : 0;
  const shoulderDiff = otherShoulder && shoulder ? Math.abs(otherShoulder.y - shoulder.y) : 0;

  let score = 85;
  let issue = null;
  let main = "좋아요 그대로";
  let sub = "리듬을 유지하세요.";
  let inUp = false, inDown = false, upLabel = "UP", downLabel = "DOWN";

  if(EXERCISE_KEY === "squat"){
    if(kneeAngle == null || hipAngle == null){ return {main:"Squat 자세를 읽는 중입니다.", sub:"측면에서 하체 전체가 보이게 해주세요.", valid:false};}
    inDown = kneeAngle < 100;
    inUp = kneeAngle > 155;
    if(kneeAngle > 130){ score -= 15; issue = "깊이"; main = "조금 더 내려가세요"; sub = `무릎 각도 ${Math.round(kneeAngle)}°`; }
    else { main = "좋아요, 깊이가 좋습니다."; sub = `무릎 각도 ${Math.round(kneeAngle)}°`; }
    if(hipAngle < 55){ score -= 10; issue = issue || "상체 기울기"; main = "상체를 조금 더 세워보세요"; }
    if(hipDiff > 0.05){ score -= 8; issue = issue || "좌우 균형"; }
  } else if(EXERCISE_KEY === "pushup"){
    if(elbowAngle == null || bodyAngle == null){ return {main:"Push-up 자세를 읽는 중입니다.", sub:"측면에서 어깨-골반-발이 보이게 해주세요.", valid:false};}
    inDown = elbowAngle < 95;
    inUp = elbowAngle > 155;
    if(bodyAngle < 155){ score -= 15; issue = "몸통 정렬"; main = "몸통을 일직선으로 유지하세요"; }
    else if(elbowAngle > 120){ score -= 12; issue = "깊이"; main = "가슴을 조금 더 내려가세요"; }
    else { main = "좋아요, Push-up 자세가 안정적입니다."; }
    sub = `팔 ${Math.round(elbowAngle)}° / 몸통 ${Math.round(bodyAngle)}°`;
  } else if(EXERCISE_KEY === "lunge"){
    if(kneeAngle == null || bodyAngle == null){ return {main:"Lunge 자세를 읽는 중입니다.", sub:"측면에서 앞다리 각도가 보이게 해주세요.", valid:false};}
    inDown = kneeAngle < 105;
    inUp = kneeAngle > 155;
    if(kneeAngle > 120){ score -= 14; issue = "깊이"; main = "무릎을 조금 더 굽혀 내려가세요"; }
    else { main = "좋아요, Lunge 깊이가 적절합니다."; }
    if(bodyAngle < 150){ score -= 10; issue = issue || "상체 정렬"; }
    sub = `앞다리 무릎 ${Math.round(kneeAngle)}°`;
  } else if(EXERCISE_KEY === "pullup"){
    if(elbowAngle == null || nose == null || wristY == null){ return {main:"Pull-up 자세를 읽는 중입니다.", sub:"얼굴과 손목이 함께 보이게 해주세요.", valid:false};}
    inUp = nose.y < wristY && elbowAngle < 115;
    inDown = elbowAngle > 160;
    if(!inUp){ score -= 12; issue = "상단 도달"; main = "턱을 손 높이 위로 끌어올리세요"; }
    else { main = "좋아요, 상단 도달입니다."; }
    if(!inDown && phase === "up"){ score -= 8; issue = issue || "완전 신전"; }
    sub = `팔 각도 ${Math.round(elbowAngle)}°`;
    upLabel = "TOP"; downLabel = "BOTTOM";
  } else if(EXERCISE_KEY === "legraise"){
    if(hipAngle == null || kneeAngle == null){ return {main:"Leg Raise 자세를 읽는 중입니다.", sub:"측면에서 어깨-골반-발끝이 보이게 해주세요.", valid:false};}
    inUp = hipAngle < 100;
    inDown = hipAngle > 155;
    if(hipAngle > 120){ score -= 14; issue = "상단 높이"; main = "다리를 조금 더 높이 올려보세요"; }
    else { main = "좋아요, 다리가 충분히 올라왔습니다."; }
    if(kneeAngle < 155){ score -= 10; issue = issue || "다리 굽힘"; }
    sub = `골반 각도 ${Math.round(hipAngle)}° / 무릎 ${Math.round(kneeAngle)}°`;
  } else if(EXERCISE_KEY === "shoulderpress"){
    if(elbowAngle == null || !wrist || !otherWrist){ return {main:"Shoulder Press 자세를 읽는 중입니다.", sub:"정면에서 양어깨와 양손이 보이게 해주세요.", valid:false};}
    inUp = elbowAngle > 160;
    inDown = elbowAngle < 95;
    if(!inUp){ score -= 12; issue = "완전 신전"; main = "팔을 끝까지 밀어올리세요"; }
    else { main = "좋아요, 위로 끝까지 밀었습니다."; }
    const wristDiff = Math.abs(wrist.y - otherWrist.y);
    if(wristDiff > 0.06){ score -= 10; issue = issue || "양팔 비대칭"; }
    sub = `팔 각도 ${Math.round(elbowAngle)}°`;
  } else if(EXERCISE_KEY === "lateralraise"){
    if(!wrist || !otherWrist || shoulderY == null){ return {main:"Lateral Raise 자세를 읽는 중입니다.", sub:"정면에서 양팔 전체가 보이게 해주세요.", valid:false};}
    const avgWristY = avg([wrist.y, otherWrist.y]);
    inUp = avgWristY < shoulderY + 0.02;
    inDown = avgWristY > shoulderY + 0.12;
    if(!inUp){ score -= 12; issue = "팔 높이"; main = "양팔을 어깨 높이까지 들어주세요"; }
    else { main = "좋아요, 어깨 높이까지 올랐습니다."; }
    const wristDiff = Math.abs(wrist.y - otherWrist.y);
    if(wristDiff > 0.06){ score -= 10; issue = issue || "양팔 높이"; }
    sub = "양팔 높이를 비슷하게 유지하세요.";
  }

  score = Math.max(45, Math.min(100, Math.round(score)));
  return {valid:true, inUp, inDown, upLabel, downLabel, score, issue, main, sub};
}

function onResults(results){
  resizeCanvas();
  ctx.clearRect(0,0,canvas.width,canvas.height);

  if(!results.poseLandmarks){
    setStatus(cameraStarted ? "인식 대기" : "대기 중", "화면 안으로 들어와 주세요.", "관절이 보이면 자동으로 측정이 시작됩니다.");
    stateText.innerText = "READY";
    liveScore = null;
    updateHud();
    return;
  }

  const lm = results.poseLandmarks;
  if(skeletonOn){
    drawConnectors(ctx, lm, POSE_CONNECTIONS, {color:'#3b82f6', lineWidth:4});
    drawLandmarks(ctx, lm, {color:'#22c55e', fillColor:'#22c55e', lineWidth:1, radius:4});
  }

  const result = evaluateForm(lm);
  if(!result.valid){
    liveScore = null;
    updateHud();
    feedbackMain.innerText = result.main;
    feedbackSub.innerText = result.sub;
    return;
  }

  liveScore = result.score;
  updateHud();

  if(setActive){
    updateRep(result.inUp, result.inDown, result.upLabel, result.downLabel, result.score, result.issue);
    setStatus("세트 진행", result.main, result.sub);
  } else if(paused){
    setStatus("일시정지", "세트가 일시정지 상태입니다.", "다시 시작을 누르면 이어서 진행합니다.");
  } else {
    setStatus("카메라 연결", result.main, "카메라 구도를 먼저 맞춘 뒤 세트를 시작하세요.");
  }
}

async function startCamera(){
  if(camera) return;
  pose = new Pose({ locateFile: (file) => "https://cdn.jsdelivr.net/npm/@mediapipe/pose/" + file });
  pose.setOptions({
    modelComplexity: 1,
    smoothLandmarks: true,
    enableSegmentation: false,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
  });
  pose.onResults(onResults);

  camera = new Camera(video, {
    onFrame: async () => { await pose.send({image: video}); },
    width: 1280,
    height: 720
  });

  await camera.start();
  cameraStarted = true;
  cameraText.innerText = "ON";
  trackingText.innerText = "IDLE";
  setStatus("카메라 연결", "카메라가 시작되었습니다.", "자세를 잡고 세트를 시작하세요.");
  resizeCanvas();
}

window.addEventListener("resize", resizeCanvas);
window.onload = function(){ resizeCanvas(); updateHud(); };
</script>
</body>
</html>
"""

def ensure_csv_header():
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "saved_at", "exercise_key", "exercise_kor", "set_no",
                "target_reps", "total_reps", "good_reps", "avg_score", "issues_json"
            ])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selected = request.form.get("exercise")
        if selected in exercise_names:
            return redirect(url_for("camera", exercise=selected))

    cards = "".join(
        f"""
        <button class='card' type='submit' name='exercise' value='{key}'>
            <div class='row'>
                <span class='tag'>{exercise_meta[key]["tag"]}</span>
                <span class='goal'>{exercise_meta[key]["goal"]}</span>
            </div>
            <div class='title'>{exercise_names[key]}</div>
            <div class='caption'>{exercise_meta[key]["camera"]}</div>
        </button>
        """
        for key in exercise_names.keys()
    )
    return render_template_string(INDEX_HTML, cards=cards)

@app.route("/camera/<exercise>")
def camera(exercise):
    if exercise not in exercise_names:
        return redirect(url_for("index"))
    return render_template_string(
        CAMERA_HTML,
        exercise_key=exercise,
        exercise_kor=exercise_names[exercise],
        meta=exercise_meta[exercise],
        tips=exercise_tips[exercise],
    )

@app.route("/api/save-session", methods=["POST"])
def save_session():
    payload = request.get_json(force=True)
    sets = payload.get("sets", [])
    if not sets:
        return jsonify({"ok": False, "message": "저장할 세트 기록이 없습니다."}), 400

    ensure_csv_header()
    saved_at = datetime.now().isoformat(timespec="seconds")
    with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in sets:
            writer.writerow([
                saved_at,
                payload.get("exercise_key", ""),
                payload.get("exercise_kor", ""),
                row.get("set_no", ""),
                row.get("target_reps", ""),
                row.get("total_reps", ""),
                row.get("good_reps", ""),
                row.get("avg_score", ""),
                json.dumps(row.get("issues", []), ensure_ascii=False),
            ])

    return jsonify({"ok": True, "message": f"{len(sets)}개 세트 기록을 저장했습니다."})

if __name__ == "__main__":
    print("RUNNING_MOTIONFIT_UPGRADED")
    app.run(debug=True)
