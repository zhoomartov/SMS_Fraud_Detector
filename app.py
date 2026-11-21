"""Streamlit frontend. Обращается к FastAPI через requests; ML-логики здесь нет."""
import html
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("SMS_API_URL", "http://127.0.0.1:8000").rstrip("/")
COLORS = {"low": "#16a34a", "medium": "#f59e0b", "high": "#dc2626"}
TITLES = {"low": "НИЗКИЙ РИСК", "medium": "СРЕДНИЙ РИСК", "high": "ВЫСОКИЙ РИСК"}
CHUNK = 200
MAX_LEN = 5000

st.set_page_config(page_title="SMS Fraud Detector", page_icon="🛡️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1100px;}
.hero h1 {font-size: 2.2rem; margin-bottom: .2rem;}
.hero p {color: #6b7280; margin-top: 0;}
.risk-card {border-radius: 16px; padding: 1.4rem 1.6rem; color: white; margin: .5rem 0 1rem 0;}
.risk-card .score {font-size: 3.2rem; font-weight: 700; line-height: 1;}
.risk-card .title {font-size: 1.1rem; letter-spacing: .08em; opacity: .95;}
.bar {background: rgba(255,255,255,.3); border-radius: 8px; height: 12px; margin-top: .8rem;}
.bar > div {background: white; height: 12px; border-radius: 8px;}
.reco {border-left: 4px solid #3b82f6; padding: .6rem 1rem; background: rgba(59,130,246,.08); border-radius: 6px;}
</style>
""", unsafe_allow_html=True)


def call_api(method, path, payload=None, timeout=10):
    try:
        r = requests.request(
            method,
            API_URL + path,
            json=payload,
            timeout=timeout
        )
    except requests.ConnectionError:
        return None, f"API недоступен по адресу {API_URL}. Запустите сервер API."
    except requests.Timeout:
        return None, "API не ответил вовремя. Проверьте, запущен ли сервер."
    except requests.RequestException as exc:
        return None, f"Ошибка запроса: {exc}"

    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return None, f"API вернул {r.status_code}: {detail}"

    return r.json(), None

def risk_card(result):
    color = COLORS[result["risk"]]
    st.markdown(
        f'<div class="risk-card" style="background:{color}">'
        f'<div class="title">{TITLES[result["risk"]]}</div>'
        f'<div class="score">{int(result["score"])}<span style="font-size:1.2rem"> / 100</span></div>'
        f'<div class="bar"><div style="width:{int(result["score"])}%"></div></div></div>',
        unsafe_allow_html=True)


st.session_state.setdefault("history", [])

with st.sidebar:
    st.header("Настройки")
    API_URL = st.text_input("Адрес API", API_URL).rstrip("/")
    health, err = call_api("GET", "/health")
    if err:
        st.error("API: не отвечает")
        st.caption(err)
    else:
        st.success("API: работает, модель загружена")
    st.caption("Уровни: LOW < 30, MEDIUM 30–64, HIGH ≥ 65")

st.markdown('<div class="hero"><h1>🛡️ SMS Fraud Detector</h1>'
            '<p>Обнаружение мошеннических SMS на русском и кыргызском языках: '
            'оценка риска от 0 до 100, причины и рекомендации.</p></div>', unsafe_allow_html=True)

tab_single, tab_batch = st.tabs(["Проверка SMS", "Массовая проверка CSV"])

with tab_single:
    text = st.text_area("Текст SMS", height=140, placeholder="Вставьте текст сообщения…")
    if st.button("Проверить", type="primary"):
        if not text.strip():
            st.warning("Введите текст SMS.")
        else:
            data, error = call_api("POST", "/check", {"text": text[:MAX_LEN]})
            if error:
                st.error(error)
            else:
                st.session_state["last"] = data
                st.session_state["history"].insert(0, {
                    "Время": datetime.now().strftime("%H:%M:%S"),
                    "SMS": text[:80] + ("…" if len(text) > 80 else ""),
                    "Риск": data["risk"].upper(), "Оценка": data["score"]})
    result = st.session_state.get("last")
    if result:
        left, right = st.columns([1, 1.4])
        with left:
            risk_card(result)
        with right:
            st.subheader("Причины")
            if result["reasons"]:
                for reason in result["reasons"]:
                    st.markdown(f"- {html.escape(reason)}")
            else:
                st.caption("Явных признаков по правилам не найдено.")
            if result.get("domains"):
                st.subheader("Домены")
                st.dataframe(pd.DataFrame(result["domains"]).rename(columns={
                    "domain": "Домен", "official": "Официальный", "impersonation": "Похож на официальный"}),
                    hide_index=True, use_container_width=True)
            st.subheader("Рекомендация")
            st.markdown(f'<div class="reco">{html.escape(result["recommendation"])}</div>',
                        unsafe_allow_html=True)
    st.subheader("История проверок")
    if st.session_state["history"]:
        st.dataframe(pd.DataFrame(st.session_state["history"]), hide_index=True, use_container_width=True)
        if st.button("Очистить историю"):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.caption("Пока пусто.")

with tab_batch:
    st.write("Загрузите CSV со столбцом с текстом SMS (например, `text`).")
    up = st.file_uploader("CSV-файл", type=["csv"])
    if up is not None:
        try:
            df = pd.read_csv(up)
        except Exception as exc:
            st.error(f"Не удалось прочитать CSV: {exc}")
            df = None
        if df is not None and df.empty:
            st.error("Файл пустой.")
        elif df is not None:
            col = "text" if "text" in df.columns else st.selectbox("Столбец с текстом", list(df.columns))
            if st.button("Проверить файл", type="primary"):
                texts = df[col].fillna("").astype(str)
                valid = texts.str.strip() != ""
                if (~valid).any():
                    st.warning(f"Пропущено пустых строк: {int((~valid).sum())}")
                idx = list(df.index[valid])
                results, failed = [], None
                bar = st.progress(0.0)
                for start in range(0, len(idx), CHUNK):
                    part = idx[start:start + CHUNK]
                    data, error = call_api("POST", "/check/batch",
                                           {"texts": [texts[i][:MAX_LEN] for i in part]})
                    if error:
                        failed = error
                        break
                    results += data["results"]
                    bar.progress(min(1.0, (start + len(part)) / max(len(idx), 1)))
                if failed:
                    st.error(failed)
                else:
                    out = df.loc[idx].copy()
                    out["score"] = [r["score"] for r in results]
                    out["risk"] = [r["risk"] for r in results]
                    out["reasons"] = ["; ".join(r["reasons"]) for r in results]
                    st.session_state["batch"] = out
    out = st.session_state.get("batch")
    if out is not None:
        st.subheader("Результаты")
        counts = out["risk"].value_counts().reindex(["low", "medium", "high"], fill_value=0)
        c1, c2, c3 = st.columns(3)
        c1.metric("LOW", int(counts["low"]))
        c2.metric("MEDIUM", int(counts["medium"]))
        c3.metric("HIGH", int(counts["high"]))
        st.bar_chart(counts)
        st.dataframe(out, use_container_width=True)
        st.download_button("Скачать результаты (CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                           file_name="sms_check_results.csv", mime="text/csv")
