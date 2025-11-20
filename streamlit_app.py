import streamlit as st
from openai import OpenAI
import os

st.set_page_config(page_title="🍜 야식 챗봇", page_icon="🍜")

st.title("🍜 야식 추천 챗봇")
st.write("야식을 고르기 어려우신가요? 취향과 예산을 알려주시면 맞춤 야식 메뉴를 추천해드리고 대화를 이어가겠습니다.")


def _get_api_key():
    # 지원: .streamlit/secrets.toml의 OPENAI_API_KEY 또는 [openai]/api_key, 또는 환경변수
    return (
        st.secrets.get("OPENAI_API_KEY")
        or st.secrets.get("openai", {}).get("api_key")
        or os.environ.get("OPENAI_API_KEY")
    )


API_KEY = _get_api_key()
if not API_KEY:
    st.error("OpenAI API 키가 설정되어 있지 않습니다. `./.streamlit/secrets.toml`에 `OPENAI_API_KEY = \"...\"` 형태로 추가하세요.")
    st.stop()

# Create OpenAI client using official SDK
client = OpenAI(api_key=API_KEY)


if "messages" not in st.session_state:
    # 첫 시스템 메시지: 챗봇 역할 정의 (한국어, 야식 추천 특화)
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "당신은 친절한 한국어 야식 추천 전문가입니다. 사용자가 원하는 분위기, 예산, 음식 성향(매운 것/안 매운 것, 고기/채식 등), 알레르기 여부, 배달 가능성 등을 물어보고 "
                "그에 맞춰 실용적인 3가지 추천 메뉴를 제안하세요. 각 메뉴에 대해 간단한 설명(맛, 예상 가격, 주문 방법 또는 간단한 조리 팁)을 포함하고, 사용자가 더 원하면 추가 추천이나 레시피를 제공하세요. "
                "대화는 한국어로 친근하고 간결하게 진행하세요."
            ),
        }
    ]


def render_messages():
    for m in st.session_state.messages:
        # 시스템 메시지는 UI에 직접 출력하지 않음
        if m["role"] == "system":
            continue
        with st.chat_message(m["role"]):
            st.markdown(m["content"])


def send_to_openai(messages):
    # messages: list of dicts with role/content
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=800,
        )
        # New OpenAI client returns choices; extract assistant text robustly
        assistant_msg = None

        # Normalize choices access (works for attribute or dict-like responses)
        choices = None
        if hasattr(resp, "choices"):
            choices = resp.choices
        elif isinstance(resp, dict):
            choices = resp.get("choices")

        if choices and len(choices) > 0:
            choice0 = choices[0]

            # 1) Try choice0.message.content (attribute or dict)
            msg = None
            if hasattr(choice0, "message"):
                msg = choice0.message
            elif isinstance(choice0, dict):
                msg = choice0.get("message") or choice0.get("delta")

            if msg is not None:
                if isinstance(msg, dict):
                    assistant_msg = msg.get("content")
                else:
                    assistant_msg = getattr(msg, "content", None)

            # 2) Fallbacks: choice0.text or choice0.get('text')
            if not assistant_msg:
                if hasattr(choice0, "text"):
                    assistant_msg = getattr(choice0, "text", None)
                elif isinstance(choice0, dict):
                    assistant_msg = choice0.get("text")

        # 3) As a last fallback, try top-level fields or string conversion
        if not assistant_msg:
            if hasattr(resp, "text"):
                assistant_msg = getattr(resp, "text", None)
            elif isinstance(resp, dict):
                assistant_msg = resp.get("text")

        if assistant_msg is None:
            assistant_msg = str(resp)

        return assistant_msg
    except Exception as e:
        return f"(오류) 응답 생성 중 문제가 발생했습니다: {e}"


with st.sidebar:
    st.header("설정")
    st.caption("모델: 고정 — gpt-4o-mini")
    if st.button("대화 초기화(Reset)"):
        st.session_state.messages = [st.session_state.messages[0]]
        st.experimental_rerun()


render_messages()

user_prompt = st.chat_input("무엇을 도와드릴까요? 예: '매콤한 거 먹고 싶어, 배달 가능하면 좋아'")
if user_prompt:
    # store and show user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # prepare messages for API call (include system + conversation)
    api_messages = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
    ]

    # call OpenAI API
    with st.chat_message("assistant"):
        placeholder = st.empty()
        assistant_text = send_to_openai(api_messages)
        placeholder.markdown(assistant_text)

    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
