import os
from langchain_qdrant import QdrantVectorStore

from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.tools import tool
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, AnyMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.prebuilt import  ToolNode

from dotenv import load_dotenv
load_dotenv()

## Instanciando um banco de dados. Para facilitar estarei utilizando um SQLite.
# Para outros bancos de dados convido você a pesquisar como criar conexão com seu banco de dados de preferência.
# Sugestão - canal Programador Lhama: https://youtube.com/playlist?list=PLAgbpJQADBGKbwhOvd9DVWy-xhA1KEGm1&si=SbWxZnnmdpzYGIrd

# Banco SQLite:
db = SQLDatabase.from_uri("sqlite:///filmes.db")

# Banco de Dados Vetorial:
db_vetorial = QdrantVectorStore.from_existing_collection(
        collection_name="criticas_filme",
        url=os.environ.get("QDRANT_URL"),
        embedding= OpenAIEmbeddings(model="text-embedding-3-large"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )

db_retriever = db_vetorial.as_retriever(search_kwargs={'k': 2})

# -------------------------------------------------------------------------------------------------------------------

# Definindo um estado:
class MeuEstado(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    question: str
    query: str


# -------------------------------------------------------------------------------------------------------------------

# Conjunto de tools:

# Criando a tool de retriever:
from langchain.tools.retriever import create_retriever_tool

retriever_tool = create_retriever_tool(
    db_retriever,
    "retrieve_filme_critica",
    "Utilizar essa ferramenta quando o usuário solicitar uma critica sobre o filme 'The Shawshank Redemption' (Título em português: Um Sonho de Liberdade).",
)


# Tool responsável por executar uma query no banco SQLite
@tool
def executa_query_banco_dados(query: Annotated[str, "query que será executada no banco de dados"]):
    """Utilize para realizar a consulta no banco de dados."""
    try:
        resposta = db.run(query)
        return f"Resultado da consulta: {resposta}"

    except Exception as e:
        return f"Erro ao executar query no banco de dados. Mensagem do erro: {e}"


# Tool responsável por gerar uma query para banco SQLite
@tool
def gerador_de_query(pergunta_usuario: Annotated[str, "colocar aqui a solicitação do usuário"],
                     se_erro: Annotated[Optional[str], "Colocar aqui a mensagem do erro se ocorrer"] = ""):
    """Utilizar para construir uma consulta SQL para um banco SQLite que contém informações sobre filmes"""

    class Query(BaseModel):
        query: str = Field(description="query para ser executada no banco SQLite")

    prompt_sistema ="""Você é um especialista em SQL com grande atenção aos detalhes.
Dada uma pergunta de entrada, crie uma consulta **SQLite** sintaticamente correta para ajudar a encontrar a resposta.

A menos que o usuário especifique um número específico de exemplos que deseja obter, sempre limite sua consulta a no máximo 10 resultados. 
Você pode ordenar os resultados por uma coluna relevante para retornar os exemplos mais interessantes do banco de dados.

Se o usuário solicitar todos os registros, limite-se a no máximo 100 resultados.

Nunca consulte todas as colunas de uma tabela, apenas selecione as colunas mais relevantes com base na pergunta.

Certifique-se de usar apenas os nomes das colunas que estão descritos no esquema da base de dados. 
Tenha cuidado para não consultar colunas que não existem e para não confundir quais colunas pertencem a quais tabelas.

# Lembre-se das boas práticas em banco de dados:
## Casos de erros mais comuns:
- Uso de **NOT IN** com valores **NULL**  
- Uso de **UNION** quando **UNION ALL** deveria ter sido utilizado  
- Uso de **BETWEEN** para intervalos exclusivos  
- Incompatibilidade de tipos de dados em predicados  
- Uso correto de aspas em identificadores  
- Uso do número correto de argumentos em funções  
- Conversão para o tipo de dado correto (**casting**)  
- Uso das colunas adequadas em **JOINs**  

## É interessante sempre trabalhar com a chave primária quando realizar os joins entre tabela. Por exemplo, \
se o usuário solicitar a nota de um determinado filme, primeiro descobrir o ID e usar ele para consultar a outra tabela.

## Você NÃO DEVE criar consultas de DELETE, UPDATE e INSERT. APENAS USE SELECT.

Use somente as seguintes tabelas e colunas:
1) 'ratings': Tabela que contém as avaliações sobre os filmes.
1.1) 'tconst': ID do filme (chave primária).
1.2) 'averageRating': Nota média de todos os votos.
1.2) 'numVotes': Número de votos.
2) 'titles': tabela principal que contem as informações básicas dos filmes cadastrados no banco de dados. As colunas dessa tabela são:
2.1) 'tconst': ID do filme (chave primária).
2.1) 'titleType': Tipo do título (titleType, short, movie, tvShort, tvMovie, tvEpisode, tvSeries, tvMiniSeries, tvSpecial, video, videoGame etc...)
2.2) 'primaryTitle': Nome principal do filme, série, jogo ou qualquer título cadastrado.
2.2) 'originalTitle': Titulo Original
2.2) 'isAdult': Se é (1) ou não (0) filme adulto.
2.2) 'startYear': Ano de lançamento do título.
2.2) 'runtimeMinutes': tamanho do filme em minutos
2.2) 'genres': Gêneros do título, separados por vírgula.

Solicitação do Usuário: {question}

Se tiver acontecido um erro na execução da query, ele aparecerá a seguir. Se não, ocorreu tudo bem:
{se_erro}
"""

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    chat_prompt_template = ChatPromptTemplate([("system", prompt_sistema)])

    model_with_structured_output = model.with_structured_output(Query)

    chain = chat_prompt_template | model_with_structured_output

    response = chain.invoke({"question": pergunta_usuario, "se_erro": se_erro})

    return response.query

# -------------------------------------------------------------------------------------------------------------------

# Definindo um modelo para o agente:
model_agent = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Acoplnado as tools ao modelo para conhecimento dele:
model_agent_tool = model_agent.bind_tools([gerador_de_query, executa_query_banco_dados, retriever_tool])

# -------------------------------------------------------------------------------------------------------------------

# Definindo as funções de nós:

def agent(state: MeuEstado):
    system_message = SystemMessage("""Você é um agente de IA com as seguintes tarefas: \

1) Você tem como objetivo responder ao usuário sobre informações de filmes, 
2) Para você obter dados sobre os filmes, você tem uma ferramenta que realiza consultas em um banco de dados 'filmes.db' a partir de uma query.
3) Você também tem um ferramenta capaz de criar query para ser executada no banco de dados.
4) Se ocorrer algum erro na execução do banco de dados, tente chamar novamente a ferramenta que gera query, informando o erro ocorrido.
5) Se ocorrer 2 tentativas com erro, avise o usuário que estamos com problema e finalize.

6) Se o usuário te pedir uma critica sobre 'The Shawshank Redemption' (Título em português: Um Sonho de Liberdade), use a ferramenta de recuperação de informação por similaridade em banco vetorial: 'retrieve_filme_critica'.

Atenção:
- Seja proativo, ajude o usuário informando suas habilidades,
- Dê sempre respostas completas, e se necessário, use tabelas quando tiver que informar dados estrutudados.
""")

    response = model_agent_tool.invoke([system_message] + state["messages"])

    return {"messages": [response]}

# Definido a rota de escolha do LLM
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]

    if not last_message.tool_calls:
        return END
    else:
        return "ferramentas"


# -------------------------------------------------------------------------------------------------------------------

# Definindo nosso grafo:

workflow = StateGraph(MeuEstado)

## Definindo os nós:

workflow.add_node("agent", agent)
workflow.add_node("ferramentas", ToolNode([gerador_de_query, executa_query_banco_dados, retriever_tool]))

## Definindo nossas arestas e aresta condicional:

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("ferramentas", "agent")

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

# solicitacao = "Oi Tudo bem?"
# solicitacao = "Tem quantos filmes do homem aranha?"
# solicitacao = "Tem quantos filmes do homem aranha? E qual tem maior nota?"
# solicitacao = "Qual é a duração do filme The Shawshank Redemption"
solicitacao = "Pode me dar algumas avaliações/criticas que as pessoas fazem do filme Um Sonho de Liberdade?"


for event in graph.stream({"messages": HumanMessage(content=solicitacao), "question":solicitacao, "query":""}, stream_mode="values"):
    event["messages"][-1].pretty_print()


# https://www.imdb.com/pt/title/tt0111161/?ref_=tturv_ov