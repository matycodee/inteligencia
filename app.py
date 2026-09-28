<<<<<<< HEAD
﻿import os
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
=======
import os
import warnings
warnings.filterwarnings("ignore")

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
>>>>>>> 4f97ee0b206760aef49f5ff971b871e9bc446b1e
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
<<<<<<< HEAD

def iniciar_agente():
    print("Cargando la base de conocimientos local de NutriFit...")
    
    documentos = []
    with open('./data/inventario.txt', 'r', encoding='utf-8') as f:
        for linea in f:
            if linea.strip():
                documentos.append(Document(page_content=linea.strip()))
                
    loader_politicas = TextLoader(file_path='./data/politicas.txt', encoding='utf-8')
    documentos.extend(loader_politicas.load())
    
    print("Vectorizando datos localmente con HuggingFace...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents=documentos, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
    
=======

# Configuración de API Key de OpenAI desde variable de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def iniciar_agente():
    print("Cargando la base de conocimientos de NutriFit...")
    
    # 1. Cargamos el inventario en texto plano estructurado
    loader_txt = TextLoader(file_path="./data/inventario.txt", encoding="utf-8")
    docs_txt = loader_txt.load()
    
    # 2. Cargamos las políticas corporativas en PDF
    loader_pdf = PyPDFLoader(file_path="./data/politicas.pdf")
    docs_pdf = loader_pdf.load_and_split()
    
    # Unificamos las fuentes de datos
    documentos = docs_txt + docs_pdf
    
    print("Vectorizando datos con OpenAI Embeddings...")
    vectorstore = Chroma.from_documents(documents=documentos, embedding=OpenAIEmbeddings())
    
    # k en 1 para que devuelva exactamente el fragmento correspondiente sin mezclar información
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
    
    # Directrices estrictas del sistema para el asistente NutriBot
>>>>>>> 4f97ee0b206760aef49f5ff971b871e9bc446b1e
    system_prompt = (
        "Eres 'NutriBot', un asistente técnico exclusivo para los ejecutivos de soporte de NutriFit Chile. "
        "Tu objetivo es responder consultas basándote ÚNICAMENTE en el siguiente contexto recuperado. "
        "Si la respuesta no se encuentra en el contexto, debes responder textualmente: "
        "'No poseo esa información en mis registros actuales'. "
        "Bajo ninguna circunstancia inventes precios, ni políticas, ni stock.\n\n"
        "Contexto recuperado:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
<<<<<<< HEAD
    # Apuntamos la base de Ollama a la ruta local exacta de Windows
    ollama_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    llm = ChatOllama(model="llama3", temperature=0, base_url="http://localhost:11434")
=======
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
>>>>>>> 4f97ee0b206760aef49f5ff971b871e9bc446b1e
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

<<<<<<< HEAD
=======
    # Cadena RAG con LCEL (LangChain Expression Language)
>>>>>>> 4f97ee0b206760aef49f5ff971b871e9bc446b1e
    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain

if __name__ == "__main__":
<<<<<<< HEAD
    agente = iniciar_agente()
    print("\n--- NutriBot (Modo Local Gratuito) Iniciado. Escribe 'salir' para terminar ---")
    while True:
        pregunta = input("\nEjecutivo NutriFit: ")
        if pregunta.lower() == 'salir':
            break
        respuesta = agente.invoke(pregunta)
        print(f"\nNutriBot: {respuesta}")
=======
    try:
        agente = iniciar_agente()
        print("\n--- NutriBot Iniciado. Escribe 'salir' para terminar ---")
        while True:
            pregunta = input("\nEjecutivo NutriFit: ")
            if pregunta.lower() == "salir":
                break
            try:
                respuesta = agente.invoke(pregunta)
                print(f"\nNutriBot: {respuesta}")
            except Exception as e:
                print(f"\n[Error al procesar consulta]: {e}")
    except Exception as e:
        print(f"\n[Error al inicializar agente]: {e}")
>>>>>>> 4f97ee0b206760aef49f5ff971b871e9bc446b1e
