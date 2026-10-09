import streamlit as st
import math
from decimal import Decimal, getcontext

# Configuração da página para ocupar mais espaço na tela
st.set_page_config(page_title="Simulador de Erros Numéricos", layout="wide")

# ==========================================
# MOTOR MATEMÁTICO (CORE LOGIC)
# ==========================================

def ajustar_precisao(valor, n, metodo):
    """
    Simula o armazenamento na máquina normalizando o número para notação
    científica (0.d1d2...dn x 10^e) e aplicando truncamento ou arredondamento.
    """
    if valor == 0:
        return 0.0
    
    valor_float = float(valor)
    
    # Normalização: transforma o valor para a forma mantissa * 10^exp
    # onde 0.1 <= |mantissa| < 1.0
    exp = math.floor(math.log10(abs(valor_float))) + 1
    mantissa = valor_float / (10**exp)
    
    fator = 10**n
    
    if metodo == "truncamento":
        # Corta os dígitos sobressalentes
        mantissa_ajustada = math.trunc(mantissa * fator) / fator
    elif metodo == "arredondamento":
        # Arredondamento clássico (round half up) para evitar o "banker's rounding" padrão do Python
        shift = mantissa * fator
        if shift >= 0:
            mantissa_ajustada = math.floor(shift + 0.5) / fator
        else:
            mantissa_ajustada = math.ceil(shift - 0.5) / fator
            
    # Retorna o valor ajustado retirando-o da notação científica simulada
    return mantissa_ajustada * (10**exp)

def calcular_erros(exato, aproximado):
    """Calcula o Erro Absoluto e o Erro Relativo."""
    exato_float = float(exato)
    erro_absoluto = abs(exato_float - aproximado)
    
    if aproximado != 0:
        erro_relativo = erro_absoluto / abs(aproximado)
    else:
        erro_relativo = float('inf') # Evita divisão por zero caso o valor aprox seja anulado
        
    return erro_absoluto, erro_relativo

# Aumentamos a precisão do Decimal do Python para simular a "precisão máxima"
getcontext().prec = 50 

# ==========================================
# INTERFACE WEB (FRONTEND)
# ==========================================

st.title("Simulador de Propagação de Erros Numéricos")
st.write("Desenvolvido para a disciplina de Cálculo Numérico. Simula como erros de truncamento e arredondamento afetam os cálculos.")

# Criando abas para separar a calculadora livre das demonstrações
aba_calculadora, aba_exemplos = st.tabs(["Calculadora Livre", "Casos de Demonstração (PDF)"])

# ------------------------------------------
# ABA 1: CALCULADORA LIVRE
# ------------------------------------------
with aba_calculadora:
    st.header("Simulador de Operações")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        x_input = st.text_input("Valor de X (ex: 0.76545)", value="1.23456")
    with col2:
        operacao = st.selectbox("Operação", ["+", "-", "*", "/"])
    with col3:
        y_input = st.text_input("Valor de Y (ex: 0.76541)", value="0.12345")
        
    col4, col5 = st.columns(2)
    with col4:
        n_digitos = st.slider("Número de Dígitos Significativos (t)", min_value=1, max_value=15, value=4)
    with col5:
        metodo = st.radio("Método de Ajuste", ["truncamento", "arredondamento"])

    if st.button("Calcular Resultado"):
        try:
            # Usando Decimal para calcular o valor real sem perdas do float do Python
            x_dec = Decimal(x_input)
            y_dec = Decimal(y_input)
            
            if operacao == "+":
                exato = x_dec + y_dec
            elif operacao == "-":
                exato = x_dec - y_dec
            elif operacao == "*":
                exato = x_dec * y_dec
            elif operacao == "/":
                exato = x_dec / y_dec

            # Aplica a precisão simulada na máquina sobre os operandos (se desejar simular a entrada)
            # O PDF pede para realizar a operação exata e DEPOIS aplicar o ajuste (no Ex 1)
            # ou armazenar com k dígitos e realizar (no Ex 2). Vamos fazer a regra geral da operação:
            resultado_aproximado = ajustar_precisao(float(exato), n_digitos, metodo)
            
            e_abs, e_rel = calcular_erros(exato, resultado_aproximado)
            
            st.success("Cálculo realizado com sucesso!")
            st.markdown(f"**Valor Exato:** `{exato}`")
            st.markdown(f"**Valor Aproximado:** `{resultado_aproximado}`")
            st.markdown(f"**Erro Absoluto (Ea):** `{e_abs}`")
            st.markdown(f"**Erro Relativo (Er):** `{e_rel}` ({e_rel * 100:.2f}%)")
            
        except Exception as e:
            st.error(f"Erro na entrada de dados. Verifique os números. Detalhes: {e}")

# ------------------------------------------
# ABA 2: CASOS DE DEMONSTRAÇÃO (APRESENTAÇÃO)
# ------------------------------------------
with aba_exemplos:
    st.header("Exemplos Exigidos no Projeto")
    
    # Exemplo 1
    with st.expander("Exemplo 1: Operação Simples (Soma)"):
        st.write("Somar dois números com 5 casas decimais com t=4.")
        ex1_x, ex1_y = Decimal("0.12345"), Decimal("0.54321")
        ex1_exato = ex1_x + ex1_y
        
        ex1_trunc = ajustar_precisao(ex1_exato, 4, "truncamento")
        ex1_arred = ajustar_precisao(ex1_exato, 4, "arredondamento")
        
        ea_t, er_t = calcular_erros(ex1_exato, ex1_trunc)
        ea_a, er_a = calcular_erros(ex1_exato, ex1_arred)
        
        st.write(f"**Operação:** {ex1_x} + {ex1_y}")
        st.write(f"**Valor Exato:** {ex1_exato}")
        
        col_t, col_a = st.columns(2)
        col_t.metric("Resultado (Truncamento)", ex1_trunc)
        col_t.write(f"**Ea:** {ea_t} | **Er:** {er_t:.4%}")
        
        col_a.metric("Resultado (Arredondamento)", ex1_arred)
        col_a.write(f"**Ea:** {ea_a} | **Er:** {er_a:.4%}")

    # Exemplo 2
    with st.expander("Exemplo 2: Cancelamento Subtrativo"):
        st.write("Calcular X - Y, onde X = 0.76545 e Y = 0.76541, armazenando na máquina com t=4 (arredondamento) antes da subtração.")
        x_ex2 = Decimal("0.76545")
        y_ex2 = Decimal("0.76541")
        exato_ex2 = x_ex2 - y_ex2
        
        # Representação na máquina (arredondamento de X e Y)
        x_aprox = ajustar_precisao(x_ex2, 4, "arredondamento")
        y_aprox = ajustar_precisao(y_ex2, 4, "arredondamento")
        
        resultado_aprox_ex2 = x_aprox - y_aprox
        ea_ex2, er_ex2 = calcular_erros(exato_ex2, resultado_aprox_ex2)
        
        st.write(f"**Valor Exato:** {exato_ex2} (ou {float(exato_ex2):.1e})")
        st.write(f"**Armazenamento na máquina:** X ≈ {x_aprox}, Y ≈ {y_aprox}")
        st.write(f"**Resultado Aproximado na máquina:** {resultado_aprox_ex2:.4f}")
        st.write(f"**Erro Absoluto (Ea):** {ea_ex2}")
        st.write(f"**Erro Relativo (Er):** {er_ex2} (ou {er_ex2 * 100}%) -> Perda total de significado!")

    # Exemplo 3
    with st.expander("Exemplo 3: Propagação de Erro em Somas Sequenciais"):
        st.write("Somar 0.56786 dez vezes, usando t=4 com truncamento em cada passo.")
        
        parcela = Decimal("0.56786")
        exato_ex3 = parcela * 10
        
        st.write(f"**Valor Exato (10 * {parcela}):** {exato_ex3}")
        
        soma_aprox = 0.0
        # Simula a adição passo a passo na máquina
        for i in range(1, 11):
            soma_exata_passo = soma_aprox + float(parcela)
            soma_aprox = ajustar_precisao(soma_exata_passo, 4, "truncamento")
            st.text(f"Passo {i}: Soma exata do passo = {soma_exata_passo:.5f} -> Após truncar: {soma_aprox}")
            
        ea_ex3, er_ex3 = calcular_erros(exato_ex3, soma_aprox)
        st.markdown(f"**Resultado Final Aproximado:** {soma_aprox}")
        st.markdown(f"**Erro Absoluto Final:** {ea_ex3}")
        st.markdown(f"**Erro Relativo Final:** {er_ex3:.4%}")