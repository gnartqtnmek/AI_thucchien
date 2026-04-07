"""
Streamlit UI for Restaurant Chatbot vs ReAct Agent comparison with Monitoring.

Usage:
    streamlit run streamlit_app.py
"""

import os
import sys
from dotenv import load_dotenv

import streamlit as st

# Setup path
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.chatbot.chatbot import RestaurantChatbot
from src.agent.agent import ReActAgent as ReActAgentCustom
from src.agent.agent_v2 import ReActAgent as ReActAgentV2
from src.agent.agent_v2 import _build_menu_tools
from src.tools import TOOL_REGISTRY


def build_provider(provider_name: str = None):
    """Build LLM provider based on env config."""
    provider_name = provider_name or os.getenv("DEFAULT_PROVIDER", "openai")
    
    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    elif provider_name == "google":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def main():
    st.set_page_config(
        page_title="餐廳助手 - Chatbot vs Agent",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🍗 Nhà hàng Gà Rán - Chatbot vs ReAct Agent")

    # Global tracking session state
    if "global_metrics" not in st.session_state:
        st.session_state.global_metrics = {
            "total_cost": 0.0,
            "total_tokens": 0,
            "queries": 0,
        }

    # Sidebar configuration
    st.sidebar.header("⚙️ Cấu hình")
    
    app_mode = st.sidebar.radio(
        "Chế độ hiển thị (Mode):",
        ["Chat", "Monitor"]
    )

    provider_name = st.sidebar.selectbox(
        "Chọn LLM Provider:",
        ["openai", "google", "local"],
        index=0,
    )
    
    agent_selection = st.sidebar.selectbox(
        "Chọn phiên bản Agent:",
        [
            "Agent (agent.py)",
            "Agent V2 - OpenAI Tools (agent_v2.py)"
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "💡 **Lưu ý:**\n"
        "- Chatbot dùng tool data nhưng không suy luận đa bước\n"
        "- Agent (agent.py) là ReAct loop tự xây với Thought/Action/Observation\n"
        "- Agent V2 (agent_v2.py) sử dụng OpenAI Function Calling (Chỉ hỗ trợ OpenAI)\n"
    )

    # Force re-init if config changes, or if cached objects are missing new metric attrs (stale session)
    _stale = (
        "chatbot" not in st.session_state
        or not hasattr(st.session_state.get("chatbot"), "last_cost")
        or "active_agent" not in st.session_state
        or not hasattr(st.session_state.get("active_agent"), "last_cost")
    )
    if _stale or "llm_provider_name" not in st.session_state or st.session_state.llm_provider_name != provider_name or "agent_selection" not in st.session_state or st.session_state.agent_selection != agent_selection:
        try:
            st.session_state.llm = build_provider(provider_name)
            st.session_state.chatbot = RestaurantChatbot(st.session_state.llm)
            
            if agent_selection == "Agent (agent.py)":
                st.session_state.active_agent = ReActAgentCustom(
                    st.session_state.llm,
                    TOOL_REGISTRY,
                    max_steps=5,
                    version="v1",
                )
            elif agent_selection == "Agent V2 - OpenAI Tools (agent_v2.py)":
                v2_tools = _build_menu_tools("data/mock_data.json")
                st.session_state.active_agent = ReActAgentV2(
                    st.session_state.llm,
                    v2_tools,
                    max_steps=6,
                    trace_enabled=True,
                )
            
            st.session_state.llm_provider_name = provider_name
            st.session_state.agent_selection = agent_selection
            st.sidebar.success(
                f"✅ Đã load {provider_name} ({st.session_state.llm.model_name})"
            )
        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi load provider: {e}")
            return

    if app_mode == "Chat":
        st.markdown(
            "So sánh câu trả lời giữa Chatbot thường và phiên bản Agent được chọn."
        )

        # Input section
        st.markdown("### 📝 Nhập câu hỏi")
        user_input = st.text_area(
            "Câu hỏi của bạn:",
            placeholder="Ví dụ: Combo nào rẻ nhất? / Giao hàng được không? / Có voucher nào không?",
            height=80,
            key="user_input",
        )

        # Query button
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            run_query = st.button("🚀 Gửi", use_container_width=True)

        if run_query and user_input.strip():
            st.markdown("---")
            st.markdown("### 📊 Kết quả so sánh")

            with st.spinner("⏳ Đang xử lý..."):
                try:
                    chatbot_response = st.session_state.chatbot.chat(user_input.strip())
                    agent_response = st.session_state.active_agent.run(user_input.strip())
                    
                    # Accumulate Global Metrics
                    st.session_state.global_metrics["total_tokens"] += st.session_state.chatbot.last_tokens + st.session_state.active_agent.last_tokens
                    st.session_state.global_metrics["total_cost"] += st.session_state.chatbot.last_cost + st.session_state.active_agent.last_cost
                    st.session_state.global_metrics["queries"] += 1
                except Exception as e:
                    st.error(f"❌ Lỗi khi xử lý: {e}")
                    return

            # Display results in two columns
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🤖 Chatbot (Baseline)")
                st.markdown(
                    f"""
    <div style="background-color: #003d99; color: #ffffff; padding: 15px; border-radius: 8px; border-left: 4px solid #0052cc; font-size: 14px; line-height: 1.6;">
    {chatbot_response}
    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"**⏱️ Time:** {st.session_state.chatbot.last_latency:.2f} ms | **🪙 Tokens:** {st.session_state.chatbot.last_tokens} | **💵 Cost:** ${st.session_state.chatbot.last_cost:.5f} | **⚖️ Ratio (PMT/TOT):** {st.session_state.chatbot.last_ratio:.2f}")

            with col2:
                st.markdown(f"#### 🧠 {agent_selection}")
                st.markdown(
                    f"""
    <div style="background-color: #1a6d1a; color: #ffffff; padding: 15px; border-radius: 8px; border-left: 4px solid #33a333; font-size: 14px; line-height: 1.6;">
    {agent_response}
    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(f"**⏱️ Time:** {st.session_state.active_agent.last_latency:.2f} ms | **🪙 Tokens:** {st.session_state.active_agent.last_tokens} | **💵 Cost:** ${st.session_state.active_agent.last_cost:.5f} | **⚖️ Ratio (PMT/TOT):** {st.session_state.active_agent.last_ratio:.2f}")
                
                with st.expander("🛠️ Xem Trace"):
                    if hasattr(st.session_state.active_agent, 'last_trace'):
                        if agent_selection == "Agent OpenAI Tools (agent_v2.py)":
                            for idx, t in enumerate(st.session_state.active_agent.last_trace):
                                st.markdown(f"**Bước {idx + 1}:**")
                                st.json(t)
                        else:
                            for t in st.session_state.active_agent.last_trace:
                                st.text(t)

            # Reset chatbot state for next conversation
            st.session_state.chatbot.history = []

        elif run_query and not user_input.strip():
            st.warning("⚠️ Vui lòng nhập một câu hỏi.")

    elif app_mode == "Monitor":
        st.markdown("## 📈 Global Metrics Dashboard (Monitor)")
        st.markdown("Theo dõi chi phí và số lượng token hệ thống đã sử dụng trong phiên làm việc (session) hiện tại.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tokens Processed", f"{st.session_state.global_metrics['total_tokens']:,}")
        col2.metric("Total Estimated Cost (USD)", f"${st.session_state.global_metrics['total_cost']:.5f}")
        col3.metric("Successful Queries Executed", st.session_state.global_metrics['queries'])

        st.info("Các số liệu bên trên được tích luỹ cho cả Chatbot và Agent sau mỗi lần Gửi truy vấn thành công.")

    # Footer
    st.markdown("---")
    st.markdown(
        """
<div style="text-align: center; color: #666;">
    <small>Lab 3: From Chatbot to Agentic ReAct | AI 20K26</small>
</div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
