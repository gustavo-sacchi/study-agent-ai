from datetime import datetime
from pydantic import BaseModel, Field
from typing_extensions import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph

from funcoes_auxiliadoras import duckduckgo_pesquisa, formata_texto_pesquisado
from state import EstadoFluxoPrincipal


# ---------------------------------------------------------------------------
# ------------------ Criando nosso Fluxo: -----------------------------------
# ---------------------------------------------------------------------------

# ----> Nós de LangGraph
def no_gerador_da_consulta_web(state: EstadoFluxoPrincipal):
    """Nó LangGraph que gera uma consulta de pesquisa web usando LLM com base no tópico de entrada do usuário."""
    print("===> Passando pelo Nó: no_gerador_da_consulta_web")

    # Prompt de sistema que orienta o LLM a criar uma consulta de pesquisa web.
    prompt_gera_query_de_pesquisa="""\
# Papel: 
Você é um pesquisador experiente com habilidade de realizar pesquisas sobre diferentes temas.

# Objetivo
Seu objetivo é gerar uma consulta de pesquisa web direcionada sobre o tema enviado pelo usuário. Ela será util para a criação de uma pesquisa profunda sobre o tema.

# Contexto
- A Data atual é: {data_atual}

# Atenção
- Certifique-se de que suas consultas considerem as informações mais atualizadas disponíveis até esta data.

# Tema
Tópico de pesquisa enviada pelo usuário: '{topico_de_pesquisa}'

# Tarefa:
De forma estruturada, gere uma consulta de pesquisa capaz de retornar fontes de alta qualidade sobre o tema solicitado."""

    # Estrutura da saida esperada:
    class ConsultaPesquisa(BaseModel):
        consulta: str = Field(description="A string da consulta de pesquisa propriamente dita")
        racional: str = Field(description="Explicação breve de por que essa consulta é relevante")

    # criando o prompt formatando as variáveis de data e tópico de pesquisa
    prompt_formatado = prompt_gera_query_de_pesquisa.format(
        data_atual=datetime.now().strftime("%d/%m/%Y"),
        topico_de_pesquisa=state["topico_de_pesquisa"]
    )

    # Criando um chatmodel com saida estruturada:
    llm_gera_consulta = ChatOpenAI(model='gpt-4o-mini', temperature=0.1)
    llm_gera_consulta_estruturado = llm_gera_consulta.with_structured_output(ConsultaPesquisa)

    # invocando o modelo com a lista de mensagens formada apenas pelo system prompt
    resultado = llm_gera_consulta_estruturado.invoke([SystemMessage(content=prompt_formatado)])

    return {"consulta_de_pesquisa_web": resultado.consulta}

def no_realiza_pesquisa(state: EstadoFluxoPrincipal):
    """Nó do LangGraph que realiza pesquisa na web usando duckduckgo utilizando a consulta de busca gerada pelo nó anterior."""
    print("===> Passando pelo Nó: no_realiza_pesquisa")

    # Chamando a função que realiza a pesquisa:
    resultados_pesquisados = duckduckgo_pesquisa(state["consulta_de_pesquisa_web"])

    # Formatando o texto pesquisado
    texto_completo_pesquisado = formata_texto_pesquisado(resultados_pesquisados)

    # Organizando as Referências Bibliográficas:
    linhas_formatadas = []
    for referencia_pesquisada in resultados_pesquisados['resultados']:
        linha = "* " + referencia_pesquisada['titulo'] + " : " + referencia_pesquisada['url']
        linhas_formatadas.append(linha)

    referencia_pesquisada_formatada = '\n'.join(linhas_formatadas)

    return {"fontes": [referencia_pesquisada_formatada], "contador_loop_pesquisa": state["contador_loop_pesquisa"] + 1,
            "resultados_web": [texto_completo_pesquisado]}

def no_realiza_resumo_texto_pesquisado(state: EstadoFluxoPrincipal):
    """Nó do LangGraph que resume e organiza os resultados de pesquisas na web para enviar ao nó que constrói o
    relatório de pesquisa profunda."""
    print("===> Passando pelo Nó: no_realiza_resumo_texto_pesquisado")

    llm_gera_sumario = ChatOpenAI(model='gpt-4o', temperature=0.3)

    prompt_sistema_sumarizador="""\
# Papel:
Aja como um especialista em processamento de linguagem natural com 15 anos de experiência em \
resumo automático de textos técnicos, acadêmicos e corporativos. Sua tarefa é analisar documentos \
extensos e gerar resumos estruturados, claros e objetivos, mantendo os pontos-chave, a ordem lógica \
e a integridade do conteúdo original

# Objetivo:
Gerar um resumo de alta qualidade com base no contexto fornecido.
Quero um resumo coerente, fiel ao documento original e de alta qualidade, que destaque as principais ideias, \
argumentos, dados e conclusões. O resumo deve ser útil para alguém que não leu o documento completo, mas precisa \
compreendê-lo rapidamente.

# Requisitos
Ao criar um NOVO resumo:
1. Destaque as informações mais relevantes relacionadas ao tema do usuário a partir dos resultados da pesquisa.
2. Garanta um fluxo coerente das informações.

# Instruções detalhadas:
1. Leia cuidadosamente todo o conteúdo do documento fornecido.
2. Identifique os tópicos centrais, subtópicos relevantes, dados numéricos, resultados e conclusões.
3. Elimine repetições, detalhes irrelevantes ou informações secundárias que não comprometam o entendimento geral.
4. Organize o resumo em seções, SOMENTE SE o documento original também seja dividido (ex: Introdução, Metodologia, Resultados, Conclusão).
5. Use linguagem clara, técnica (se necessário), objetiva e impessoal.
6. Garanta um fluxo coerente das informações.
7. O resumo deve ter entre 15% e 30% do tamanho do texto original.

# Atenção: 
- Comece diretamente com o resumo atualizado, sem introduções ou títulos. Não use tags XML na saída.
- Pense cuidadosamente sobre o Contexto fornecido antes. Em seguida, gere um resumo do contexto que responda à Solicitação do Usuário."""

    prompt_humano = f"""\
# Contexto Pesquisado:
<contexto>
{state["resultados_web"][-1]}
</contexto>
# Tarefa:
Com base no contexto presente entre as tags <contexto></contexto>, crie um sumário NOVO com este tópico de pesquisa solicitado:
{state["topico_de_pesquisa"]}"""

    # Fazendo a invocação ao modelo
    resposta = llm_gera_sumario.invoke(
        [SystemMessage(content=prompt_sistema_sumarizador),
         HumanMessage(content=prompt_humano)]
    )

    return {"sumario_da_pesquisa": [resposta.content]}

def no_analista_resultado_relatorio(state: EstadoFluxoPrincipal):
    """Nó do LangGraph que identifica lacunas de conhecimento e gera consultas para buscar novas informações na web."""
    print("===> Passando pelo Nó: no_analista_resultado_relatorio")

    # Estrutura da saida esperada:
    class AnalistaPesquisa(BaseModel):
        gap_de_conhecimento: str = Field(description="Descreva qual informação está faltando ou precisa de esclarecimento")
        consulta_nova: str = Field(description="Escreva uma pergunta específica para abordar essa lacuna")


    prompt_analista_lacunas_pesquisa = f"""\
# Papel:
Você é um assistente de pesquisa especialista analisando um resumo sobre {state["topico_de_pesquisa"]}.

# Objetivo:
1. Identificar lacunas de conhecimento ou áreas que precisam de exploração mais aprofundada  
2. Gerar uma pergunta de acompanhamento que ajude a expandir o entendimento  
3. Focar em detalhes técnicos, especificidades de implementação ou tendências emergentes que não foram totalmente abordadas  

# Atenção:
Certifique-se de que a pergunta de acompanhamento seja autoexplicativa e inclua o contexto necessário para uma busca na web.

# Tarefa:
Reflita cuidadosamente sobre o conteúdo presente em 'Resumo' para identificar lacunas de conhecimento e produza uma pergunta de acompanhamento.

## Resumo:
Reflita sobre o nosso conhecimento existente:
===
{state["resultado_final"]}
===
E agora identifique uma lacuna de conhecimento e gere uma consulta de pesquisa na Web de acompanhamento."""
    # Criando um chatmodel com saida estruturada:
    llm_gera_consulta_acompanhamento = ChatOpenAI(model='gpt-4o-mini', temperature=0.2)
    llm_gera_consulta_acompanhamento_estruturado = llm_gera_consulta_acompanhamento.with_structured_output(AnalistaPesquisa)

    # invocando o modelo com a lista de mensagens formada apenas pelo system prompt
    resultado = llm_gera_consulta_acompanhamento_estruturado.invoke([SystemMessage(content=prompt_analista_lacunas_pesquisa)])

    return {"consulta_de_pesquisa_web": f"Fale-me mais sobre  {resultado.consulta_nova}"}

def no_pesquisa_profunda_final(state: EstadoFluxoPrincipal):
    """Nó do LangGraph que cria o relatório final da pesquisa profunda. Recebe como insumo o resumo gerado pelo
    nó 'no_realiza_resumo_texto_pesquisado'"""
    print("===> Passando pelo Nó: no_pesquisa_profunda_final")

    # Criando e usando um modelo maior apra construir a resposta final.
    llm_gera_sumario_final = ChatOpenAI(model='gpt-4o', temperature=0.3)

    if not state["resultado_final"]:
        pesquisa_profunda ="[Pesquisa profunda não iniciada!]"
    else:
        pesquisa_profunda = state["resultado_final"]

    prompt_deep_research =f"""\
# Papel: 
Aja como um pesquisador acadêmico altamente qualificado e experiente. Você tem mais de 20 anos de experiência na \
elaboração de pesquisas aprofundadas a partir de múltiplas fontes. Sua especialidade é coletar, interpretar e organizar \
informações dispersas (como resumos, trechos e anotações) em uma pesquisa robusta, lógica e bem estruturada.

# Objetivo: 
A partir de múltiplos resumos fornecidos, você deve criar um documento de pesquisa profunda utilizando (se existir) o 
documento inicialmente escrito seguindo os requisitos presentes no item '# Requisitos', tal que a pesquisa final seja 
clara, detalhada, bem argumentada e com uma linha narrativa consistente. A pesquisa final deve ser adequada para 
apresentação acadêmica, com início, desenvolvimento e conclusão.

# Instruções:
- Analise todos os resumos apresentados no item '# Conteúdo das pesquisas realizadas pelo usuário'. Extraia as ideias centrais de cada um.
- Agrupe as ideias semelhantes por temas ou subtemas.
- Elabore uma introdução apresentando o contexto geral do tema tratado.
- Desenvolva os principais tópicos da pesquisa a partir dos resumos, aprofundando cada um com base nas ideias fornecidas e conectando-as de maneira coesa.
- Onde faltar conteúdo, utilize inferência lógica e generalizações acadêmicas para expandir os argumentos.
- Conclua com uma síntese das ideias principais, apontando implicações, lacunas e possíveis caminhos para estudos futuros.
- Certifique-se de que a linguagem esteja em tom acadêmico, fluido e profissional.

# Requisitos:
## Regras caso NÃO EXISTA uma pesquisa profunda previamente iniciada:
1. Destaque as informações mais relevantes relacionadas ao tema do usuário a partir dos resultados da pesquisa.
2. Garanta um fluxo coerente das informações.

## Regras caso JÀ EXISTA uma pesquisa profunda previamente iniciada:
1. Leia atentamente o resumo atual e os novos resultados da pesquisa.
2. Compare as novas informações com o resumo já existente.
3. Para cada nova informação:
    a. Se estiver relacionada a pontos já existentes, integre-a ao parágrafo correspondente.
    b. Se for totalmente nova, mas relevante, adicione um novo parágrafo com uma transição suave.
    c. Se não for relevante ao tema do usuário, ignore-a.
4. Certifique-se de que todas as adições são pertinentes ao tema do usuário.
5. Verifique se sua saída final é diferente do resumo de entrada.

## Formato de saída desejado para a pesquisa profunda:
- Título da pesquisa
- Introdução
- Corpo da pesquisa (dividido em subtópicos com títulos)
- Conclusão

# Importante: 
- A pesquisa deve conter no mínimo 1000 palavras e estar organizada de forma lógica, fluida e informativa, mantendo coesão e progressão temática.

# Atenção:
- Se existir uma pesquisa profunda ela estará presente entre as tags <pesquisa_profunda_iniciada></pesquisa_profunda_iniciada>

# Conteúdo das pesquisas realizadas pelo usuário:
{state["sumario_da_pesquisa"][-1]}

# Pesquisa profunda se existir:
<pesquisa_profunda_iniciada>
{pesquisa_profunda}
</pesquisa_profunda_iniciada>

Respire fundo e resolva este problema passo a passo."""

    resposta = llm_gera_sumario_final.invoke([SystemMessage(content=prompt_deep_research)])
    return {"resultado_final": resposta.content}

def no_inclui_fontes_na_resposta(state: EstadoFluxoPrincipal):
    """Nó que só inclui no final da pesquisa profunda todas as fontes utilizadas."""

    print("===> Passando pelo Nó: no_inclui_fontes_na_resposta")
    fontes_visitadas= set()
    fontes_unidas = []
    for fonte in state["fontes"]:
        for linha in fonte.split('\n'):
            if linha.strip() and linha not in fontes_visitadas:
                fontes_visitadas.add(linha)
                fontes_unidas.append(linha)
    todas_as_fontes = "\n".join(fontes_unidas)
    relatorio_final = f"""# Pesquisa Profunda finalizada sobre o tópico:\n\n"{state['topico_de_pesquisa']}"\n\n---\n\n{state['resultado_final']}\n\n---\n\n# Referências Bibliográficas:\n\n{todas_as_fontes}"""
    return {"resultado_final": relatorio_final}

def no_rota(state: EstadoFluxoPrincipal) -> Literal["no_inclui_fontes_na_resposta", "no_realiza_pesquisa"]:
    """Nó de roteamento do LangGraph entre pesquisar mais informações ou finalizar."""
    if state["contador_loop_pesquisa"] <= state["max_loop_pesquisa"]:
        print("===> Passando pelo Nó: no_rota | Opção: Seguir para -> no_realiza_pesquisa")
        return "no_realiza_pesquisa"
    else:
        print("===> Passando pelo Nó: no_rota | Opção: Seguir para -> no_inclui_fontes_na_resposta")
        return "no_inclui_fontes_na_resposta"


# Inicializando o Grafo
builder = StateGraph(EstadoFluxoPrincipal)

# Adicionando os nós:
builder.add_node("no_gerador_da_consulta_web", no_gerador_da_consulta_web)
builder.add_node("no_realiza_pesquisa", no_realiza_pesquisa)
builder.add_node("no_realiza_resumo_texto_pesquisado", no_realiza_resumo_texto_pesquisado)
builder.add_node("no_analista_resultado_relatorio", no_analista_resultado_relatorio)
builder.add_node("no_pesquisa_profunda_final", no_pesquisa_profunda_final)
builder.add_node("no_inclui_fontes_na_resposta", no_inclui_fontes_na_resposta)

# Adicionando as arestas:
builder.add_edge(START, "no_gerador_da_consulta_web")
builder.add_edge("no_gerador_da_consulta_web", "no_realiza_pesquisa")
builder.add_edge("no_realiza_pesquisa", "no_realiza_resumo_texto_pesquisado")
builder.add_edge("no_realiza_resumo_texto_pesquisado", "no_pesquisa_profunda_final")
builder.add_edge("no_pesquisa_profunda_final", "no_analista_resultado_relatorio")
builder.add_conditional_edges("no_analista_resultado_relatorio", no_rota)
builder.add_edge("no_inclui_fontes_na_resposta", END)

# Compilando o grafo:
graph = builder.compile()

# Plotando a imagem do fluxo:
# import io
# from PIL import Image
# img_bytes = graph.get_graph(xray=1).draw_mermaid_png()
# img = Image.open(io.BytesIO(img_bytes))
# img.save('diagrama_workflow.png')
# img.show()

