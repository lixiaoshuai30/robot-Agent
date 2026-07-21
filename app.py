import streamlit as st
from agent.test import ReactAgent
from utils.db_handler import init_db, get_all_sessions, create_session, delete_session, DB_PATH
import sqlite3

# 1. 初始化数据库（创建 sessions 表）
init_db()

# 2. 页面标题
st.set_page_config(page_title="智扫通机器人智能客服", layout="wide")
st.title("智扫通机器人智能客服")
st.divider()

# 3. 初始化 Agent（确保在加载历史记录前可用）
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# 4. 侧边栏会话管理
with st.sidebar:
    st.header("会话管理")
    sessions = get_all_sessions()
    session_names = {s[0]: s[1] for s in sessions}

    # 新建会话按钮
    if st.button("➕ 新建会话", use_container_width=True):
        new_session_id = create_session()
        st.session_state["current_session_id"] = new_session_id
        st.session_state["message"] = []
        st.rerun()

    st.subheader("历史会话")
    if sessions:
        for session_id, session_name in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                # 切换会话
                if st.button(session_name, key=f"select_{session_id}", use_container_width=True):
                    st.session_state["current_session_id"] = session_id
                    st.session_state["message"] = []  # 清空当前内存，触发从数据库加载
                    st.rerun()
            with col2:
                # 删除会话
                if st.button("🗑️", key=f"delete_{session_id}"):
                    delete_session(session_id)
                    # 同时物理删除 checkpoints 表中的历史记录
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    try:
                        cursor.execute('DELETE FROM checkpoints WHERE thread_id = ?', (session_id,))
                        cursor.execute('DELETE FROM checkpoint_blobs WHERE thread_id = ?', (session_id,))
                        cursor.execute('DELETE FROM checkpoint_writes WHERE thread_id = ?', (session_id,))
                        conn.commit()
                    except:
                        pass
                    conn.close()
                    # 如果删的是当前会话，重置状态
                    if "current_session_id" in st.session_state and st.session_state[
                        "current_session_id"] == session_id:
                        del st.session_state["current_session_id"]
                        st.session_state["message"] = []
                    st.rerun()
    else:
        st.info("暂无历史会话")

# 5. 确定当前活跃会话
if "current_session_id" not in st.session_state:
    if sessions:
        st.session_state["current_session_id"] = sessions[0][0]  # 默认选第一个
    else:
        st.session_state["current_session_id"] = create_session()
    st.session_state["message"] = []

current_session_id = st.session_state["current_session_id"]

# 6. 【核心修复】从数据库加载历史消息到 UI
if not st.session_state["message"]:
    # 使用 Langgraph 官方方法获取状态
    config = {"configurable": {"thread_id": current_session_id}}
    state = st.session_state["agent"].agent.get_state(config)

    if state and state.values and "messages" in state.values:
        history_messages = state.values["messages"]
        for msg in history_messages:
            role = None
            # 识别消息类型并提取内容
            if msg.type == "human":
                role = "user"
            elif msg.type == "ai" and msg.content:  # 排除掉空的 AI 消息（如仅包含工具调用的）
                role = "assistant"

            if role and msg.content:
                st.session_state["message"].append({"role": role, "content": msg.content})

# 7. 界面展示
st.caption(f"当前会话 ID: {current_session_id}")
st.subheader(f"对话窗口: {session_names.get(current_session_id, '新会话')}")

# 显示消息历史
for message in st.session_state["message"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 8. 聊天输入处理
prompt = st.chat_input("请输入您的问题...")

if prompt:
    # 展示并保存用户消息
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 调用 Agent 获取流式回复
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        # 传入当前会话的 thread_id 确保记忆持久化到正确位置
        res_stream = st.session_state["agent"].execute_stream(prompt, thread_id=current_session_id)

        for chunk in res_stream:
            full_response += chunk
            placeholder.markdown(full_response + "▌")

        placeholder.markdown(full_response)

    # 保存助手消息并刷新
    st.session_state["message"].append({"role": "assistant", "content": full_response})
    st.rerun()
