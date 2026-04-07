import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from tools import search_flights, search_hotels, calculate_budget
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# 1. Đọc System Prompt
# =====================================================================
try:
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    print("Lỗi: Không tìm thấy file system_prompt.txt. Vui lòng tạo file trước khi chạy.")
    exit()

# =====================================================================
# 2. Khai báo State
# =====================================================================
class AgentState(TypedDict):
    # Dùng add_messages để tự động nối (append) tin nhắn mới vào list thay vì ghi đè
    messages: Annotated[list, add_messages]

# =====================================================================
# 3. Khởi tạo LLM và Tools
# =====================================================================
tools_list = [search_flights, search_hotels, calculate_budget]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # Set temperature=0 để AI trả lời ổn định hơn
llm_with_tools = llm.bind_tools(tools_list)

# =====================================================================
# 4. Agent Node
# =====================================================================
def agent_node(state: AgentState):
    messages = state["messages"]
    
    # Inject System Prompt vào đầu list tin nhắn nếu chưa có
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    # Gọi LLM
    response = llm_with_tools.invoke(messages)
    
    # === LOGGING CHẨN ĐOÁN (Theo yêu cầu của Lab) ===
    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"\n[SYSTEM] Agent quyết định gọi tool: {tc['name']}({tc['args']})")
    else:
        print(f"\n[SYSTEM] Agent trả lời trực tiếp cho người dùng.")
        
    return {"messages": [response]}

# =====================================================================
# 5. Xây dựng Graph (Phần quan trọng nhất)
# =====================================================================
builder = StateGraph(AgentState)

# Thêm 2 node chính vào đồ thị
builder.add_node("agent", agent_node)
tool_node = ToolNode(tools_list)
builder.add_node("tools", tool_node)

# --- TODO: Khai báo edges (Các cạnh nối) ---

# Bắt đầu đồ thị: Luôn đi vào node "agent" đầu tiên
builder.add_edge(START, "agent")

# Từ "agent", dùng tools_condition để kiểm tra:
# - Nếu AI có gọi tool -> tự động đi tới node "tools"
# - Nếu AI không gọi tool -> tự động đi tới END (kết thúc vòng lặp)
builder.add_conditional_edges("agent", tools_condition)

# Sau khi node "tools" chạy xong và trả về kết quả, 
# BẮT BUỘC phải quay lại "agent" để AI đọc kết quả tool và phân tích tiếp
builder.add_edge("tools", "agent")

# --- KẾT THÚC TODO ---

# Compile (đóng gói) đồ thị thành một object có thể thực thi
graph = builder.compile()

# =====================================================================
# 6. Chat loop
# =====================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("TravelBuddy - Trợ lý Du lịch Thông minh")
    print("Gõ 'quit', 'exit' hoặc 'q' để thoát")
    print("=" * 60)
    
    while True:
        user_input = input("\nBạn: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Tạm biệt! Hẹn gặp lại.")
            break
            
        if not user_input:
            continue
            
        print("\nTravelBuddy đang suy nghĩ...")
        
        # Invoke graph với input của người dùng
        result = graph.invoke({"messages": [("human", user_input)]})
        
        # Lấy tin nhắn cuối cùng (câu trả lời cuối cùng của Agent)
        final_message = result["messages"][-1]
        
        print(f"\nTravelBuddy:\n{final_message.content}")