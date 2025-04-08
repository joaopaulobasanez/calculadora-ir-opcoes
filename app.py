import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from io import BytesIO
import re

st.set_page_config(page_title="Calculadora IR Opções - Clear", layout="wide")
st.title("📈 Calculadora IR sobre Opções (Notas da Clear)")

def extrair_texto_pdf(arquivo):
    texto_total = ""
    with fitz.open(stream=arquivo.read(), filetype="pdf") as doc:
        for pagina in doc:
            texto_total += pagina.get_text()
    return texto_total

def parse_nota_clear(texto):
    linhas = texto.split("\n")
    operacoes = []
    data_pregao = None

    for i, linha in enumerate(linhas):
        if "Data pregão" in linha and i + 1 < len(linhas):
            try:
                data_pregao = pd.to_datetime(linhas[i + 1].strip(), dayfirst=True)
            except:
                pass

        if "B3 RV LISTADO" in linha and ("OPCAO DE" in linha or "OPÇÃO DE" in linha):
            partes = linha.split()
            try:
                tipo_op = "venda" if "V" in partes else "compra"
                ativo = partes[7] if len(partes) > 7 else "N/A"
                quantidade = int(partes[-4])
                preco = float(partes[-3].replace(",", "."))
                valor_total = float(partes[-2].replace(",", "."))
                operacoes.append({
                    "data": data_pregao,
                    "ativo": ativo,
                    "tipo": tipo_op,
                    "quantidade": quantidade,
                    "preco": preco,
                    "valor_total": valor_total
                })
            except:
                continue
    return pd.DataFrame(operacoes)

# App principal
uploaded_files = st.file_uploader("📎 Envie suas notas da Clear (PDF)", type=["pdf"], accept_multiple_files=True)
if uploaded_files:
    todas_ops = pd.DataFrame()
    for arq in uploaded_files:
        texto = extrair_texto_pdf(arq)
        df = parse_nota_clear(texto)
        todas_ops = pd.concat([todas_ops, df], ignore_index=True)

    if not todas_ops.empty:
        st.success("✅ Operações detectadas:")
        st.dataframe(todas_ops)
    else:
        st.warning("⚠️ Nenhuma operação foi detectada.")
else:
    st.info("Envie ao menos um PDF para começar.")
