from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

@tool
def adicao(a: int, b: int):
    """ função que realiza a adição de 2 números inteiros """
    return a + b


llm = ChatGroq(model = "qwen-qwq-32b", temperature = 0.3)

llm_tools = llm.bind_tools([adicao])

# Invoke do modelo sem tool:
resposta1 = llm_tools.invoke(
    [SystemMessage(content="Voce é um assistente para auxiliar o usuário a responder perguntas de somar."),
     HumanMessage(content="Oi Tudo bem?")])
print(f"Resposta 1 - tool_calls = {resposta1.tool_calls} \n content= {resposta1.content}")

# Invoke do modelo com tool:
resposta2 = llm_tools.invoke(
    [SystemMessage(content="Voce é um assistente para auxiliar o usuário a responder perguntas de somar."),
     HumanMessage(content="Quanto é 10 + 11")])
print(f"Resposta 2 - tool_calls = {resposta2.tool_calls} \n content= {resposta2.content}")