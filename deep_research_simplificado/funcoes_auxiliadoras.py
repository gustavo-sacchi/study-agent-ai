import httpx

from duckduckgo_search import DDGS
from markdownify import markdownify

def formata_texto_pesquisado(resultados_pesquisados):
    """ Recebe o dicionário de resultados pesquisados e retorna um texto formatado."""
    # Organizando as fontes (tirando as duplicatas se aparecer um site repetido):
    fontes_unicas = {}
    for fontes in resultados_pesquisados["resultados"]:
        if fontes['url'] not in fontes_unicas:
            fontes_unicas[fontes['url']] = fontes

    # Texto de saída
    texto_organizado_das_fontes = "# Fontes de Pesquisa:\n\n"
    for ordem_fonte, fonte in enumerate(fontes_unicas.values(), 1):
        texto_organizado_das_fontes += f"# Fonte de pesquisa [{ordem_fonte}]:\n===\n"
        texto_organizado_das_fontes += f"## Título da Fonte: {fonte['titulo']}\n===\n"
        texto_organizado_das_fontes += f"## Site: {fonte['url']}\n===\n"
        texto_organizado_das_fontes += f"## Sumário da fonte pesquisada: {fonte['conteudo_resumido']}\n===\n"

        conteudo_completo = fonte.get('conteudo_completo', '')
        texto_organizado_das_fontes += f"## Conteúdo completo da página web:\n{conteudo_completo}\n\n"

    return texto_organizado_das_fontes.strip()


def buscar_conteudo_completo_site(url: str):
    """
    Busca o conteúdo HTML de uma URL e o converte para o formato markdown.

    Utiliza um tempo limite de 10 segundos para evitar travamentos em sites lentos ou páginas muito grandes.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return markdownify(response.text)
    except Exception as e:
        print(f"Aviso: Falha ao buscar o conteúdo completo da página para {url}: {str(e)}")
        return None


def duckduckgo_pesquisa(consulta: str, max_resultados: int = 3):
    """Realiza uma busca na web usando o DuckDuckGo e retorna os resultados formatados.

    :argument:
        consulta (str): A consulta de busca a ser executada
        max_resultados (int, opcional): Número máximo de resultados a serem retornados. Padrão é 3.

    :return: Dicionário com a resposta da busca contendo.
    """
    try:
        with DDGS() as ddgs:
            resultados = []
            resultados_pesquisa = list(ddgs.text(consulta, max_results=max_resultados))

            for r in resultados_pesquisa:
                url = r.get('href')
                titulo = r.get('title')
                conteudo_resumido = r.get('body')

                if not all([url, titulo, conteudo_resumido]):
                    print(f"Aviso: Resultado incompleto do DuckDuckGo. Ignorar: {r}")
                    continue

                conteudo_completo = buscar_conteudo_completo_site(url)

                # Adiciona os resultados na lista de sites pesquisados
                dicionario_resultados = {
                    "titulo": titulo,
                    "url": url,
                    "conteudo_resumido": conteudo_resumido,
                    "conteudo_completo": conteudo_completo
                }
                resultados.append(dicionario_resultados)

            return {"resultados": resultados}
    except Exception as e:
        print(f"Erro em DuckDuckGo: {str(e)}")
        return {"resultados": []}

