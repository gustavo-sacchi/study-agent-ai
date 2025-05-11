import operator
from typing_extensions import Annotated, TypedDict

# Definindo o state que será utilizado pelos nós do grafo
class EstadoFluxoPrincipal(TypedDict):
    topico_de_pesquisa: str
    consulta_de_pesquisa_web: str
    resultados_web: Annotated[list, operator.add]
    fontes: Annotated[list, operator.add]
    contador_loop_pesquisa: int
    max_loop_pesquisa: int
    sumario_da_pesquisa: Annotated[list, operator.add]
    resultado_final: str

