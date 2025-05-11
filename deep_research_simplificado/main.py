from workflow import graph

from dotenv import load_dotenv
load_dotenv()

resposta = graph.invoke(
    {"topico_de_pesquisa": "Me dê uma pesquisa profunda sobre o novo papa eleito hoje",
     "contador_loop_pesquisa": 0,
     "consulta_de_pesquisa_web": "",
     "resultados_web": [],
     "fontes": [],
     "sumario_da_pesquisa": [],
     "resultado_final": "",
     "max_loop_pesquisa": 2,
     })

print(resposta["resultado_final"])