import os
from typing import Annotated, Sequence, TypedDict

from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END, add_messages, START
from langgraph.prebuilt import ToolNode

from langchain_core.messages import SystemMessage, AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from dotenv import load_dotenv
load_dotenv()

# ===========================================================
# Opção 1
# ===========================================================

## Definindo as Tools:
@tool
def pega_dados_clima(cidade: Annotated[str, "nome da cidade que se deseja obter informações climáticas."]):
    """Ferramenta para obter dados meteorológicos da API OpenWeatherMap."""
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
    API_KEY = os.getenv("API_KEY")

    import requests
    request_url = f"{BASE_URL}?appid={API_KEY}&q={cidade}"

    try:
        response = requests.get(request_url)
        response.raise_for_status()

        data = response.json()
        dados_clima = {
            "weather": data.get('weather', [{}])[0].get("description", "N/A"),
            "wind_speed": data.get("wind", {}).get("speed", "N/A"),
            "cloud_cover": data.get("clouds", {}).get("all", "N/A"),
            "sea_level": data.get("main", {}).get("sea_level", "N/A"),
            "temperature": round(data.get("main", {}).get("temp", 273.15) - 273.15, 1),
            "humidity": data.get("main", {}).get("humidity", "N/A"),
            "pressure": data.get("main", {}).get("pressure", "N/A")
        }

        return f"Dados Climáticos: {dados_clima}"

    except Exception as e:
        error_data = {
            "weather": "N/A",
            "wind_speed": "N/A",
            "cloud_cover": "N/A",
            "sea_level": "N/A",
            "temperature": "N/A",
            "humidity": "N/A",
            "pressure": "N/A"
        }
        return f"Dados Climáticos: {error_data}. Falha ao buscar dados meteorológicos para {cidade}. Erro: {str(e)}"

# Cria a lista de ferramentas:
tools = [pega_dados_clima]

## Definindo o State:
class AgentState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]


## Escolhendo um modelo que permite chamada à função:
model = ChatOpenAI(model="gpt-4o-mini")


## Acoplando as ferramentas ao modelo para que ele conheça quais são as disponíveis!
model_bind_tool = model.bind_tools(tools)

# Nó de chamada ao LLM
def call_model(state: AgentState, config: RunnableConfig):
    system_prompt = SystemMessage("Você é um agente de IA que possui uma ferramenta de dados climáticos. Quando o usuário solicitar informações de clima para uma determinada cidade, escolha ela para usar.")
    response = model_bind_tool.invoke([system_prompt] + state["messages"], config)
    return {"messages": [response]}


# Nó de roteamento
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    else:
        return "no_ferramenta"

# Definindo nosso grafo:

workflow = StateGraph(AgentState)

## Definindo os nós:

workflow.add_node("agent", call_model)
workflow.add_node("no_ferramenta", ToolNode(tools))

## Definindo nossa aresta condicional:
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("no_ferramenta", "agent")

## Compilando nosso grafo
graph = workflow.compile()

## Plotando a imagem:

# import io
# from PIL import Image
#
# # Supondo que graph.get_graph().draw_mermaid_png() retorne os bytes da imagem PNG:
# img_bytes = graph.get_graph(xray=1).draw_mermaid_png()
#
# # Cria um objeto Image a partir dos bytes:
# img = Image.open(io.BytesIO(img_bytes))
#
# # Exibe a imagem em uma janela separada:
# img.show()

# Invocando nosso grafo. Sabemos que o State é uma base de mensagens então precisamos enviar uma mensagem um dicionário com um BaseMessage:

for event in graph.stream({"messages": HumanMessage(content="Oi tudo bem?")}, stream_mode="values"):
    event["messages"][-1].pretty_print()


# ===========================================================
# Opção 2
# ===========================================================

# from langgraph.prebuilt import create_react_agent
#
#
# agente = create_react_agent(model=model, tools=tools, prompt="Você é um agente de IA que possui uma ferramenta de dados climáticos. Quando o usuário solicitar informações de clima para uma determinada cidade, escolha ela para usar.")
#
# for event in agente.stream({"messages": HumanMessage(content="Qual é a temperatura atual em São Paulo?")}, stream_mode="values"):
#     event["messages"][-1].pretty_print()
