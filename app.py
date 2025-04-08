
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import base64
from io import BytesIO
import tempfile
import os

st.set_page_config(page_title="Calculadora de IR para Opções", layout="wide")

st.title("📈 Calculadora de IR para Opções (Notas Sinacor)")
st.write("Faça upload de arquivos PDF com notas de corretagem no formato Sinacor para calcular lucro/prejuízo mensal e o imposto devido.")

def extrair_texto_pdf(arquivo):
    texto_total = ""
    with fitz.open(stream=arquivo.read(), filetype="pdf") as doc:
        for pagina in doc:
            texto_total += pagina.get_text()
    return texto_total

def parse_nota_sinacor(texto):
    linhas = texto.split("\n")
    operacoes = []
    data_nota = None
    for i, linha in enumerate(linhas):
        if "Data pregão" in linha:
            try:
                data_nota = pd.to_datetime(linha.split()[-1], dayfirst=True)
            except:
                data_nota = None
        if "OPÇÕES DE COMPRA" in linha or "OPÇÕES DE VENDA" in linha:
            j = i + 2
            while j < len(linhas) and linhas[j].strip():
                partes = linhas[j].split()
                if len(partes) >= 6:
                    ativo = partes[0]
                    tipo = "C" if "C" in partes else "V"
                    quantidade = int(partes[1])
                    preco = float(partes[-2].replace(",", "."))
                    valor = float(partes[-1].replace(",", "."))
                    operacoes.append({
                        "data": data_nota,
                        "ativo": ativo,
                        "tipo": tipo,
                        "quantidade": quantidade,
                        "preco": preco,
                        "valor": valor
                    })
                j += 1
    return pd.DataFrame(operacoes)

def classificar_tipo_operacao(df):
    if 'data' not in df.columns:
        st.error("Erro: a coluna 'data' não foi encontrada nos dados extraídos.")
        st.stop()
    df['data_str'] = df['data'].dt.strftime('%Y-%m-%d')
    df['tipo_operacao'] = "Swing Trade"
    for ativo in df['ativo'].unique():
        datas = df[df['ativo'] == ativo]['data'].sort_values().values
        if len(datas) > 1 and (datas[-1] == datas[-2]):
            df.loc[df['ativo'] == ativo, 'tipo_operacao'] = "Day Trade"
    return df

def calcular_lucros(df):
    df = classificar_tipo_operacao(df)
    df['ano_mes'] = df['data'].dt.to_period('M')
    resultado = df.groupby(['ano_mes', 'tipo_operacao']).agg({'valor': 'sum'}).reset_index()
    resultado['lucro'] = resultado['valor']
    resultado.drop(columns='valor', inplace=True)
    return resultado

def gerar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="IR Resultado")
    return output.getvalue()

arquivos = st.file_uploader("📎 Envie suas notas de corretagem (PDF)", type=["pdf"], accept_multiple_files=True)

if arquivos:
    todas_operacoes = pd.DataFrame()
    for arquivo in arquivos:
        texto = extrair_texto_pdf(arquivo)
        df = parse_nota_sinacor(texto)
        todas_operacoes = pd.concat([todas_operacoes, df], ignore_index=True)

    if not todas_operacoes.empty:
        st.write("📊 Pré-visualização das operações extraídas:")
        st.dataframe(todas_operacoes)

        df_resultado = calcular_lucros(todas_operacoes)

        st.subheader("📅 Resultado mensal com IR:")
        st.dataframe(df_resultado)

        excel_bytes = gerar_excel(df_resultado)

        st.download_button(
            label="📥 Baixar Relatório Excel",
            data=excel_bytes,
            file_name="relatorio_ir_opcoes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Nenhuma operação foi detectada nos PDFs enviados.")
