
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from io import BytesIO
import re

st.set_page_config(page_title="Calculadora de IR - Opções", layout="wide")
st.title("📈 Calculadora de IR para Opções - Notas Clear (Sinacor)")

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
        if "Data pregão" in linha:
            match = re.search(r"(\d{2}/\d{2}/\d{4})", linha)
            if match:
                data_pregao = pd.to_datetime(match.group(1), dayfirst=True)

        if "B3 RV LISTADO" in linha and ("OPCAO DE" in linha or "OPÇÃO DE" in linha):
            partes = linha.split()
            try:
                tipo_op = "venda" if partes[3] == "V" else "compra"
                especificacao = partes[7]
                quantidade = int(partes[-4])
                preco = float(partes[-3].replace(",", "."))
                valor_total = float(partes[-2].replace(",", "."))
                operacoes.append({
                    "data": data_pregao,
                    "ativo": especificacao,
                    "tipo": tipo_op,
                    "quantidade": quantidade,
                    "preco": preco,
                    "valor": valor_total
                })
            except:
                continue
    return pd.DataFrame(operacoes)

def classificar_tipo_operacao(df):
    if 'data' not in df.columns:
        st.error("Erro: coluna 'data' ausente.")
        st.stop()
    df['data_str'] = df['data'].dt.strftime('%Y-%m-%d')
    df['tipo_operacao'] = 'Swing Trade'
    grupo = df.groupby(['data_str', 'ativo'])
    for (data_str, ativo), sub in grupo:
        if 'compra' in sub['tipo'].values and 'venda' in sub['tipo'].values:
            df.loc[(df['data_str'] == data_str) & (df['ativo'] == ativo), 'tipo_operacao'] = 'Day Trade'
    df.drop(columns=['data_str'], inplace=True)
    return df

def calcular_lucros(df):
    df = classificar_tipo_operacao(df)
    df['mes'] = df['data'].dt.to_period('M')
    resultados = []

    prejuizo_swing = 0
    prejuizo_day = 0

    for mes, grupo in df.groupby('mes'):
        lucro_swing = 0
        lucro_day = 0

        for tipo_op in ['Swing Trade', 'Day Trade']:
            grupo_op = grupo[grupo['tipo_operacao'] == tipo_op]
            for ativo in grupo_op['ativo'].unique():
                atv = grupo_op[grupo_op['ativo'] == ativo]
                c = atv[atv['tipo'] == 'compra']
                v = atv[atv['tipo'] == 'venda']
                if not c.empty and not v.empty:
                    total_c = c['quantidade'].sum() * c['preco'].mean()
                    total_v = v['quantidade'].sum() * v['preco'].mean()
                    lucro = total_v - total_c
                    if tipo_op == 'Swing Trade':
                        lucro_swing += lucro
                    else:
                        lucro_day += lucro

        liq_swing = lucro_swing + prejuizo_swing
        liq_day = lucro_day + prejuizo_day

        ir_swing = 0.15 * liq_swing if liq_swing > 0 else 0
        ir_day = 0.20 * liq_day if liq_day > 0 else 0

        prejuizo_swing = liq_swing if liq_swing < 0 else 0
        prejuizo_day = liq_day if liq_day < 0 else 0

        resultados.append({
            'mês': str(mes),
            'lucro_swing': round(liq_swing, 2),
            'IR_swing (15%)': round(ir_swing, 2),
            'lucro_day': round(liq_day, 2),
            'IR_day (20%)': round(ir_day, 2),
            'IR_total': round(ir_swing + ir_day, 2)
        })

    return pd.DataFrame(resultados)

def gerar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="IR_Resumo")
    output.seek(0)
    return output.read()

# Interface
arquivos = st.file_uploader("📎 Envie suas notas de corretagem da Clear (.PDF)", type=["pdf"], accept_multiple_files=True)

if arquivos:
    todas_ops = pd.DataFrame()
    for arq in arquivos:
        texto = extrair_texto_pdf(arq)
        df = parse_nota_clear(texto)
        todas_ops = pd.concat([todas_ops, df], ignore_index=True)

    if not todas_ops.empty:
        st.subheader("🧾 Operações detectadas:")
        st.dataframe(todas_ops)

        resultado = calcular_lucros(todas_ops)

        st.subheader("📅 Resultado mensal com IR:")
        st.dataframe(resultado)

        excel = gerar_excel(resultado)

        st.download_button("📥 Baixar Excel", data=excel, file_name="resultado_ir_opcoes.xlsx")
    else:
        st.warning("Nenhuma operação encontrada nos PDFs enviados.")
else:
    st.info("Envie ao menos um PDF para começar.")
