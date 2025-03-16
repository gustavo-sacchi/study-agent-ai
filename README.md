# Estudo sobre Agente de IA usando LangGraph
Repositório para estudo de Agentes de AI e para compartilhamento dos arquivos apresentados nos tutoriais do youtube.

# Diretórios:
- AgentReAct - Implementação da estrutura da um agente ReAct usando LangGraph
- Agent_RAG_SQL_Simples - Implementação da estrutura da um agente ReAct usando 3 ferramentas para interagir com banco vetorial (via RAG) e banco estruturado SQLite.

# Descrição:
- O que são **Agentes de IA** e por que são tão importantes.  
- Um tutorial prático de **implementação do agente usando LangGraph**, incluindo código em Python e integração de ferramenta API climática Openweathermap.
- Dicas para construir uma abordagem ReAct sólida, lidar com o custo computacional, otimizar prompts e evitar alucinações.  

# Tutorial no Youtube:
- Domine Agentes de IA ReAct: Transforme Seus Projetos em Máquinas Autônomas - https://youtu.be/Liv3t45GESc
- Agentes de IA com Banco Vetorial e SQL no LangGraph: Arquitetura React Passo a Passo em Python - https://youtu.be/q00IDGB0P9c


### Instalação

1. Clone o repositório:

   ```
   git clone https://github.com/gustavo-sacchi/study-agent-ai.git
   ```

2. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```
**Atenção**: Se por acaso o comando de instalação das dependências acima não funciuonar, tente executar a instalação via terminal pip:

``` 
pip install langchain-openai langchain langchain-core langchain-community langchain-experimental python-dotenv langgraph
```
    

3. Configure as variáveis de ambiente:

   - Renomeie o arquivo `.env.example` para `.env` e atualize as variáveis com seus valores. Exemplo:

   ```
   mv .env.example .env
   ```

5) Crie o ambiente virtual: 

    ```
    python -m venv venv
    ```

6) Execute os exemplos de código via interface ou via terminal, conforme sua preferência.

