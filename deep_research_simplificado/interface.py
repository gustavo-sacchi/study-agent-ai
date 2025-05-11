import chainlit as cl
from workflow import graph


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Papa Atual",
            message="Poderia entregar uma pesquisa sobre o atual papa eleito?",
            ),

        cl.Starter(
            label="Desafios Tecnologia",
            message="É sabido hoje que inteligência artificial está sendo bastante divulgada, poderia me entregar uma pesquisa focando nos desafios encontrados pelas empresas na adoção de IA em seus processos? Seja detalhado e forneça dados quantitativos também.",
            ),
        ]


@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id}}

    resposta = await graph.ainvoke(
        {"topico_de_pesquisa": msg.content,
         "contador_loop_pesquisa": 0,
         "consulta_de_pesquisa_web": "",
         "resultados_web": [],
         "fontes": [],
         "sumario_da_pesquisa": [],
         "resultado_final": "",
         "max_loop_pesquisa": 2,
         }, config=config)
    await cl.Message(content=resposta["resultado_final"]).send()
