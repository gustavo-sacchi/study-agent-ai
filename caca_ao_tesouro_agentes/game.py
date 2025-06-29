from pydantic import BaseModel, Field
from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START

import time

from state import EstadoJogo

from dotenv import load_dotenv
load_dotenv()

# Modelo de linguagem para todos os agentes
modelo = ChatOpenAI(model="gpt-4o", temperature=0.7)


# Funções uteis:
def extrair_texto_pos_thinking(texto: str) -> str:
    fechamento = "</thinking>"

    if fechamento in texto:
        # Posição onde termina o último </thinking>
        pos = texto.rfind(fechamento) + len(fechamento)
        return texto[pos:].strip()
    else:
        print(">>> </thinking> não encontrado!")
        # Nenhuma tag encontrada, retorna o texto inteiro (ou vazio, conforme quiser)
        return texto.strip()


# Nó Criador: Gera o conteúdo do jogo
def inicializar_jogo(estado: EstadoJogo):
    """Cria os locais e enigmas do jogo baseado no tema e dificuldade"""

    class Enigmas(BaseModel):
        pergunta: str = Field(description="pergunta do enigma")
        resposta: str = Field(description="resposta do enigma")

    class FasesJogo(BaseModel):
        locais: list[str] = Field(description="Lista com 3 locais sendo o ultimo denominado 'Tesouro'")
        enigmas: list[Enigmas]


    prompt = f"""\
Crie uma mini caça ao tesouro com tema '{estado['tema']}' e dificuldade '{estado['dificuldade']}'.

Forneça:
1. Uma lista de 3 locais (o último deve ser chamado "Tesouro")
2. Um enigma simples para cada local (exceto o último)
3. A resposta para cada enigma
Exemplo: 
{{
    "locais": ["Local 1", "Local 2", ...,  "Tesouro"],
    "enigmas": [
        {{"pergunta": "Enigma do Local 1", "resposta": "Resposta 1"}},
        {{"pergunta": "Enigma do Local 2", "resposta": "Resposta 2"}}, ...
    ]
}}"""
    modelo_com_saida_estruturada = modelo.with_structured_output(FasesJogo)

    resposta = modelo_com_saida_estruturada.invoke([HumanMessage(content=prompt)])

    return {
        "locais": resposta.locais,
        "enigmas": resposta.enigmas,
        "local_atual": 0,
        "turno": 0,
        "jogo_completo": False,
        "resposta_jogador": "",
        "mensagem_sistema": f"Jogo criado com tema '{estado['tema']}' e dificuldade '{estado['dificuldade']}'!\n\nVamos começar a caça ao tesouro!",
    }

# Agente Mestre: Coordena o jogo
def agente_mestre(estado: EstadoJogo):
    """Gerencia o fluxo principal do jogo"""

    # Verifica se o jogo foi completado
    if estado["local_atual"] >= len(estado["locais"]) - 1:
        return {"jogo_completo": True,
                "mensagem_sistema": f"Jogo concluído! O tesouro foi encontrado em {estado['locais'][-1]}!",
                "proximo": "__end__"
                }

    # Apresenta o local e enigma atual
    indice_atual = estado["local_atual"]
    local_atual = estado["locais"][indice_atual]
    enigma = estado["enigmas"][indice_atual].pergunta

    # Determina próximo passo
    if "resposta_jogador" in estado and estado["resposta_jogador"]:
        return {"proximo": "assistente", "mensagem_sistema": f"Local atual: {local_atual}\nEnigma: {enigma}"}
    else:
        return {"proximo": "jogador", "mensagem_sistema": f"Local atual: {local_atual}\nEnigma: {enigma}"}

# Agente Jogador: IA que tenta resolver os enigmas
def agente_jogador(estado: EstadoJogo):
    """Agente de IA que tenta resolver os enigmas do jogo"""
    indice_atual = estado["local_atual"]
    enigma_atual = estado["enigmas"][indice_atual].pergunta

    print(f"============================== ")
    print(f"# Local: {estado['locais'][indice_atual]}")
    print(f"# Enigma: {enigma_atual}")
    print(f"# Resposta do Enigma: {estado['enigmas'][indice_atual].resposta}")
    print(f"============================== ")

    # Simula o "pensamento" do agente jogador
    print(f"\033[31m[Agente Jogador está pensando...]\033[0m")
    time.sleep(2)  # Pausa para simular "pensamento"

    # Normalmente o LLM sempre acerta a resposta, então vamos forçar que ele erre sempre o primeiro local para
    # verificarmos o assistente fornecendo uma dica...
    #   I. Forçar o LLM a errar
    #   II. Forçar o LLM a acertar

    if estado["turno"] == 0:
        escolha = 'errar'
    else:
        escolha = 'acertar'

    if 'Dica' in estado["mensagem_sistema"]:
        dica = estado["mensagem_sistema"]
    else:
        dica = ""

    prompt = f"""\
Você é um jogador que está tentando resolver um enigma, pense bastante antes de responder. Para isso siga as instruções:

Instruções:
1) Inicie com uma cadeia de pensamento utilizando as tags de abertura e fechamento: <thinking></thinking>. Utilize \
esse espaço para interpretar o enigma, raciocinar antes de sugerir uma resposta.
2) Quando decidir qual é a resposta que você deseja entregar como solução do enigma, escreva ela após a tag de fechamento </thinking>.
3) Para esta resposta, Você precisa {escolha}!

Enigma: {enigma_atual}

Dê uma resposta plausível.
O mestre Falou: {dica}
"""

    resposta = modelo.invoke([HumanMessage(content=prompt)])

    # print(f">>>>> resposta completa: {resposta.content}")

    resposta_sem_tags_thinking = extrair_texto_pos_thinking(resposta.content)

    print(f"> Solicitamos ao Jogador: 'Você precisa {escolha}'")
    print(f"\033[32m[Agente Jogador]: Hmm, acho que a resposta é '{resposta_sem_tags_thinking}'\033[0m")

    return {"resposta_jogador": resposta_sem_tags_thinking, "turno": estado["turno"]+1}

# Agente Assistente: Avalia respostas e fornece dicas
def agente_assistente(estado: EstadoJogo):
    """Avalia as respostas e fornece dicas quando necessário"""

    indice_atual = estado["local_atual"]
    resposta_jogador = estado["resposta_jogador"]
    resposta_correta = estado["enigmas"][indice_atual].resposta

    class Julgamento(BaseModel):
        resposta: bool = Field(description="A resposta está correta (True) ou incorreta (False)")
        raciocinio: str = Field(description="Raciocínio utilizado para julgar se a resposta para o enigma está correta ou não")

    prompt = f"""\
Um jogador tentou resolver um enigma. Interprete e julgue se a resposta dele está correta ou não. O jogador não \
precisa responder de forma exatamente igual à resposta correta, se ele responder algo parecido, julgue \
como uma resposta correta. Apenas julgue que ele errou se a resposta realmente for muito diferente daquela esperada.

Enigma: {estado["enigmas"][indice_atual].pergunta}
Resposta correta do enigma: {resposta_correta}
Resposta do jogador: {resposta_jogador}

Dê uma dica útil sem revelar a resposta diretamente."""

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    modelo_com_saida_estruturada = llm.with_structured_output(Julgamento)

    resposta = modelo_com_saida_estruturada.invoke([HumanMessage(content=prompt)])

    print(f"\033[33m[Agente Assistente está Julgando a resposta...]\033[0m")
    time.sleep(2)  # Pausa para simular "pensamento"

    # Verifica resposta do julgamento:

    print(f"============================== ")
    print(f"# Julgamento: {resposta.resposta}")
    print(f"# Racicionio: {resposta.raciocinio}")
    print(f"============================== ")

    # Verifica se a resposta está correta (comparação simplificada)
    if resposta.resposta:

        # Mensagem de transição
        proximo_local = estado["locais"][estado["local_atual"]] if estado["local_atual"] < len(estado["locais"]) else "Tesouro"

        print(f"\033[33m[Assistente]: Isso mesmo! A resposta '{resposta_jogador}' está correta!\033[0m")
        time.sleep(1)

        return {
            "local_atual": estado["local_atual"] + 1,
            "resposta_jogador": "",
            "mensagem_sistema": f"Resposta correta! O jogador avança para {proximo_local}."
        }
    else:
        # Fornece uma dica
        prompt = f"""\
Um jogador tentou resolver um enigma e errou.

Enigma: {estado["enigmas"][indice_atual].pergunta}
Resposta correta: {resposta_correta}
Resposta do jogador: {resposta_jogador}

Dê uma dica útil sem revelar a resposta diretamente."""

        resposta = modelo.invoke([HumanMessage(content=prompt)])
        dica = resposta.content

        print(f"\033[33m[Assistente]: Hmm, '{resposta_jogador}' não está certo.\nDica: {dica}\033[0m")

    time.sleep(1)  # Pausa para melhor visualização

    return {
        "resposta_jogador": "",
        "mensagem_sistema": f"Resposta incorreta. Dica: {dica}"
    }


def rota(estado: EstadoJogo) -> Literal["criador", "jogador", "assistente", "__end__"]:
    """ Aresta condicional """
    if estado["proximo"] == "jogador":
        return "jogador"
    elif estado["proximo"] == "assistente":
        return "assistente"
    else:
        return "__end__"


# Construção do grafo com LangGraph
fluxo = StateGraph(EstadoJogo)

# Adiciona os nós (agentes)

fluxo.add_node("inicializar_jogo", inicializar_jogo)

fluxo.add_node("mestre", agente_mestre)
fluxo.add_node("jogador", agente_jogador)
fluxo.add_node("assistente", agente_assistente)

# Define o ponto de entrada
fluxo.add_edge(START, "inicializar_jogo")

# Define as conexões básicas
fluxo.add_edge("inicializar_jogo", "mestre")
fluxo.add_edge("jogador", "mestre")
fluxo.add_edge("assistente", "mestre")

# Adiciona conexões condicionais do agente mestre
fluxo.add_conditional_edges("mestre", rota, {"jogador": "jogador", "assistente": "assistente", "__end__": END})

grafo = fluxo.compile()

# import io
# from PIL import Image
# img_bytes = grafo.get_graph(xray=1).draw_mermaid_png()
# img = Image.open(io.BytesIO(img_bytes))
# img.save('diagrama_workflow_game.png')
# img.show()

# Para executar o jogo com agentes automatizados:
if __name__=="__main__":
    tema="Lugar turístico brasileiro"
    dificuldade= "difícil"

    print(f"\n===== INICIANDO CAÇA AO TESOURO =====")
    print(f"Tema: {tema}")
    print(f"Dificuldade: {dificuldade}")
    print("=====================================\n")

    # Estado inicial
    estado_inicial = {
        "tema": tema,
        "dificuldade": dificuldade,
        "mensagem_sistema": ""}

    estado_in = grafo.invoke(estado_inicial)

    print(f"\n[Sistema]: {estado_in['mensagem_sistema']}")
    print("\n===== FIM DO JOGO =====")