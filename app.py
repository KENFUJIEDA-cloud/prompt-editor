"""
app.py  ─  LLM Prompt Editor (AWS Bedrock版)
"""
import os
import json
import re
import time
from datetime import datetime

import boto3
from botocore.session import Session
import streamlit as st

st.set_page_config(page_title="LLM Prompt Editor", page_icon="✏️", layout="wide")

st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }
  .score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .score-label { width: 100px; font-size: 12px; color: #5F5E5A; flex-shrink: 0; }
  .score-bar-bg { flex: 1; height: 8px; background: #E8E6E0; border-radius: 4px; overflow: hidden; }
  .score-bar-fill { height: 100%; border-radius: 4px; }
  .score-num { width: 36px; font-size: 13px; font-weight: 600; text-align: right; flex-shrink: 0; }
  .comment-card { border-left: 3px solid #534AB7; background: #F7F5FF; border-radius: 0 8px 8px 0; padding: 8px 14px; margin-bottom: 8px; font-size: 13px; line-height: 1.6; }
  .comment-card.good { border-color: #3B6D11; background: #F2F8EA; }
  .comment-card.warn { border-color: #BA7517; background: #FEF6E8; }
  .comment-card.bad  { border-color: #A32D2D; background: #FEF0F0; }
  .improved-box { background: #F2F8EA; border: 0.5px solid #97C459; border-radius: 10px; padding: 14px 16px; font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

MODEL_ID = "jp.anthropic.claude-sonnet-4-6"
REGION = "ap-northeast-1"
AWS_PROFILE = "PowerUser-980268627924"

EVAL_CRITERIA = [
    ("clarity",     "明確さ"),
    ("specificity", "具体性"),
    ("role",        "役割設定"),
    ("output_fmt",  "出力形式"),
    ("context",     "コンテキスト"),
    ("constraint",  "制約条件"),
]

SCORE_SYSTEM = """あなたはプロンプトエンジニアリングの専門家です。
ユーザーが入力したプロンプトを以下の6つの観点で採点し、改善案を提示してください。

## 採点観点
1. clarity      : 明確さ（指示が曖昧なく伝わるか）
2. specificity  : 具体性（抽象的でなく具体的な条件・例があるか）
3. role         : 役割設定（AIの役割・ペルソナが適切に定義されているか）
4. output_fmt   : 出力形式（形式・長さ・構造の指定があるか）
5. context      : コンテキスト（背景情報・前提が十分に与えられているか）
6. constraint   : 制約条件（やってはいけないこと・制限が明示されているか）

## 出力形式（必ずこのJSONのみ返してください。前置きや説明は不要）
{
  "scores": {
    "clarity":     <0-100の整数>,
    "specificity": <0-100の整数>,
    "role":        <0-100の整数>,
    "output_fmt":  <0-100の整数>,
    "context":     <0-100の整数>,
    "constraint":  <0-100の整数>
  },
  "comments": [
    {"type": "good"|"warn"|"bad", "text": "<日本語のコメント>"}
  ],
  "summary": "<総評を2〜3文で>",
  "improved_prompt": "<改善されたプロンプト全文>"
}
必ずJSON形式のみ返す。コードブロックも不要。"""


def score_color(score):
    if score >= 75: return "#639922"
    elif score >= 50: return "#BA7517"
    else: return "#D85A30"


@st.cache_resource
def get_bedrock_client():
    session = boto3.Session(profile_name=AWS_PROFILE)
    return session.client("bedrock-runtime", region_name=REGION)


def score_prompt(prompt_text, client):
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "system": SCORE_SYSTEM,
        "messages": [{"role": "user", "content": f"以下のプロンプトを採点してください:\n\n{prompt_text}"}],
    })
    try:
        response = client.invoke_model(modelId=MODEL_ID, body=body, contentType="application/json", accept="application/json")
        raw = json.loads(response["body"].read())["content"][0]["text"].strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m: raw = m.group(0)
        return json.loads(raw)
    except Exception as e:
        st.error(f"Bedrock エラー: {e}")
        return None


def render_score_bar(label, score):
    color = score_color(score)
    st.markdown(f"""<div class="score-row">
  <span class="score-label">{label}</span>
  <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%; background:{color};"></div></div>
  <span class="score-num" style="color:{color};">{score}</span>
</div>""", unsafe_allow_html=True)


for k, v in [("result", None), ("prompt_text", ""), ("history", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("## ✏️ LLM Prompt Editor")
st.caption(f"AWS Bedrock ({MODEL_ID}) でプロンプトを6観点で自動採点・改善案を生成します")
st.divider()

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("#### 📝 プロンプト入力")
    prompt_input = st.text_area("プロンプト", value=st.session_state.prompt_text, height=280,
        placeholder="ここにプロンプトを入力してください...", label_visibility="collapsed")
    st.caption(f"{len(prompt_input)} 文字")

    run_col, clear_col = st.columns([3, 1])
    with run_col:
        run_btn = st.button("🔍 採点して改善案を生成", type="primary", use_container_width=True, disabled=not prompt_input.strip())
    with clear_col:
        if st.button("クリア", use_container_width=True):
            st.session_state.prompt_text = ""
            st.session_state.result = None
            st.rerun()

    if st.session_state.result and st.session_state.result.get("improved_prompt"):
        st.markdown("")
        if st.button("⬆️ 改善案を入力欄に反映して再採点", use_container_width=True):
            st.session_state.prompt_text = st.session_state.result["improved_prompt"]
            st.session_state.result = None
            st.rerun()

with right:
    st.markdown("#### 📊 採点結果")
    if not prompt_input.strip():
        st.info("左側にプロンプトを入力してください。")
    elif st.session_state.result is None and not run_btn:
        st.info("「採点して改善案を生成」を押してください。")

if run_btn and prompt_input.strip():
    st.session_state.prompt_text = prompt_input
    with right:
        with st.spinner("Bedrock で採点中..."):
            t0 = time.time()
            client = get_bedrock_client()
            result = score_prompt(prompt_input, client)
            elapsed = time.time() - t0
        if result:
            st.session_state.result = result
            st.session_state.history.insert(0, {
                "prompt": prompt_input, "result": result,
                "elapsed": elapsed, "timestamp": datetime.now().strftime("%H:%M:%S"),
            })
            st.session_state.history = st.session_state.history[:20]
    st.rerun()

result = st.session_state.result
if result:
    with right:
        scores = result.get("scores", {})
        total = round(sum(scores.values()) / len(scores)) if scores else 0
        total_color = score_color(total)

        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f'<div style="font-size:42px;font-weight:700;color:{total_color};line-height:1;">{total}</div><div style="font-size:12px;color:#5F5E5A;">総合スコア / 100</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="font-size:13px;line-height:1.7;color:#444;padding-top:4px;">{result.get("summary","")}</div>', unsafe_allow_html=True)

        st.markdown("")
        for key, label in EVAL_CRITERIA:
            render_score_bar(label, scores.get(key, 0))

        st.markdown("")
        for c in result.get("comments", []):
            ctype = c.get("type", "warn")
            icon = {"good": "✅", "warn": "⚠️", "bad": "❌"}.get(ctype, "•")
            st.markdown(f'<div class="comment-card {ctype}">{icon} {c["text"]}</div>', unsafe_allow_html=True)

    improved = result.get("improved_prompt", "")
    if improved:
        st.divider()
        st.markdown("#### 🌱 改善されたプロンプト")
        st.markdown(f'<div class="improved-box">{improved}</div>', unsafe_allow_html=True)
        st.markdown("")
        st.download_button("📥 ダウンロード", data=improved, file_name="improved_prompt.txt", mime="text/plain")

if st.session_state.history:
    st.divider()
    st.markdown("#### 🕘 採点履歴")
    for i, h in enumerate(st.session_state.history):
        h_scores = h["result"].get("scores", {})
        h_total = round(sum(h_scores.values()) / len(h_scores)) if h_scores else 0
        h_color = score_color(h_total)
        c1, c2, c3, c4 = st.columns([1, 5, 2, 1])
        with c1:
            st.markdown(f'<span style="font-size:22px;font-weight:700;color:{h_color};">{h_total}</span>', unsafe_allow_html=True)
        with c2:
            st.caption(h["prompt"][:80] + ("..." if len(h["prompt"]) > 80 else ""))
        with c3:
            st.caption(h.get("timestamp", ""))
        with c4:
            if st.button("復元", key=f"restore_{i}"):
                st.session_state.prompt_text = h["prompt"]
                st.session_state.result = h["result"]
                st.rerun()
        st.markdown("---")


# ── Test execution ────────────────────────────────────
if result:
    st.divider()
    st.markdown("#### ▶️ プロンプトをそのまま実行")
    if st.button("このプロンプトでAIに問い合わせる", use_container_width=True):
        with st.spinner("Bedrock で実行中..."):
            try:
                client = get_bedrock_client()
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": st.session_state.prompt_text}],
                })
                response = client.invoke_model(modelId=MODEL_ID, body=body, contentType="application/json", accept="application/json")
                answer = json.loads(response["body"].read())["content"][0]["text"]
                st.markdown("**AIの回答:**")
                st.markdown(f'<div style="background:#F7F8FA; border:0.5px solid #E0DDD6; border-radius:8px; padding:14px 16px; font-size:13px; line-height:1.7; white-space:pre-wrap;">{answer}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"実行エラー: {e}")
