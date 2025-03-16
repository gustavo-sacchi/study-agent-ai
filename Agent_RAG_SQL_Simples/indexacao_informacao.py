import os

from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore


from dotenv import load_dotenv
load_dotenv()


class CarregadorDocumento:
    def __init__(self, caminho_documento):
        self.caminho_documento = caminho_documento
        self.text_splitter = RecursiveCharacterTextSplitter(separators=["\n\n"],chunk_size=1000, chunk_overlap=200)
        self.embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

    def carregar_texto(self):
        """Lê e carrega o PDF criando os Documents apenas do texto."""
        loader = TextLoader(self.caminho_documento, encoding="utf-8")  # mudar aqui para o caminho do seu computador
        pages_sinc = loader.load()
        return pages_sinc

    def cria_chunks(self, documentos):
        """Função que cria os chunks"""
        chunks = self.text_splitter.split_documents(documentos)
        return chunks


    def indexar_informacao(self):
        """Função cria os embeddings e armazena no banco cloud Qdrant"""

        # carrega texto:
        documento_lido = self.carregar_texto()
        chunk_documento_lido = self.cria_chunks(documento_lido)

        # Indexar no banco vetorial
        QdrantVectorStore.from_documents(
            documents=chunk_documento_lido,
            embedding=self.embedding_model,
            api_key=os.environ.get("QDRANT_API_KEY"),
            url=os.environ.get("QDRANT_URL"),
            prefer_grpc=True,
            collection_name="criticas_filme"
        )
        print(">> Indexação realizada")


if __name__=="__main__":
    i = CarregadorDocumento(r".\Criticas_Filme_Um_Sonho_de_Liberdade.txt")
    i.indexar_informacao()
