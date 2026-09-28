import os
import warnings
warnings.filterwarnings("ignore")

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage

# NUEVO: Importaciones modernas de LangGraph que reemplazan a langchain.agents
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Configuración de API Key de OpenAI desde variable de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 1. HERRAMIENTA DE ESCRITURA (Tickets)
@tool
def registrar_ticket(problema: str) -> str:
    """Útil para escribir, registrar o guardar un ticket de soporte cuando un cliente tiene un reclamo o falta stock."""
    with open("tickets_soporte.txt", "a", encoding="utf-8") as f:
        f.write(f"TICKET DE SOPORTE: {problema}\n---\n")
    return "El ticket fue redactado y guardado exitosamente en el sistema."

def iniciar_agente():
    print("Cargando la base de conocimientos de NutriFit...")
    
    loader_txt = TextLoader(file_path="./data/inventario.txt", encoding="utf-8")
    docs_txt = loader_txt.load()
    loader_pdf = PyPDFLoader(file_path="./data/politicas.pdf")
    docs_pdf = loader_pdf.load_and_split()
    documentos = docs_txt + docs_pdf
    
    print("Vectorizando datos con OpenAI Embeddings...")
    vectorstore = Chroma.from_documents(documents=documentos, embedding=OpenAIEmbeddings())
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    
    # 2. HERRAMIENTA DE CONSULTA (RAG)
    @tool
    def consultar_base_datos(consulta: str) -> str:
        """Útil para buscar información estricta de inventario, stock, precios y políticas corporativas de NutriFit."""
        documentos_recuperados = retriever.invoke(consulta)
        return "\n\n".join(doc.page_content for doc in documentos_recuperados)

    tools = [consultar_base_datos, registrar_ticket]
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    # 3. PROMPT DEL AGENTE
    system_message = SystemMessage(
        content=(
            "Eres 'NutriBot', un agente técnico exclusivo para los ejecutivos de soporte de NutriFit Chile. "
            "REGLAS ESTRICTAS: "
            "1. Si te preguntan por productos o políticas, DEBES usar la herramienta 'consultar_base_datos'. "
            "2. Si la información no está en la base de datos, responde textualmente: 'No poseo esa información en mis registros actuales'. "
            "3. Nunca inventes precios, ni políticas, ni stock. "
            "4. Si te piden levantar, guardar o registrar un ticket, usa la herramienta 'registrar_ticket'."
        )
    )

    # 4. MEMORIA (Usando LangGraph MemorySaver)
    memory = MemorySaver()

    # 5. ORQUESTACIÓN DEL AGENTE CON LANGGRAPH (El estándar moderno)
    agent_executor = create_react_agent(
        llm, 
        tools, 
        state_modifier=system_message,
        checkpointer=memory
    )
    
    return agent_executor

if __name__ == "__main__":
    try:
        agente = iniciar_agente()
        print("\n--- NutriBot Agente Iniciado. Escribe 'salir' para terminar ---")
        
        # Configuración para mantener el hilo de la conversación (Memoria)
        config = {"configurable": {"thread_id": "sesion_1"}}
        
        while True:
            pregunta = input("\nEjecutivo NutriFit: ")
            if pregunta.lower() == "salir":
                break
            try:
                # Invocamos el agente pasándole el mensaje del usuario
                respuesta = agente.invoke(
                    {"messages": [("user", pregunta)]}, 
                    config
                )
                # LangGraph devuelve una lista de mensajes, imprimimos el último (la respuesta del bot)
                print(f"\nNutriBot: {respuesta['messages'][-1].content}")
            except Exception as e:
                print(f"\n[Error al procesar consulta]: {e}")
    except Exception as e:
        print(f"\n[Error al inicializar agente]: {e}")