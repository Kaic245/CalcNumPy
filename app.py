# -*- coding: utf-8 -*-
"""
=====================================================================
SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS — INTERFACE (Streamlit)
Disciplina de Cálculo Numérico - Univasf - Projeto Unidade 1 (Erros)
=====================================================================

ESTE ARQUIVO É SÓ A INTERFACE (telas, botões, tabelas). Nenhuma conta do
simulador é feita aqui:

    motor_calculo.py   -> a matemática (normalização, truncamento,
                          arredondamento, erros, sequências)   <- apresentação
    entrada_saida.py   -> ler o que o usuário digita e formatar os números
    app.py             -> (este arquivo) desenha a página com o Streamlit
    testes_motor.py    -> testes automáticos do motor

Como executar
-------------
    pip install streamlit          (o pandas já vem junto com o Streamlit)
    streamlit run app.py

IMPORTANTE: os quatro arquivos .py devem ficar na MESMA pasta (a raiz do
repositório). O Streamlit Cloud continua usando `app.py` como arquivo principal.

Mapa deste arquivo
------------------
    1. Configuração da página e rótulos da interface
    2. Estado da sessão e callbacks (novo cálculo, sair, histórico...)
    3. Componentes de interface (tabelas, resultado, alertas)
    4. Casos de demonstração (Exemplos 1, 2 e 3 do PDF)
    5. Página principal (abas)
"""

from decimal import getcontext

import pandas as pd
import streamlit as st

from entrada_saida import (formatar, formatar_aprox, formatar_percentual,
                           interpretar_numero, notacao_normalizada, sobrescrito)
from motor_calculo import (CTX_EXATO, LIMITE_EXP_CONTEXTO, MAX_DIGITOS_ENTRADA,
                           MAX_EXPOENTE_ENTRADA, N_MAX, N_MIN, PRECISAO_EXATA,
                           TIPO_CURTO, ErroSimulador,
                           digitos_perdidos_por_cancelamento, simular_operacao,
                           simular_operacao_sequencial)

# O set_page_config precisa ser o PRIMEIRO comando do Streamlit no script.
st.set_page_config(page_title="Simulador de Erros Numéricos", page_icon="🧮", layout="wide")

# O contexto Decimal é "por thread" e o Streamlit roda cada sessão em uma thread
# própria. O motor já usa contextos explícitos em todas as contas; estas linhas
# são só uma rede de segurança para qualquer operação Decimal "solta".
getcontext().prec = PRECISAO_EXATA
getcontext().Emax = LIMITE_EXP_CONTEXTO
getcontext().Emin = -LIMITE_EXP_CONTEXTO


# =====================================================================
# 1. RÓTULOS DA INTERFACE
# =====================================================================
# (As chaves são os valores usados pelo motor; os textos são só para exibir.)

OPERACOES = {"+": "+  (soma)", "-": "-  (subtração)", "*": "*  (multiplicação)", "/": "/  (divisão)"}
SIMBOLOS = {"+": "+", "-": "−", "*": "×", "/": "÷"}   # só para exibição
METODOS = {
    "truncamento": "Truncamento (corta os dígitos extras)",
    "arredondamento": "Arredondamento (5 ou mais sobe)",
}
TIPOS_AJUSTE = {
    "significativos": "Dígitos significativos (forma 0.d₁d₂…dₙ × 10ᵉ) — item 3.2 do enunciado",
    "decimais": "Casas decimais (n dígitos depois do ponto) — como no Exemplo 3 do PDF",
}
MODOS_CALCULO = {
    "entradas": "Armazenar X e Y com n dígitos, operar e ajustar o resultado (máquina hipotética — Exemplo 2)",
    "resultado": "Operar com os valores exatos e ajustar só o resultado (item 3.2 do enunciado)",
}
ESTRUTURAS_SEQ = {
    "parcela_pura": "Repetir o mesmo termo k vezes (ex.: 0.56786 dez vezes — Exemplo 3)",
    "base_e_termo": "Partir de um valor inicial e aplicar a operação k vezes com o termo",
}
MODO_CURTO = {"entradas": "entradas + resultado", "resultado": "só o resultado"}


# =====================================================================
# 2. ESTADO DA SESSÃO E CALLBACKS
# =====================================================================
# O Streamlit reexecuta o script inteiro a cada interação. Tudo que precisa
# "sobreviver" (valores digitados, último resultado, histórico) fica em
# st.session_state. Cada visitante do site (QR code) tem a sua própria sessão.

PADROES_ESTADO = {
    # Calculadora livre — operação básica (padrão = Exemplo 2 do PDF)
    "x_txt": "0.76545", "op": "-", "y_txt": "0.76541", "n_dig": 4,
    "metodo": "arredondamento", "tipo_ajuste": "significativos", "modo_calc": "entradas",
    # Calculadora livre — operação sequencial (padrão = Exemplo 3 do PDF)
    "seq_modo_entrada": "parcela_pura",
    "seq_base_txt": "1.0", "seq_termo_txt": "0.56786", "seq_op": "+", "seq_qtd": 10,
    "seq_n_dig": 4, "seq_metodo": "truncamento", "seq_tipo_ajuste": "decimais",
    "seq_armazenar": False,
    # Resultado atual, histórico e controle de saída
    "resultado": None, "historico": [], "contador": 0, "encerrado": False,
    # Casos de demonstração (valores do PDF, mas editáveis)
    "d1_x": "0.12345", "d1_y": "0.54321", "d1_n": 4,
    "d2_x": "0.76545", "d2_y": "0.76541", "d2_n": 4,
    "d3_p": "0.56786", "d3_qtd": 10, "d3_n": 4, "d3_metodo": "truncamento",
    "d3_armazenar": False,
}
for _chave, _valor in PADROES_ESTADO.items():
    if _chave not in st.session_state:       # só define na primeira vez
        st.session_state[_chave] = _valor


def novo_calculo():
    """Callback do botão 'Novo cálculo': limpa os campos de valores e o resultado
    (mantém n, método e tipo de ajuste, que normalmente se repetem)."""
    for chave in ("x_txt", "y_txt", "seq_base_txt", "seq_termo_txt"):
        st.session_state[chave] = ""
    st.session_state["resultado"] = None


def limpar_historico():
    """Callback do botão 'Limpar histórico'."""
    st.session_state["historico"] = []


def sair():
    """Callback do botão 'Sair': mostra a tela de despedida."""
    st.session_state["encerrado"] = True


def voltar():
    """Callback do botão 'Voltar ao simulador' (na tela de despedida)."""
    st.session_state["encerrado"] = False


def enviar_para_calculadora(x_txt, op, y_txt, n, metodo, tipo, modo):
    """Callback dos botões 'Enviar para a calculadora livre' (aba de demonstração):
    copia os valores do exemplo para os campos da operação básica."""
    novos = {"x_txt": x_txt, "op": op, "y_txt": y_txt, "n_dig": int(n), "metodo": metodo,
             "tipo_ajuste": tipo, "modo_calc": modo, "resultado": None}
    for chave, valor in novos.items():
        st.session_state[chave] = valor
    st.session_state["aviso_envio"] = (
        "Valores enviados! Abra a aba **🧮 Calculadora livre** (Operação básica) e clique em **Calcular**."
    )


def registrar_historico(r):
    """Guarda o cálculo no histórico da sessão (só textos, bem leve)."""
    st.session_state["contador"] += 1
    if r.get("tipo_resultado") == "sequencial":
        if r["base_usada"] == r["termo_usado"] and r["op"] == "+":
            descricao = f"Repetir {formatar(r['termo_usado'], 15)} {r['quantidade']}× (+)"
        else:
            descricao = (f"{formatar(r['base_usada'], 12)} {SIMBOLOS[r['op']]} "
                         f"{formatar(r['termo_usado'], 12)} ({r['quantidade']}×)")
        linha = {
            "#": st.session_state["contador"], "Operação": descricao, "n": r["n"],
            "Método": r["metodo"], "Ajuste": TIPO_CURTO[r["tipo"]],
            "Modo": "sequencial (" + ("operandos na máquina" if r["armazenar"] else "só resultados") + ")",
            "Valor exato": formatar(r["exato"], 20), "Valor aproximado": formatar(r["final"], 20),
            "Ea": formatar_aprox(r["ea"], 6), "Er": formatar_percentual(r["er"]),
        }
    else:
        linha = {
            "#": st.session_state["contador"],
            "Operação": f"{formatar(r['x'], 20)} {SIMBOLOS[r['op']]} {formatar(r['y'], 20)}",
            "n": r["n"], "Método": r["metodo"], "Ajuste": TIPO_CURTO[r["tipo"]],
            "Modo": MODO_CURTO["entradas" if r["armazenar"] else "resultado"],
            "Valor exato": formatar(r["exato"], 20), "Valor aproximado": formatar(r["aprox"], 20),
            "Ea": formatar_aprox(r["ea"], 6), "Er": formatar_percentual(r["er"]),
        }
    st.session_state["historico"] = (st.session_state["historico"] + [linha])[-50:]


# =====================================================================
# 3. COMPONENTES DE INTERFACE
# =====================================================================

def mostrar_tabela(linhas):
    """Mostra uma lista de dicionários como tabela estática.
    A primeira coluna vira o cabeçalho das linhas (fica mais legível)."""
    if not linhas:
        return
    tabela = pd.DataFrame(linhas)
    st.table(tabela.set_index(tabela.columns[0]))


def gerar_alertas(r, rotulo=""):
    """Avisos didáticos sobre o resultado: anulação e cancelamento subtrativo.
    Devolve lista de (tipo, mensagem), onde tipo é 'error' ou 'warning'."""
    prefixo = f"**{rotulo}:** " if rotulo else ""
    alertas = []
    if r["aprox"] == 0 and r["exato"] != 0:
        alertas.append((
            "error",
            prefixo + "o valor aproximado virou **0**: a operação foi **anulada** pela precisão "
                      "limitada (perda total de dígitos significativos). O erro relativo fica "
                      "**indefinido**, pois o enunciado só o define quando o valor aproximado é ≠ 0."
        ))
    perdidos = digitos_perdidos_por_cancelamento(r)
    if perdidos:
        alertas.append((
            "warning",
            prefixo + f"**cancelamento subtrativo:** o resultado é cerca de {perdidos} ordens de "
                      f"grandeza menor que os operandos. Os primeiros dígitos (iguais) se anulam e "
                      f"sobram só os últimos — justamente os mais afetados pelo armazenamento com "
                      f"n dígitos."
        ))
    return alertas


def exibir_alertas(alertas):
    """Mostra os alertas gerados por gerar_alertas()."""
    for tipo, mensagem in alertas:
        if tipo == "error":
            st.error(mensagem)
        else:
            st.warning(mensagem)


def leitura_do_resultado(r):
    """Frase curta interpretando Ea e Er (objetivo: 'calcular e interpretar')."""
    if r["er"] is None:
        return "O valor aproximado é 0, então o erro relativo não está definido."
    if r["ea"] == 0:
        return (f"O valor exato cabe em n = {r['n']} ({TIPO_CURTO[r['tipo']]}); "
                f"a máquina o representa sem erro (Ea = 0).")
    return (f"O erro absoluto foi {formatar_aprox(r['ea'], 6)} e o erro relativo é da ordem de "
            f"10{sobrescrito(r['er'].adjusted())} ({formatar_percentual(r['er'])}).")


def montar_passo_a_passo(r):
    """Texto (markdown) com o caminho do cálculo, no mesmo roteiro do item 3.2."""
    simb, n = SIMBOLOS[r["op"]], r["n"]
    unidade = TIPO_CURTO[r["tipo"]]
    er_txt = "indefinido (aproximado = 0)" if r["er"] is None else formatar_aprox(r["er"], 8)
    linhas = [f"1. **Operação exata** (precisão máxima): "
              f"`{formatar(r['x'])} {simb} {formatar(r['y'])} = {formatar(r['exato'])}`"]
    if r["x_maq"] is not None:
        linhas.append(
            f"2. **Armazenamento das entradas** com n = {n} {unidade} ({r['metodo']}): "
            f"`X = {formatar(r['x'])}` → `{formatar(r['x_maq'])}` e "
            f"`Y = {formatar(r['y'])}` → `{formatar(r['y_maq'])}`. "
            f"Operação com os valores da máquina: "
            f"`{formatar(r['x_maq'])} {simb} {formatar(r['y_maq'])} = {formatar(r['bruto'])}`")
    else:
        linhas.append("2. **Armazenamento das entradas:** não se aplica neste modo — "
                      "só o resultado é ajustado (item 3.2 do enunciado).")
    linhas.append(f"3. **Normalização** do valor a ajustar: "
                  f"`{formatar(r['bruto'])}` = `{notacao_normalizada(r['bruto'])}`")
    n_pad = n if r["tipo"] == "significativos" else None
    linhas.append(f"4. **Ajuste** ({r['metodo']}) para n = {n} {unidade}: "
                  f"`{formatar(r['aprox'])}` = `{notacao_normalizada(r['aprox'], n_pad)}`")
    linhas.append(f"5. **Erros:** `Ea = |{formatar(r['exato'], 20)} − {formatar(r['aprox'])}| = "
                  f"{formatar_aprox(r['ea'], 8)}` e `Er = Ea / |aproximado| = {er_txt}`")
    return "\n".join(linhas)


def mostrar_resultado(r):
    """Apresenta o resultado de uma operação básica da calculadora livre."""
    n = r["n"]
    n_pad = n if r["tipo"] == "significativos" else None

    st.success("✅ Cálculo realizado com sucesso!")
    st.caption(f"Configuração usada: n = {n} · {r['metodo']} · {TIPO_CURTO[r['tipo']]} · "
               f"{MODO_CURTO['entradas' if r['armazenar'] else 'resultado']}")

    # --- Os quatro resultados exigidos pelo item 3.3 do enunciado ---
    st.markdown("#### Resultados")
    if r["er"] is None:
        er_valor, er_notacao = "indefinido (valor aproximado = 0)", "—"
    else:
        er_valor = f"{formatar_aprox(r['er'], 8)}  ({formatar_percentual(r['er'])})"
        er_notacao = notacao_normalizada(r["er"], sig_max=10)
    mostrar_tabela([
        {"Grandeza": "Valor exato", "Valor": formatar(r["exato"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["exato"])},
        {"Grandeza": "Valor aproximado (simulador)", "Valor": formatar(r["aprox"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["aprox"], n_pad)},
        {"Grandeza": "Erro absoluto  Ea = |exato − aproximado|", "Valor": formatar_aprox(r["ea"], 10),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["ea"], sig_max=12)},
        {"Grandeza": "Erro relativo  Er = Ea / |aproximado|", "Valor": er_valor,
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": er_notacao},
    ])

    # --- Entradas (e como a máquina as guardou, se for o caso) ---
    linhas_entrada = [
        {"Entrada": "X digitado", "Valor": formatar(r["x"]), "Notação normalizada": notacao_normalizada(r["x"])},
        {"Entrada": "Y digitado", "Valor": formatar(r["y"]), "Notação normalizada": notacao_normalizada(r["y"])},
    ]
    if r["x_maq"] is not None:
        linhas_entrada += [
            {"Entrada": "X na máquina", "Valor": formatar(r["x_maq"]),
             "Notação normalizada": notacao_normalizada(r["x_maq"], n_pad)},
            {"Entrada": "Y na máquina", "Valor": formatar(r["y_maq"]),
             "Notação normalizada": notacao_normalizada(r["y_maq"], n_pad)},
        ]
    st.markdown("#### Entradas")
    mostrar_tabela(linhas_entrada)
    if r["x_maq"] is None:
        st.caption("Neste modo X e Y entram na operação sem ajuste; apenas o resultado é ajustado.")

    exibir_alertas(gerar_alertas(r))
    st.info("📖 " + leitura_do_resultado(r))

    with st.expander("🔍 Passo a passo do cálculo", expanded=True):
        st.markdown(montar_passo_a_passo(r))


def mostrar_metricas_sequenciais(r):
    """Quatro números-resumo de uma operação sequencial."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valor exato final", formatar(r["exato"]))
    c2.metric("Valor aproximado final", formatar(r["final"]))
    c3.metric("Erro absoluto final (Ea)", formatar_aprox(r["ea"], 8))
    c4.metric("Erro relativo final (Er)", formatar_percentual(r["er"]))


def mostrar_passos_sequenciais(r):
    """Tabela passo a passo + gráfico do erro acumulado (usado pela calculadora
    sequencial e pelo Exemplo 3)."""
    simb = SIMBOLOS[r["op"]]
    st.markdown("#### Evolução passo a passo")
    mostrar_tabela([{
        "Passo nº": p["passo"],
        "Operação": f"{formatar(p['anterior'])} {simb} {formatar(p['termo'])}",
        "Resultado do passo (antes do ajuste)": formatar(p["bruto"]),
        "Após o ajuste (máquina)": formatar(p["apos"]),
        "Valor exato acumulado": formatar(p["exato_parcial"]),
        "Erro absoluto acumulado": formatar_aprox(p["erro"], 6),
    } for p in r["passos"]])

    # Gráfico só ilustrativo: float é usado APENAS para desenhar a curva.
    # Nenhum cálculo do simulador usa float.
    if r["passos"]:
        grafico = pd.DataFrame({"Passo": [p["passo"] for p in r["passos"]],
                                "Erro absoluto acumulado": [float(p["erro"]) for p in r["passos"]]})
        st.line_chart(grafico.set_index("Passo"))
        st.caption("Evolução do erro absoluto acumulado a cada passo (gráfico ilustrativo).")


def mostrar_resultado_sequencial(r):
    """Apresenta o resultado de uma operação sequencial da calculadora livre."""
    n = r["n"]
    n_pad = n if r["tipo"] == "significativos" else None

    st.success("✅ Operação sequencial concluída!")
    st.caption(
        f"Configuração usada: {r['quantidade']} repetições da operação {r['op']} · "
        f"n = {n} · {r['metodo']} · {TIPO_CURTO[r['tipo']]} · "
        f"{'operandos guardados na máquina' if r['armazenar'] else 'só os resultados de cada passo são ajustados'}"
    )
    mostrar_metricas_sequenciais(r)

    st.markdown("#### Resumo do resultado final")
    if r["er"] is None:
        er_valor, er_notacao = "indefinido (valor aproximado = 0)", "—"
    else:
        er_valor = f"{formatar_aprox(r['er'], 8)}  ({formatar_percentual(r['er'])})"
        er_notacao = notacao_normalizada(r["er"], sig_max=10)
    mostrar_tabela([
        {"Grandeza": "Valor exato final", "Valor": formatar(r["exato"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["exato"])},
        {"Grandeza": "Valor aproximado final", "Valor": formatar(r["final"]),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["final"], n_pad)},
        {"Grandeza": "Erro absoluto total  Ea = |exato − aproximado|", "Valor": formatar_aprox(r["ea"], 10),
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": notacao_normalizada(r["ea"], sig_max=12)},
        {"Grandeza": "Erro relativo total  Er = Ea / |aproximado|", "Valor": er_valor,
         "Notação normalizada (0.d₁d₂… × 10ᵉ)": er_notacao},
    ])
    mostrar_passos_sequenciais(r)


def mostrar_historico():
    """Tabela com os cálculos feitos nesta sessão (mais recente primeiro)."""
    historico = st.session_state["historico"]
    with st.expander(f"🕘 Histórico desta sessão ({len(historico)})"):
        if not historico:
            st.write("Nenhum cálculo ainda. Faça um cálculo e ele aparece aqui.")
            return
        tabela = pd.DataFrame(list(reversed(historico)))
        try:
            st.dataframe(tabela, hide_index=True)
        except TypeError:                 # versões antigas do Streamlit não têm hide_index
            st.dataframe(tabela)


def processar_calculo():
    """Lê os campos da operação básica, valida, calcula e guarda o resultado.
    Valida X e Y juntos para mostrar todos os problemas de uma vez."""
    erros, x, y = [], None, None
    try:
        x = interpretar_numero(st.session_state["x_txt"], "X")
    except ErroSimulador as erro:
        erros.append(str(erro))
    try:
        y = interpretar_numero(st.session_state["y_txt"], "Y")
    except ErroSimulador as erro:
        erros.append(str(erro))
    if erros:
        st.session_state["resultado"] = None
        for mensagem in erros:
            st.error("⚠️ " + mensagem)
        return

    try:
        r = simular_operacao(
            x, y, st.session_state["op"], int(st.session_state["n_dig"]),
            st.session_state["metodo"], st.session_state["tipo_ajuste"],
            st.session_state["modo_calc"] == "entradas",
        )
    except ErroSimulador as erro:
        st.session_state["resultado"] = None
        st.error("⚠️ " + str(erro))
        return
    except Exception as erro:             # rede de segurança: nunca mostrar "traceback" ao público
        st.session_state["resultado"] = None
        st.error(f"⚠️ Erro inesperado ({type(erro).__name__}). Confira os valores e tente de novo.")
        return

    st.session_state["resultado"] = r
    registrar_historico(r)


def processar_calculo_sequencial():
    """Lê os campos da operação sequencial, valida, calcula e guarda o resultado."""
    erros, termo, base = [], None, None
    try:
        termo = interpretar_numero(st.session_state["seq_termo_txt"], "Termo repetido")
    except ErroSimulador as erro:
        erros.append(str(erro))
    if st.session_state["seq_modo_entrada"] == "base_e_termo":
        try:
            base = interpretar_numero(st.session_state["seq_base_txt"], "Valor inicial")
        except ErroSimulador as erro:
            erros.append(str(erro))
    if erros:
        st.session_state["resultado"] = None
        for mensagem in erros:
            st.error("⚠️ " + mensagem)
        return

    try:
        r = simular_operacao_sequencial(
            valor_base=base, termo=termo, op=st.session_state["seq_op"],
            quantidade=int(st.session_state["seq_qtd"]), n=int(st.session_state["seq_n_dig"]),
            metodo=st.session_state["seq_metodo"], tipo=st.session_state["seq_tipo_ajuste"],
            armazenar_operandos=bool(st.session_state["seq_armazenar"]),
        )
    except ErroSimulador as erro:
        st.session_state["resultado"] = None
        st.error("⚠️ " + str(erro))
        return
    except Exception as erro:
        st.session_state["resultado"] = None
        st.error(f"⚠️ Erro inesperado ({type(erro).__name__}). Confira os valores e tente de novo.")
        return

    st.session_state["resultado"] = r
    registrar_historico(r)


# =====================================================================
# 4. CASOS DE DEMONSTRAÇÃO (aba 2): cada exemplo usa o modo que o PDF pede
# =====================================================================

def explicar_ajuste(exato, n):
    """Explica, com os dígitos do valor exato, de onde vem a diferença entre
    truncamento e arredondamento (procedimento comum de testes, passo 4)."""
    if exato == 0:
        return "O valor exato é 0; não há o que ajustar."
    digitos = "".join(str(d) for d in exato.normalize(CTX_EXATO).as_tuple().digits)
    if len(digitos) <= n:
        return (f"O valor exato tem apenas {len(digitos)} dígito(s) significativo(s) (≤ n = {n}): "
                f"cabe inteiro na máquina, então truncamento e arredondamento coincidem e **Ea = 0**.")
    mantidos, descartado = digitos[:n], int(digitos[n])
    if descartado >= 5:
        regra_arred = "o dígito descartado é ≥ 5, então ele **soma 1** ao último dígito mantido"
    else:
        regra_arred = "o dígito descartado é < 5, então ele **mantém** os dígitos (igual ao truncamento)"
    return (f"Dígitos significativos do valor exato: `{digitos}`. Com n = {n}, a máquina guarda "
            f"`{mantidos}` e descarta o resto (primeiro dígito descartado: **{descartado}**).\n\n"
            f"- **Truncamento:** apenas corta os dígitos extras.\n"
            f"- **Arredondamento:** {regra_arred}.")


def demo_exemplo_1():
    """Exemplo 1: soma de dois números com 5 casas decimais, n = 4 (só o resultado é ajustado)."""
    with st.expander("Exemplo 1 — Operação simples (soma)"):
        st.write("Soma de dois números com 5 casas decimais, com n = 4 dígitos significativos. "
                 "Aqui só o **resultado** é ajustado (item 3.2). Os valores do PDF já estão "
                 "preenchidos, mas você pode editá-los e testar outros.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("X", key="d1_x")
        c2.text_input("Y", key="d1_y")
        c3.number_input("n (dígitos significativos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d1_n")
        try:
            x = interpretar_numero(st.session_state["d1_x"], "X")
            y = interpretar_numero(st.session_state["d1_y"], "Y")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        n = int(st.session_state["d1_n"])

        resultados = {m: simular_operacao(x, y, "+", n, m, "significativos", False)
                      for m in ("truncamento", "arredondamento")}
        exato = resultados["truncamento"]["exato"]
        st.write(f"**Operação:** {formatar(x)} + {formatar(y)}  →  valor exato = "
                 f"`{formatar(exato)}` = `{notacao_normalizada(exato)}`")

        mostrar_tabela([{
            "Método": metodo.capitalize(),
            "Valor exato": formatar(r["exato"]),
            "Valor aproximado": formatar(r["aprox"]),
            "Notação normalizada": notacao_normalizada(r["aprox"], n),
            "Erro absoluto (Ea)": formatar_aprox(r["ea"], 10),
            "Erro relativo (Er)": formatar_aprox(r["er"], 8),
            "Er (%)": formatar_percentual(r["er"]),
        } for metodo, r in resultados.items()])
        st.markdown(explicar_ajuste(exato, n))
        st.button("➡️ Enviar para a calculadora livre", key="d1_enviar",
                  on_click=enviar_para_calculadora,
                  args=(st.session_state["d1_x"], "+", st.session_state["d1_y"], n,
                        "truncamento", "significativos", "resultado"),
                  help="Pré-seleciona truncamento; troque o método lá se quiser comparar.")


def demo_exemplo_2():
    """Exemplo 2: cancelamento subtrativo (X e Y são armazenados com n dígitos antes de subtrair)."""
    with st.expander("Exemplo 2 — Propagação de erro e cancelamento subtrativo"):
        st.write("X e Y são guardados na máquina com n = 4 dígitos significativos **antes** da "
                 "subtração (como no PDF). Veja o que acontece com cada método — com truncamento "
                 "a subtração fica **nula**.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("X", key="d2_x")
        c2.text_input("Y", key="d2_y")
        c3.number_input("n (dígitos significativos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d2_n")
        try:
            x = interpretar_numero(st.session_state["d2_x"], "X")
            y = interpretar_numero(st.session_state["d2_y"], "Y")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        n = int(st.session_state["d2_n"])

        resultados = {m: simular_operacao(x, y, "-", n, m, "significativos", True)
                      for m in ("arredondamento", "truncamento")}
        exato = resultados["arredondamento"]["exato"]
        st.write(f"**Valor exato:** {formatar(x)} − {formatar(y)} = `{formatar(exato)}` "
                 f"= `{notacao_normalizada(exato)}`")

        mostrar_tabela([{
            "Método": metodo.capitalize(),
            "X na máquina": formatar(r["x_maq"]),
            "Y na máquina": formatar(r["y_maq"]),
            "Resultado aproximado": formatar(r["aprox"]),
            "Notação normalizada": notacao_normalizada(r["aprox"], n),
            "Erro absoluto (Ea)": formatar_aprox(r["ea"], 10),
            "Erro relativo (Er)": formatar_aprox(r["er"], 8) if r["er"] is not None else "indefinido",
            "Er (%)": formatar_percentual(r["er"]),
        } for metodo, r in resultados.items()])

        for metodo, r in resultados.items():
            exibir_alertas(gerar_alertas(r, metodo.capitalize()))
        st.markdown(
            "**Por que isso acontece?** X e Y são quase iguais; ao subtraí-los, os primeiros "
            "dígitos se anulam e sobram apenas os últimos — exatamente os que o armazenamento com "
            "n dígitos distorce (arredondamento) ou descarta (truncamento). O resultado, que "
            "deveria ser pequeno e preciso, fica com erro relativo enorme ou até zero."
        )
        st.button("➡️ Enviar para a calculadora livre", key="d2_enviar",
                  on_click=enviar_para_calculadora,
                  args=(st.session_state["d2_x"], "-", st.session_state["d2_y"], n,
                        "arredondamento", "significativos", "entradas"),
                  help="Pré-seleciona arredondamento (como na análise do PDF); troque lá para truncamento.")


def demo_exemplo_3():
    """Exemplo 3: somar uma parcela várias vezes ajustando a soma a cada passo."""
    with st.expander("Exemplo 3 — Propagação de erro em uma sequência de somas"):
        st.write("Somar 0.56786 dez vezes, ajustando a soma a cada passo. Os valores do PDF já "
                 "estão preenchidos; edite à vontade.")
        c1, c2, c3 = st.columns(3)
        c1.text_input("Parcela", key="d3_p")
        c2.number_input("Quantidade de termos", min_value=2, max_value=100, step=1, key="d3_qtd")
        c3.number_input("n (dígitos)", min_value=N_MIN, max_value=N_MAX, step=1, key="d3_n")
        c4, c5 = st.columns(2)
        c4.radio("Método de ajuste", list(METODOS), key="d3_metodo",
                 format_func=METODOS.get, horizontal=True)
        c5.checkbox("Guardar também a parcela com n dígitos antes de somar (variante “máquina real”)",
                    key="d3_armazenar")
        try:
            parcela = interpretar_numero(st.session_state["d3_p"], "Parcela")
        except ErroSimulador as erro:
            st.error("⚠️ " + str(erro))
            return
        qtd, n = int(st.session_state["d3_qtd"]), int(st.session_state["d3_n"])
        metodo, armazenar = st.session_state["d3_metodo"], bool(st.session_state["d3_armazenar"])

        st.info(
            "ℹ️ **Observação sobre o enunciado:** os passos do PDF (1.1357, 1.7035, 2.2713…) "
            "cortam em **4 casas decimais**, enquanto o item 3.2 define n como **dígitos "
            "significativos** (1.13572 → 1.135 com n = 4). Por isso as duas versões aparecem "
            "abaixo, lado a lado, para comparação."
        )
        aba_dec, aba_sig = st.tabs([f"{n} casas decimais (como no PDF)",
                                    f"{n} dígitos significativos (item 3.2)"])
        for aba, tipo in ((aba_dec, "decimais"), (aba_sig, "significativos")):
            with aba:
                # Exemplo 3 = repetir o mesmo termo (valor_base=None) com a operação "+".
                r = simular_operacao_sequencial(None, parcela, "+", qtd, n, metodo, tipo, armazenar)
                mostrar_metricas_sequenciais(r)
                mostrar_passos_sequenciais(r)


# =====================================================================
# 5. PÁGINA PRINCIPAL
# =====================================================================

# --- Tela de despedida (botão "Sair") ---------------------------------
if st.session_state["encerrado"]:
    st.title("👋 Sessão encerrada")
    st.write("Obrigado por usar o Simulador de Propagação de Erros Numéricos! "
             "Você já pode fechar esta aba.")
    st.button("↩️ Voltar ao simulador", on_click=voltar)
    st.stop()          # interrompe o script aqui: nada abaixo é desenhado

st.title("🧮 Simulador de Propagação de Erros Numéricos")
st.caption("Cálculo Numérico • Univasf • Projeto Unidade 1 (Erros). Simula uma máquina que guarda "
           "só n dígitos e mostra como truncamento e arredondamento geram e propagam erros.")

aba_calc, aba_demo, aba_ajuda = st.tabs(
    ["🧮 Calculadora livre", "📋 Casos de demonstração (PDF)", "ℹ️ Ajuda e conceitos"])

# ---------------------------------------------------------------------
# ABA 1: CALCULADORA LIVRE (duas sub-abas: básica e sequencial)
# ---------------------------------------------------------------------
with aba_calc:
    st.subheader("Calculadora de precisão limitada")
    sub_basica, sub_seq = st.tabs(["Operação básica (X e Y)",
                                   "Operação sequencial (repetida k vezes)"])

    # ----- Sub-aba: operação básica -----
    with sub_basica:
        st.write("Digite **X** e **Y** (ponto ou vírgula), escolha a operação, o número de dígitos **n** "
                 "e o método, e clique em **Calcular**.")

        # O formulário só dispara o cálculo ao clicar em "Calcular" (ou apertar Enter),
        # e todos os campos chegam juntos — evita bugs de digitação no celular.
        with st.form("form_calculadora_basica"):
            col_x, col_op, col_y = st.columns([3, 2, 3])
            col_x.text_input("Valor de X", key="x_txt", placeholder="ex.: 0.76545",
                             help="Número com ponto ou vírgula decimal. Aceita notação científica, ex.: 1.5e-3.")
            col_op.selectbox("Operação", list(OPERACOES), key="op", format_func=OPERACOES.get)
            col_y.text_input("Valor de Y", key="y_txt", placeholder="ex.: 0.76541",
                             help="Mesmas regras do X. Na divisão, Y não pode ser 0.")

            col_n, col_m = st.columns([1, 2])
            col_n.number_input("Dígitos (n)", min_value=N_MIN, max_value=N_MAX, step=1, key="n_dig",
                               help="Quantos dígitos a máquina guarda (veja 'tipo de ajuste' nas opções avançadas).")
            col_m.radio("Método de ajuste", list(METODOS), key="metodo", format_func=METODOS.get)

            with st.expander("⚙️ Opções avançadas: tipo de ajuste e modo de cálculo "
                             "(padrão: dígitos significativos + entradas e resultado)"):
                st.radio("O que o “n” conta?", list(TIPOS_AJUSTE), key="tipo_ajuste",
                         format_func=TIPOS_AJUSTE.get)
                st.radio("O que é ajustado?", list(MODOS_CALCULO), key="modo_calc",
                         format_func=MODOS_CALCULO.get)

            calcular = st.form_submit_button("Calcular", type="primary")

        if calcular:
            processar_calculo()
        resultado = st.session_state["resultado"]
        if resultado is not None and resultado.get("tipo_resultado") != "sequencial":
            mostrar_resultado(resultado)
        elif not calcular:
            st.info("👆 Preencha os campos e clique em **Calcular** para ver o resultado.")

    # ----- Sub-aba: operação sequencial -----
    with sub_seq:
        st.write("Repita uma operação **k vezes**, ajustando o resultado a cada passo, para ver o "
                 "erro se **acumular e se propagar** (Exemplo 3 do PDF).")

        # Este seletor fica FORA do formulário de propósito: assim, ao trocar a opção, a
        # página atualiza na hora e o campo "Valor inicial" liga/desliga imediatamente.
        st.radio("Estrutura da operação repetida", list(ESTRUTURAS_SEQ), key="seq_modo_entrada",
                 format_func=ESTRUTURAS_SEQ.get, horizontal=True)
        usa_base = st.session_state["seq_modo_entrada"] == "base_e_termo"

        with st.form("form_calculadora_sequencial"):
            col_b, col_o, col_t, col_q = st.columns([3, 2, 3, 2])
            col_b.text_input("Valor inicial", key="seq_base_txt", placeholder="ex.: 1.0",
                             disabled=not usa_base,
                             help="Usado só na estrutura 'Partir de um valor inicial'.")
            col_o.selectbox("Operação", list(OPERACOES), key="seq_op", format_func=OPERACOES.get)
            col_t.text_input("Termo repetido", key="seq_termo_txt", placeholder="ex.: 0.56786",
                             help="Valor que entra na operação a cada passo.")
            col_q.number_input("Repetições (k)", min_value=2, max_value=100, step=1, key="seq_qtd",
                               help="'Repetir o mesmo termo': k é o número de termos (k − 1 operações). "
                                    "'Valor inicial': k é o número de operações.")

            col_n2, col_m2 = st.columns([1, 2])
            col_n2.number_input("Dígitos (n)", min_value=N_MIN, max_value=N_MAX, step=1, key="seq_n_dig")
            col_m2.radio("Método de ajuste", list(METODOS), key="seq_metodo", format_func=METODOS.get)

            with st.expander("⚙️ Opções avançadas da operação sequencial"):
                st.radio("O que o “n” conta?", list(TIPOS_AJUSTE), key="seq_tipo_ajuste",
                         format_func=TIPOS_AJUSTE.get)
                st.checkbox("Guardar também o ponto de partida e o termo com n dígitos antes de operar",
                            key="seq_armazenar",
                            help="Se marcado, eles são truncados/arredondados antes de entrar nas contas.")

            calcular_seq = st.form_submit_button("Calcular operação sequencial", type="primary")

        if calcular_seq:
            processar_calculo_sequencial()
        resultado = st.session_state["resultado"]
        if resultado is not None and resultado.get("tipo_resultado") == "sequencial":
            mostrar_resultado_sequencial(resultado)
        elif not calcular_seq:
            st.info("👆 Preencha os campos e clique em **Calcular operação sequencial**.")

    # --- Ações: novo cálculo / limpar histórico / sair (instrução 4 do enunciado) ---
    b1, b2, b3 = st.columns(3)
    b1.button("🔄 Novo cálculo", on_click=novo_calculo, key="btn_novo",
              help="Limpa os valores digitados e o resultado para você começar outro problema.")
    b2.button("🧹 Limpar histórico", on_click=limpar_historico, key="btn_limpar_hist")
    b3.button("🚪 Sair", on_click=sair, key="btn_sair", help="Encerra a sessão.")

    mostrar_historico()

# ---------------------------------------------------------------------
# ABA 2: CASOS DE DEMONSTRAÇÃO (valores do PDF, editáveis)
# ---------------------------------------------------------------------
with aba_demo:
    st.subheader("Exemplos do enunciado")
    st.write("Cada exemplo já vem com os valores do PDF e usa o modo de cálculo que o enunciado pede "
             "para ele. Você pode **editar os valores** para testar outros casos sem reiniciar.")
    aviso = st.session_state.pop("aviso_envio", None)
    if aviso:
        st.success(aviso)
    demo_exemplo_1()
    demo_exemplo_2()
    demo_exemplo_3()

# ---------------------------------------------------------------------
# ABA 3: AJUDA E CONCEITOS
# ---------------------------------------------------------------------
with aba_ajuda:
    st.subheader("Como usar")
    st.markdown(
        "- **Digite os números** com ponto ou vírgula (`0.76545` ou `0,76545`). Também vale "
        "notação científica (`1.5e-3`). Limites: até "
        f"{MAX_DIGITOS_ENTRADA} dígitos significativos e valores entre 1e-{MAX_EXPOENTE_ENTRADA} e "
        f"1e{MAX_EXPOENTE_ENTRADA} (ou 0).\n"
        "- **Operação básica:** escolha operação, **n** e método e clique em **Calcular**.\n"
        "- **Operação sequencial:** repete uma operação k vezes, ajustando a cada passo, e mostra "
        "como o erro se acumula.\n"
        "- **Novo cálculo** limpa os campos; o **histórico** guarda tudo que você calculou; "
        "**Sair** encerra a sessão."
    )

    st.subheader("Conceitos")
    st.markdown("**Notação normalizada:** todo número é escrito como 0.d₁d₂…dₙ × 10ᵉ, com d₁ ≠ 0. "
                "Exemplo: 123.45 = 0.12345 × 10³.")
    st.markdown("**Truncamento:** descarta os dígitos além do n-ésimo. "
                "**Arredondamento:** olha o primeiro dígito descartado; se for 5 ou mais, soma 1 "
                "ao último dígito mantido.")
    st.markdown("**Erros (definições do enunciado):**")
    st.latex(r"E_a = \left|\,\text{valor exato} - \text{valor aproximado}\,\right|")
    st.latex(r"E_r = \dfrac{E_a}{\left|\,\text{valor aproximado}\,\right|}")
    st.markdown("Se o valor aproximado for 0, o erro relativo é **indefinido** (a menos que Ea = 0, "
                "caso em que não há erro).")

    st.subheader("Opções avançadas")
    st.markdown(
        "- **O que o “n” conta?** *Dígitos significativos* (item 3.2 do enunciado) ou *casas "
        "decimais* (é o que os passos do Exemplo 3 do PDF fazem: 1.13572 → 1.1357).\n"
        "- **O que é ajustado?** *Só o resultado* (item 3.2: opera com os valores exatos e ajusta o "
        "resultado) ou *entradas e resultado* (a máquina guarda X e Y com n dígitos antes de operar, "
        "como no Exemplo 2). Os dois modos podem dar valores diferentes por causa do ajuste duplo."
    )

    st.subheader("Por que o cálculo usa Decimal?")
    st.markdown(
        "A máquina hipotética do enunciado trabalha em **base 10**. O `float` do Python trabalha em "
        "base 2 e não consegue guardar números como 0.7655 ou 28.4 exatamente, o que distorceria "
        "dígitos no truncamento e no arredondamento. Por isso o simulador lê o que você digita "
        "diretamente como número decimal (`decimal.Decimal`) e calcula o valor exato com 400 dígitos "
        "de precisão. Você continua informando “números em ponto flutuante” normalmente."
    )
