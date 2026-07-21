from langchain.agents import create_agent
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch

from langgraph.checkpoint.memory import MemorySaver
from utils.db_handler import DB_PATH
from langgraph.checkpoint.sqlite import SqliteSaver


class ReactAgent:
    def __init__(self):
        # 核心修复：SqliteSaver.from_conn_string 是一个上下文管理器
        # 我们需要在 __init__ 中保持连接开启，或者在每次调用时开启
        # 这里采用一种兼容性更强的方式，直接创建实例
        self.saver = SqliteSaver.from_conn_string(DB_PATH)

        # 由于 create_agent 内部需要直接访问 checkpointer，
        # 我们手动进入上下文管理器获取真正的 saver 实例
        self.actual_saver = self.saver.__enter__()

        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
            checkpointer=self.actual_saver  # 使用进入上下文后的实例
        )

    def __del__(self):
        # 对象销毁时关闭数据库连接
        if hasattr(self, 'saver'):
            self.saver.__exit__(None, None, None)

    def execute_stream(self, query: str, thread_id: str = "user001"):
        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}, config=config):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"

if __name__ == '__main__':
    agent = ReactAgent()

    print("第一轮对话")
    for chunk in agent.execute_stream("我所在城市的天气怎么样"):
        print(chunk, end="", flush=True)

    print("第一轮对话")
    for chunk in agent.execute_stream("我叫老李，有一只猫"):
        print(chunk, end="", flush=True)

    print("第二轮对话")
    for chunk in agent.execute_stream("我有两只狗"):
        print(chunk, end="", flush=True)

    print("第三轮对话")
    for chunk in agent.execute_stream("我60岁，综合我的情况，有推荐的型号吗,"):
        print(chunk, end="", flush=True)
    #
    # print("第四轮对话")
    # for chunk in agent.execute_stream("生成我的使用报告,"):
    #     print(chunk, end="", flush=True)
    #
    # print("第五轮对话")
    # for chunk in agent.execute_stream("我还有一只鹦鹉,"):
    #     print(chunk, end="", flush=True)
    #
    # print("第六轮对话")
    # for chunk in agent.execute_stream("我是谁，多少岁,我有几个宠物，生成我的使用报告"):
    #     print(chunk, end="", flush=True)
