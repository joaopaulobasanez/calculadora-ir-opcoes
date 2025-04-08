# Requisitos: streamlit, PyPDF2, pandas, openpyxl, fpdf
# Instale com: pip install streamlit PyPDF2 pandas openpyxl fpdf

import streamlit as st
import pandas as pd
import re
from PyPDF2 import PdfReader
from io import BytesIO
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Calculadora IR Opções", layout="wide")
st.title("📈 Calculadora de Imposto de Renda - Opções com Notas Sinacor")

uploaded_files = st.file_uploader("Envie suas notas de corretagem (PDF, formato Sinacor)", accept_multiple_files=True, type="pdf")

@st.cache_data
def extrair_operacoes(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    texto = ''
    for page in reader.pages:
        texto += page.extract_text()

    operacoes = []
    linhas = texto.split('\n')
    data_nota = ""

    for linha in linhas:
        if re.search(r'\d{2}/\d{2}/\d{4}', linha):
            data_match = re.search(r'\d{2}/\d{2}/\d{4}', linha)
            if data_match:
                data_nota = datetime.strptime(data_match.group(), "%d/%m/%Y")

        dados = re.findall(r'([A-Z]{4}\d+[A-Z]\d+)\s+(\d+)\s+([\d,.]+)\s+([CV])', linha)
        for ativo, qtd, preco, tipo in dados:
            preco = float(preco.replace('.', '').replace(',', '.'))
            qtd = int(qtd)
            operacoes.append({
                'data': data_nota,
                'ativo': ativo,
                'quantidade': qtd,
                'preco': preco,
                'tipo': 'compra' if tipo == 'C' else 'venda'
            })
    return operacoes

def classificar_tipo_operacao(df):
    df['data_str'] = df['data'].dt.strftime('%Y-%m-%d')
    df['tipo_operacao'] = 'swing_trade'

    agrupado = df.groupby(['data_str', 'ativo'])
    for (data_str, ativo), grupo in agrupado:
        tipos = grupo['tipo'].unique()
        if 'compra' in tipos and 'venda' in tipos:
            df.loc[(df['data_str'] == data_str) & (df['ativo'] == ativo), 'tipo_operacao'] = 'day_trade'

    df.drop(columns=['data_str'], inplace=True)
    return df

def calcular_lucros(operacoes):
    df = pd.DataFrame(operacoes)
    df = classificar_tipo_operacao(df)
    df['mes'] = df['data'].dt.to_period('M')

    resultado = []
    prejuizo_swing = 0
    prejuizo_day = 0

    for mes, grupo in df.groupby('mes'):
        lucro_swing = 0
        lucro_day = 0

        for tipo_op in ['swing_trade', 'day_trade']:
            grupo_tipo = grupo[grupo['tipo_operacao'] == tipo_op]
            for ativo in grupo_tipo['ativo'].unique():
                op_ativo = grupo_tipo[grupo_tipo['ativo'] == ativo]
                compras = op_ativo[op_ativo['tipo'] == 'compra']
                vendas = op_ativo[op_ativo['tipo'] == 'venda']
                if not compras.empty and not vendas.empty:
                    total_compra = compras['quantidade'].sum() * compras['preco'].mean()
                    total_venda = vendas['quantidade'].sum() * vendas['preco'].mean()
                    lucro = total_venda - total_compra
                    if tipo_op == 'swing_trade':
                        lucro_swing += lucro
                    else:
                        lucro_day += lucro

        lucro_swing_liq = lucro_swing + prejuizo_swing
        lucro_day_liq = lucro_day + prejuizo_day

        ir_swing = 0.15 * lucro_swing_liq if lucro_swing_liq > 0 else 0
        ir_day = 0.20 * lucro_day_liq if lucro_day_liq > 0 else 0

        if lucro_swing_liq < 0:
            prejuizo_swing = lucro_swing_liq
        else:
            prejuizo_swing = 0

        if lucro_day_liq < 0:
            prejuizo_day = lucro_day_liq
        else:
            prejuizo_day = 0

        resultado.append({
            'mês': str(mes),
            'lucro_swing_trade': round(lucro_swing_liq, 2),
            'IR_swing_trade': round(ir_swing, 2),
            'lucro_day_trade': round(lucro_day_liq, 2),
            'IR_day_trade': round(ir_day, 2),
            'IR_total': round(ir_swing + ir_day, 2)
        })

    return pd.DataFrame(resultado)

def gerar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='IR_Resumo')
    output.seek(0)
    return output

def gerar_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Resumo de IR sobre Opções", ln=True, align='C')
    pdf.ln(10)
    for index, row in df.iterrows():
        linha = (
            f"Mês: {row['mês']} | Lucro Swing: R${row['lucro_swing_trade']:.2f} | IR 15%: R${row['IR_swing_trade']:.2f} | "
            f"Lucro Day: R${row['lucro_day_trade']:.2f} | IR 20%: R${row['IR_day_trade']:.2f} | Total IR: R${row['IR_total']:.2f}"
        )
        pdf.cell(200, 10, txt=linha, ln=True)
    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

if uploaded_files:
    todas_operacoes = []
    for file in uploaded_files:
        operacoes = extrair_operacoes(file.read())
        todas_operacoes.extend(operacoes)

    df_resultado = calcular_lucros(todas_operacoes)
    st.subheader("📊 Resultado Consolidado")
    st.dataframe(df_resultado)

    excel = gerar_excel(df_resultado)
    st.download_button("📥 Baixar Excel", data=excel, file_name="resumo_ir_opcoes.xlsx")

    pdf = gerar_pdf(df_resultado)
    st.download_button("📄 Baixar PDF", data=pdf, file_name="resumo_ir_opcoes.pdf")
else:
    st.info("Envie ao menos um arquivo PDF para continuar.")
