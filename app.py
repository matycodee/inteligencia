import os
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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
    
    # Apuntamos la base de Ollama a la ruta local exacta de Windows
    ollama_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    llm = ChatOllama(model="llama3", temperature=0, base_url="http://localhost:11434")
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain

if __name__ == "__main__":
    agente = iniciar_agente()
    print("\n--- NutriBot (Modo Local Gratuito) Iniciado. Escribe 'salir' para terminar ---")
    while True:
        pregunta = input("\nEjecutivo NutriFit: ")
        if pregunta.lower() == 'salir':
            break
        respuesta = agente.invoke(pregunta)
        print(f"\nNutriBot: {respuesta}")
