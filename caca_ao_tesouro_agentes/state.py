from typing import TypedDict, List, Dict

class EstadoJogo(TypedDict):
    # Configuração inicial
    tema: str
    dificuldade: str
    proximo: str  # Qual é o agente que realiza a proxima ação

    # Estado do jogo
    locais: List[str]  # Lista de locais na caça ao tesouro
    local_atual: int  # Índice do local atual (0, 1, 2...)
    turno: int
    enigmas: Dict[int, Dict]  # Enigmas para cada local {0: {"pergunta": "...", "resposta": "..."}}

    # Interação
    resposta_jogador: str  # Resposta fornecida pelo agente jogador
    mensagem_sistema: str  # Mensagem exibida para o usuário humano
    jogo_completo: bool  # Indica se o jogo terminou

