
import fitz  # PyMuPDF
import pandas as pd

def extrair_texto_pdf(caminho_pdf):
    texto_total = ""
    with fitz.open(caminho_pdf) as doc:
        for pagina in doc:
            texto_total += pagina.get_text()
    return texto_total

def parser_personalizado(texto):
    linhas = texto.split("\n")
    operacoes = []
    data_pregao = None

    for i, linha in enumerate(linhas):
        if "Data pregão" in linha and i + 1 < len(linhas):
            try:
                data_pregao = pd.to_datetime(linhas[i + 1].strip(), dayfirst=True)
            except:
                data_pregao = None

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
            except Exception as e:
                print(f"Erro ao processar linha: {linha}")
                print(e)
                continue
    return pd.DataFrame(operacoes)

if __name__ == "__main__":
    caminho = input("Digite o caminho completo do arquivo PDF: ").strip()
    texto = extrair_texto_pdf(caminho)
    df = parser_personalizado(texto)
    print("\n📋 Operações encontradas:")
    print(df if not df.empty else "Nenhuma operação detectada.")
