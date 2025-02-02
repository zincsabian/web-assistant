import streamlit as st
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains import RetrievalQA

import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Streamlit UI
st.title("📄 RAG System with DeepSeek R1 & Ollama")

uploaded_file = st.file_uploader("Upload your PDF file here", type="pdf")

if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getvalue())

    loader = PDFPlumberLoader("temp.pdf")
    docs = loader.load()

    text_splitter = SemanticChunker(HuggingFaceEmbeddings())
    documents = text_splitter.split_documents(docs)

    st.write("### Semantic Chunks:")
    for i, doc in enumerate(documents):
        st.write(f"**Chunk {i+1}:**")
        st.write(doc.page_content)
        st.write("")

    embedder = HuggingFaceEmbeddings()
    vector = FAISS.from_documents(documents, embedder)
    retriever = vector.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    llm = Ollama(model="deepseek-r1:7b")

    prompt = """
    Use the following context to answer the question.
    Context: {context}
    Question: {question}
    Answer:"""

    QA_PROMPT = PromptTemplate.from_template(prompt)

    llm_chain = LLMChain(llm=llm, prompt=QA_PROMPT)
    combine_documents_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="context")

    qa = RetrievalQA(combine_documents_chain=combine_documents_chain, retriever=retriever)

    user_input = st.text_input("Ask a question about your document:")

    if user_input:
        response = qa(user_input)["result"]
        # 打印检索到的文档（可以按需要打印文档的部分或详细信息）
        matches = retriever.get_relevant_documents(user_input)  # 假设这个方法返回相关文档的列表

# 打印匹配的文档和相关性分数
        for i, match in enumerate(matches):
             print(i, match)
	#    logging.info(f"Match {i+1}: Score: {match['score']}, Document Excerpt: {match['text'][:200]}...")

        st.write("**Response:**")
        st.write(response)
